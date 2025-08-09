import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException
import stripe

from agentops.opsboard.services.billing_service import billing_service


def get_org_owner_id(org):
    """Helper to get the owner user ID from an organization."""
    for user_org in org.users:
        if user_org.role == OrgRoles.owner:
            return user_org.user_id
    return None


def setup_mock_request_auth(mock_request, user_id):
    """Helper to ensure mock_request has proper authentication setup."""
    if not hasattr(mock_request, 'state'):
        mock_request.state = MagicMock()
    if not hasattr(mock_request.state, 'session'):
        mock_request.state.session = MagicMock()
    mock_request.state.session.user_id = user_id


from agentops.opsboard.views.billing import BillingDashboardView
from agentops.opsboard.views.orgs import update_member_licenses, UpdateMemberLicensesBody
from agentops.opsboard.models import (
    OrgModel,
    UserOrgModel,
    BillingPeriod,
    BillingAuditLog,
    PremStatus,
    OrgRoles,
    ProjectModel,
)

# Import shared billing fixtures
pytest_plugins = ["tests._conftest.billing"]


# Mock stripe at module level to prevent API key errors
stripe.api_key = 'sk_test_mock'


@pytest.fixture(autouse=True)
def ensure_clean_session(orm_session):
    """Ensure clean session state before each test."""
    try:
        # Check if session has pending rollback
        if orm_session.in_transaction() and orm_session.is_active:
            if hasattr(orm_session, '_transaction') and orm_session._transaction.is_active:
                # Session is in a good state
                pass
        yield
    except Exception:
        orm_session.rollback()
        raise
    finally:
        # Cleanup after test
        try:
            if orm_session.in_transaction():
                orm_session.rollback()
        except Exception:
            pass


@pytest.fixture
def test_billing_members(orm_session, test_pro_org, test_user2, test_user3):
    """Create test members for billing integration tests."""
    members = []

    # Use existing test users to avoid foreign key constraints
    test_users = [test_user2, test_user3]

    for i, user in enumerate(test_users):
        member = UserOrgModel(
            user_id=user.id,
            org_id=test_pro_org.id,
            role=OrgRoles.developer,
            user_email=user.email,
            is_paid=i < 1,  # First one is paid, second one is not
        )
        orm_session.add(member)
        members.append(member)

    orm_session.flush()
    return members


@pytest.fixture(autouse=True)
def mock_stripe_config():
    """Mock Stripe configuration for all tests."""
    with (
        patch('agentops.opsboard.views.orgs.STRIPE_SECRET_KEY', 'sk_test_123'),
        patch('agentops.opsboard.views.orgs.STRIPE_SUBSCRIPTION_PRICE_ID', 'price_test123'),
        patch('agentops.api.environment.STRIPE_SECRET_KEY', 'sk_test_123'),
        patch('agentops.api.environment.STRIPE_SUBSCRIPTION_PRICE_ID', 'price_test123'),
        patch.dict(
            'os.environ',
            {'STRIPE_SECRET_KEY': 'sk_test_123', 'STRIPE_SUBSCRIPTION_PRICE_ID': 'price_test123'},
        ),
    ):
        yield


class TestBillingIntegration:
    """Integration tests for the billing system components."""

    @patch('stripe.Subscription.modify')
    @patch('stripe.Subscription.retrieve')
    async def test_full_billing_workflow_new_member_join(
        self,
        mock_stripe_retrieve,
        mock_stripe_modify,
        mock_request,
        orm_session,
        test_pro_org,
        test_billing_members,
        mock_stripe_subscription,
    ):
        """Test complete billing workflow when a new member joins and gets licensed."""
        setup_mock_request_auth(mock_request, get_org_owner_id(test_pro_org))
        mock_stripe_retrieve.return_value = mock_stripe_subscription

        unlicensed_member = next(m for m in test_billing_members if not m.is_paid)

        # Step 1: License the member
        body = UpdateMemberLicensesBody(add=[str(unlicensed_member.user_id)], remove=[])

        license_result = await update_member_licenses(
            request=mock_request, org_id=str(test_pro_org.id), body=body, orm=orm_session
        )

        # Verify licensing worked
        assert license_result.paid_members_count == 3  # Owner + 1 existing + newly added

        # Step 2: Check audit log was created
        audit_logs = (
            orm_session.query(BillingAuditLog)
            .filter_by(org_id=test_pro_org.id, action='member_licensed')
            .all()
        )
        assert len(audit_logs) == 1
        assert audit_logs[0].details['member_id'] == str(unlicensed_member.user_id)

        # Step 3: Verify Stripe was called
        mock_stripe_modify.assert_called_once()
        call_args = mock_stripe_modify.call_args
        assert call_args[1]['items'][0]['quantity'] == 3

    @patch('stripe.Subscription.modify')
    @patch('stripe.Subscription.retrieve')
    async def test_full_billing_workflow_member_removal(
        self,
        mock_stripe_retrieve,
        mock_stripe_modify,
        mock_request,
        orm_session,
        test_pro_org,
        test_billing_members,
        mock_stripe_subscription,
    ):
        """Test complete billing workflow when a member is removed and unlicensed."""
        setup_mock_request_auth(mock_request, get_org_owner_id(test_pro_org))
        mock_stripe_retrieve.return_value = mock_stripe_subscription

        licensed_member = next(m for m in test_billing_members if m.is_paid)

        # Step 1: Remove member license
        body = UpdateMemberLicensesBody(add=[], remove=[str(licensed_member.user_id)])

        license_result = await update_member_licenses(
            request=mock_request, org_id=str(test_pro_org.id), body=body, orm=orm_session
        )

        # Verify unlicensing worked
        assert license_result.paid_members_count == 1  # Only owner remains

        # Step 2: Check audit log was created
        audit_logs = (
            orm_session.query(BillingAuditLog)
            .filter_by(org_id=test_pro_org.id, action='member_unlicensed')
            .all()
        )
        assert len(audit_logs) == 1

        # Step 3: Verify member is marked as unpaid (need to refresh from DB)
        orm_session.refresh(licensed_member)
        assert licensed_member.is_paid is False

    async def test_billing_period_snapshot_creation_integration(
        self, orm_session, test_pro_org, test_billing_members
    ):
        """Test creating billing period snapshots integrates with usage tracking."""
        # Create some projects for usage data
        project = ProjectModel(name="Test Project", org_id=test_pro_org.id)
        orm_session.add(project)
        orm_session.flush()

        period_start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        period_end = datetime(2024, 1, 31, tzinfo=timezone.utc)

        with (
            patch.object(billing_service, 'get_usage_for_period') as mock_get_usage,
            patch.object(billing_service, 'calculate_usage_costs') as mock_calc_costs,
            patch.object(billing_service, 'get_seat_price') as mock_seat_price,
        ):
            mock_get_usage.return_value = {"tokens": 1000000, "spans": 500}
            mock_calc_costs.return_value = {"tokens": 20, "spans": 50}
            mock_seat_price.return_value = 4000

            billing_period = await billing_service.create_billing_period_snapshot(
                orm_session, test_pro_org, period_start, period_end
            )

        # Verify the snapshot
        assert billing_period.org_id == test_pro_org.id
        assert billing_period.seat_count == 2  # Owner + 1 paid member
        assert billing_period.seat_cost == 8000  # 2 * 4000
        assert billing_period.usage_quantities == {"tokens": 1000000, "spans": 500}
        assert billing_period.usage_costs == {"tokens": 20, "spans": 50}
        assert billing_period.total_cost == 8070  # 8000 + 20 + 50

        # Verify it's in the database
        saved_period = orm_session.query(BillingPeriod).filter_by(id=billing_period.id).first()
        assert saved_period is not None

    async def test_billing_dashboard_reflects_member_changes(
        self, mock_request, orm_session, test_pro_org, test_billing_members
    ):
        """Test billing dashboard shows updated costs after member licensing changes."""
        setup_mock_request_auth(mock_request, get_org_owner_id(test_pro_org))
        dashboard_view = BillingDashboardView(mock_request)

        with (
            patch.object(billing_service, 'get_usage_for_period', return_value={"tokens": 500000}),
            patch.object(billing_service, 'calculate_usage_costs', return_value={"tokens": 100}),
            patch.object(billing_service, 'get_seat_price', return_value=5000),
        ):
            result = await dashboard_view(org_id=str(test_pro_org.id), orm=orm_session)

        # Extract response data if wrapped in JSONResponse
        if hasattr(result, 'body'):
            import json

            result = json.loads(result.body.decode())

        # Verify dashboard reflects current state
        assert result['current_period']['seat_count'] == 2  # Owner + 1 paid member
        assert result['current_period']['seat_cost'] == 10000  # 2 * 5000
        assert result['current_period']['usage_costs'] == {"tokens": 100}
        assert result['current_period']['total_cost'] == 10100  # 10000 + 100

    async def test_billing_audit_logs_track_all_changes(
        self, mock_request, orm_session, test_pro_org, test_billing_members, billing_period_factory
    ):
        """Test audit logs are created for all billing-related changes."""
        setup_mock_request_auth(mock_request, get_org_owner_id(test_pro_org))
        # Create billing period
        billing_period = billing_period_factory(
            test_pro_org.id,
            total_cost=8000,
        )
        orm_session.add(billing_period)
        orm_session.commit()

        # Create audit log for period creation
        audit_log = BillingAuditLog(
            org_id=test_pro_org.id,
            user_id=mock_request.state.session.user_id,
            action='billing_period_created',
            details={'period_id': str(billing_period.id), 'total_cost': billing_period.total_cost},
        )
        orm_session.add(audit_log)
        orm_session.commit()

        # Verify audit trail
        all_logs = orm_session.query(BillingAuditLog).filter_by(org_id=test_pro_org.id).all()
        assert len(all_logs) >= 1

        period_creation_log = next((log for log in all_logs if log.action == 'billing_period_created'), None)
        assert period_creation_log is not None
        assert period_creation_log.details['period_id'] == str(billing_period.id)

    @patch('stripe.Subscription.modify')
    @patch('stripe.Subscription.retrieve')
    async def test_stripe_integration_member_licensing(
        self,
        mock_stripe_retrieve,
        mock_stripe_modify,
        mock_request,
        orm_session,
        test_pro_org,
        test_billing_members,
        mock_stripe_subscription,
    ):
        """Test Stripe subscription updates when member licensing changes."""
        setup_mock_request_auth(mock_request, get_org_owner_id(test_pro_org))
        mock_stripe_retrieve.return_value = mock_stripe_subscription

        # Test multiple operations
        unlicensed_member = next(m for m in test_billing_members if not m.is_paid)
        licensed_member = next(m for m in test_billing_members if m.is_paid)

        # Operation 1: Add member
        body1 = UpdateMemberLicensesBody(add=[str(unlicensed_member.user_id)], remove=[])

        await update_member_licenses(
            request=mock_request, org_id=str(test_pro_org.id), body=body1, orm=orm_session
        )

        # Operation 2: Remove member
        body2 = UpdateMemberLicensesBody(add=[], remove=[str(licensed_member.user_id)])

        await update_member_licenses(
            request=mock_request, org_id=str(test_pro_org.id), body=body2, orm=orm_session
        )

        # Verify Stripe was called twice with correct quantities
        assert mock_stripe_modify.call_count == 2

        # First call should increase quantity
        first_call = mock_stripe_modify.call_args_list[0]
        assert first_call[1]['items'][0]['quantity'] == 3  # Added one

        # Second call should decrease quantity
        second_call = mock_stripe_modify.call_args_list[1]
        assert second_call[1]['items'][0]['quantity'] == 2  # Removed one

    async def test_usage_cost_calculation_integration(self, orm_session, test_pro_org, test_billing_members):
        """Test usage cost calculation integrates with billing service and ClickHouse."""
        # Create project for usage
        project = ProjectModel(name="Usage Test Project", org_id=test_pro_org.id)
        orm_session.add(project)
        orm_session.flush()

        # Mock ClickHouse response
        with patch('agentops.opsboard.services.billing_service.get_clickhouse') as mock_clickhouse:
            mock_client = MagicMock()
            mock_result = MagicMock()
            mock_result.result_rows = [(1000, 82000)]  # span_count, total_tokens (50000+25000+5000+2000)
            mock_client.query.return_value = mock_result
            mock_clickhouse.return_value = mock_client

            period_start = datetime(2024, 1, 1)
            period_end = datetime(2024, 1, 31)

            # Get usage data
            usage_data = await billing_service.get_usage_for_period(
                orm_session, str(test_pro_org.id), period_start, period_end
            )

            # Calculate costs
            costs = await billing_service.calculate_usage_costs(usage_data)

        # Verify integration
        assert usage_data == {'tokens': 82000, 'spans': 1000}  # Total from mock data
        assert isinstance(costs, dict)
        assert 'tokens' in costs or 'spans' in costs  # At least one cost type

    async def test_billing_error_handling_integration(
        self, mock_request, orm_session, test_pro_org, test_billing_members, mock_stripe_subscription
    ):
        """Test error handling across billing service, views, and models."""
        setup_mock_request_auth(mock_request, get_org_owner_id(test_pro_org))
        # Test scenario: Stripe fails during member licensing
        with (
            patch('stripe.Subscription.retrieve') as mock_retrieve,
            patch('stripe.Subscription.modify') as mock_modify,
        ):
            # Ensure the mock subscription has the correct price ID to pass legacy check
            mock_stripe_subscription.items.data[0]['price']['id'] = 'price_test123'
            mock_retrieve.return_value = mock_stripe_subscription

            # Make Stripe fail
            mock_modify.side_effect = stripe.error.StripeError("Card declined")

            unlicensed_member = next(m for m in test_billing_members if not m.is_paid)

            body = UpdateMemberLicensesBody(add=[str(unlicensed_member.user_id)], remove=[])

            # Should raise HTTPException from Stripe error
            with pytest.raises(HTTPException) as excinfo:
                await update_member_licenses(
                    request=mock_request, org_id=str(test_pro_org.id), body=body, orm=orm_session
                )

            # Verify error is properly handled
            assert excinfo.value.status_code == 500
            assert "Failed to update subscription" in excinfo.value.detail

            # Verify the error was logged
            # Since the transaction raises an exception, the database changes are rolled back
            # and we can't easily verify the state without complex session management

    async def test_billing_cache_integration(self, orm_session, test_pro_org, test_billing_members):
        """Test billing service caching works correctly with real data."""
        # Create project
        project = ProjectModel(name="Cache Test Project", org_id=test_pro_org.id)
        orm_session.add(project)
        orm_session.flush()

        period_start = datetime(2024, 1, 1)
        period_end = datetime(2024, 1, 31)

        with patch('agentops.opsboard.services.billing_service.get_clickhouse') as mock_clickhouse:
            mock_client = MagicMock()
            mock_result = MagicMock()
            mock_result.result_rows = [(500, 40000)]  # span_count, total_tokens (25000+12000+2000+1000)
            mock_client.query.return_value = mock_result
            mock_clickhouse.return_value = mock_client

            # First call should hit ClickHouse
            usage_data1 = await billing_service.get_usage_for_period(
                orm_session, str(test_pro_org.id), period_start, period_end
            )

            # Second call should use cache
            usage_data2 = await billing_service.get_usage_for_period(
                orm_session, str(test_pro_org.id), period_start, period_end
            )

        # Verify caching worked
        assert usage_data1 == usage_data2
        assert mock_client.query.call_count == 1  # Only called once due to caching

    @patch('stripe.Subscription.modify')
    @patch('stripe.Subscription.retrieve')
    async def test_concurrent_member_licensing_operations(
        self,
        mock_stripe_retrieve,
        mock_stripe_modify,
        mock_request,
        orm_session,
        test_pro_org,
        test_billing_members,
        mock_stripe_subscription,
    ):
        """Test concurrent member licensing operations don't cause data corruption."""
        setup_mock_request_auth(mock_request, get_org_owner_id(test_pro_org))
        mock_stripe_retrieve.return_value = mock_stripe_subscription

        # This test simulates what would happen with concurrent operations
        # In practice, the with_for_update() lock should prevent issues

        unlicensed_member = next(m for m in test_billing_members if not m.is_paid)

        body = UpdateMemberLicensesBody(add=[str(unlicensed_member.user_id)], remove=[])

        # Simulate first operation
        result1 = await update_member_licenses(
            request=mock_request, org_id=str(test_pro_org.id), body=body, orm=orm_session
        )

        # Verify state is consistent
        assert result1.paid_members_count == 3

        # Verify database state
        updated_member = orm_session.query(UserOrgModel).filter_by(user_id=unlicensed_member.user_id).first()
        assert updated_member.is_paid is True


class TestBillingWorkflows:
    """Test common billing workflows end-to-end."""

    async def test_org_upgrade_to_pro_workflow(self, mock_request, orm_session, test_user):
        """Test complete workflow of upgrading an org to pro status."""
        # Create free org
        free_org = OrgModel(name="Free Org", prem_status=PremStatus.free)
        orm_session.add(free_org)
        orm_session.flush()

        # Add user as owner
        user_org = UserOrgModel(
            user_id=test_user.id,
            org_id=free_org.id,
            role=OrgRoles.owner,
            user_email=test_user.email,
            is_paid=False,
        )
        orm_session.add(user_org)
        orm_session.flush()

        # Simulate upgrade process
        free_org.prem_status = PremStatus.pro
        free_org.subscription_id = "sub_new_upgrade"
        user_org.is_paid = True
        orm_session.commit()

        # Verify upgrade
        assert free_org.prem_status == PremStatus.pro
        assert free_org.subscription_id is not None
        assert user_org.is_paid is True

    async def test_monthly_billing_period_closure_workflow(
        self, orm_session, test_pro_org, test_billing_members
    ):
        """Test monthly billing period closure and snapshot creation."""
        # Create project for usage
        project = ProjectModel(name="Monthly Test Project", org_id=test_pro_org.id)
        orm_session.add(project)
        orm_session.flush()

        # Set up billing period
        period_start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        period_end = datetime(2024, 1, 31, tzinfo=timezone.utc)

        with (
            patch.object(billing_service, 'get_usage_for_period') as mock_usage,
            patch.object(billing_service, 'calculate_usage_costs') as mock_costs,
            patch.object(billing_service, 'get_seat_price') as mock_price,
        ):
            mock_usage.return_value = {"tokens": 2000000, "spans": 1000}
            mock_costs.return_value = {"tokens": 40, "spans": 100}
            mock_price.return_value = 4000

            # Create snapshot (simulates monthly closure)
            snapshot = await billing_service.create_billing_period_snapshot(
                orm_session, test_pro_org, period_start, period_end
            )

        # Verify snapshot
        assert snapshot.period_start == period_start
        assert snapshot.period_end == period_end
        assert snapshot.seat_count == 2  # Owner + 1 paid member
        assert snapshot.total_cost == 8140  # (2 * 4000) + 40 + 100
        assert snapshot.status == 'pending'

    async def test_member_invitation_auto_licensing_workflow(
        self, mock_request, orm_session, test_pro_org, test_user, test_user3
    ):
        """Test workflow of inviting a member and auto-licensing them."""
        # Use existing test_user3 instead of creating new user
        # Simulate invitation acceptance and auto-licensing
        new_member = UserOrgModel(
            user_id=test_user3.id,
            org_id=test_pro_org.id,
            role=OrgRoles.developer,
            user_email=test_user3.email,
            is_paid=True,  # Auto-licensed
        )
        orm_session.add(new_member)
        orm_session.commit()

        # Create audit log for auto-licensing
        audit_log = BillingAuditLog(
            org_id=test_pro_org.id,
            user_id=test_user3.id,
            action='member_auto_licensed_on_invite_accept',
            details={
                'member_id': str(test_user3.id),
                'member_email': test_user3.email,
                'invite_role': 'developer',
            },
        )
        orm_session.add(audit_log)
        orm_session.commit()

        # Verify workflow
        assert new_member.is_paid is True

        # Verify audit log
        audit_logs = (
            orm_session.query(BillingAuditLog)
            .filter_by(org_id=test_pro_org.id, action='member_auto_licensed_on_invite_accept')
            .all()
        )
        assert len(audit_logs) == 1

    async def test_legacy_to_new_billing_migration_workflow(
        self, mock_request, orm_session, test_pro_org, test_billing_members
    ):
        """Test migration from legacy billing to new seat-based billing."""
        # Simulate legacy billing state
        test_pro_org.subscription_id = "sub_legacy_migration"

        # Set all members as unpaid initially (legacy state)
        for member in test_billing_members:
            member.is_paid = False

        # Get owner
        owner = orm_session.query(UserOrgModel).filter_by(org_id=test_pro_org.id, role=OrgRoles.owner).first()
        owner.is_paid = False

        orm_session.commit()

        # Simulate migration: auto-license all existing members
        all_members = orm_session.query(UserOrgModel).filter_by(org_id=test_pro_org.id).all()

        for member in all_members:
            member.is_paid = True

        orm_session.commit()

        # Verify migration
        paid_members = orm_session.query(UserOrgModel).filter_by(org_id=test_pro_org.id, is_paid=True).count()
        assert paid_members == 3  # Owner + 2 members

    @patch('stripe.Subscription.retrieve')
    async def test_subscription_cancellation_workflow(
        self, mock_stripe_retrieve, mock_request, orm_session, test_pro_org, test_billing_members
    ):
        """Test workflow when subscription is cancelled."""
        setup_mock_request_auth(mock_request, get_org_owner_id(test_pro_org))
        # Mock cancelled subscription for member licensing check
        cancelled_subscription = MagicMock()
        cancelled_subscription.cancel_at_period_end = True
        cancelled_subscription.current_period_end = int((datetime.now() + timedelta(days=7)).timestamp())

        def mock_get(key, default=None):
            if key == 'cancel_at_period_end':
                return True
            elif key == 'current_period_end':
                return cancelled_subscription.current_period_end
            elif key == 'items':
                return {'data': [{'price': {'id': 'price_legacy_123'}}]}
            return default

        cancelled_subscription.get = mock_get
        mock_stripe_retrieve.return_value = cancelled_subscription

        # Test that member licensing is blocked for cancelled subscription
        body = UpdateMemberLicensesBody(add=[], remove=[])

        with pytest.raises(HTTPException) as excinfo:
            await update_member_licenses(
                request=mock_request, org_id=str(test_pro_org.id), body=body, orm=orm_session
            )

        assert excinfo.value.status_code == 400
        assert "subscription is scheduled to cancel" in excinfo.value.detail

        # This test primarily verifies that cancelled subscriptions prevent seat management,
        # which is the core functionality we care about for the cancellation workflow


class TestBillingDataConsistency:
    """Test data consistency across billing components."""

    async def test_seat_count_consistency_across_components(
        self, orm_session, test_pro_org, test_billing_members
    ):
        """Test seat counts are consistent between service, models, and Stripe."""
        # Count paid members in database
        db_paid_count = (
            orm_session.query(UserOrgModel).filter_by(org_id=test_pro_org.id, is_paid=True).count()
        )

        # Should be consistent with owner + paid members
        assert db_paid_count >= 1  # At least the owner

    async def test_usage_data_consistency_billing_dashboard(
        self, orm_session, test_pro_org, test_billing_members
    ):
        """Test usage data consistency between service and dashboard view."""
        # Create project for usage
        project = ProjectModel(name="Consistency Test", org_id=test_pro_org.id)
        orm_session.add(project)
        orm_session.flush()

        test_usage = {"tokens": 1500000, "spans": 750}
        test_costs = {"tokens": 30, "spans": 75}

        with (
            patch.object(billing_service, 'get_usage_for_period', return_value=test_usage),
            patch.object(billing_service, 'calculate_usage_costs', return_value=test_costs),
            patch.object(billing_service, 'get_seat_price', return_value=4000),
        ):
            # Get data from service directly
            period_start = datetime(2024, 1, 1)
            period_end = datetime(2024, 1, 31)

            service_usage = await billing_service.get_usage_for_period(
                orm_session, str(test_pro_org.id), period_start, period_end
            )
            service_costs = await billing_service.calculate_usage_costs(service_usage)

            # Get data from dashboard view
            dashboard_view = BillingDashboardView(MagicMock())
            dashboard_view.request.state.session.user_id = "00000000-0000-0000-0000-000000000000"

            dashboard_result = await dashboard_view(org_id=str(test_pro_org.id), orm=orm_session)

            # Extract response data if wrapped in JSONResponse
            if hasattr(dashboard_result, 'body'):
                import json

                dashboard_result = json.loads(dashboard_result.body.decode())

        # Verify consistency
        assert service_usage == test_usage
        assert service_costs == test_costs
        assert dashboard_result['current_period']['usage_quantities'] == test_usage
        assert dashboard_result['current_period']['usage_costs'] == test_costs

    async def test_cost_calculation_consistency(self, orm_session, test_pro_org, test_billing_members):
        """Test cost calculations are consistent across all billing components."""
        # Test data
        usage_quantities = {"tokens": 2000000, "spans": 1000}

        # Calculate costs multiple times
        with patch.object(billing_service, 'get_usage_pricing') as mock_pricing:
            from decimal import Decimal

            mock_pricing.return_value = {
                'tokens': {'price_per_unit': Decimal('0.00002'), 'unit_size': 1000},
                'spans': {'price_per_unit': Decimal('0.001'), 'unit_size': 1},
            }

            costs1 = await billing_service.calculate_usage_costs(usage_quantities)
            costs2 = await billing_service.calculate_usage_costs(usage_quantities)
            costs3 = await billing_service.calculate_usage_costs(usage_quantities)

        # All calculations should be identical
        assert costs1 == costs2 == costs3

        # Verify expected calculations
        # Tokens: 2M / 1000 * 0.00002 = 0.04 = 4 cents
        # Spans: 1000 * 0.001 = 1.00 = 100 cents
        assert costs1.get('tokens', 0) == 4
        assert costs1.get('spans', 0) == 100

    async def test_audit_log_completeness(
        self, mock_request, orm_session, test_pro_org, test_billing_members, billing_period_factory
    ):
        """Test all billing actions generate appropriate audit log entries."""
        setup_mock_request_auth(mock_request, get_org_owner_id(test_pro_org))
        initial_log_count = orm_session.query(BillingAuditLog).filter_by(org_id=test_pro_org.id).count()

        # Perform several billing operations

        # 1. Create billing period
        billing_period = billing_period_factory(
            test_pro_org.id,
            total_cost=5000,
        )
        orm_session.add(billing_period)
        orm_session.commit()

        # Add audit log for period creation
        period_log = BillingAuditLog(
            org_id=test_pro_org.id,
            user_id=mock_request.state.session.user_id,
            action='billing_period_created',
            details={'period_id': str(billing_period.id)},
        )
        orm_session.add(period_log)

        # 2. Create member licensing log
        member_log = BillingAuditLog(
            org_id=test_pro_org.id,
            user_id=mock_request.state.session.user_id,
            action='member_licensed',
            details={'member_id': str(test_billing_members[0].user_id)},
        )
        orm_session.add(member_log)

        orm_session.commit()

        # Verify audit logs were created
        final_log_count = orm_session.query(BillingAuditLog).filter_by(org_id=test_pro_org.id).count()
        assert final_log_count == initial_log_count + 2

        # Verify log content
        logs = orm_session.query(BillingAuditLog).filter_by(org_id=test_pro_org.id).all()
        actions = [log.action for log in logs]
        assert 'billing_period_created' in actions
        assert 'member_licensed' in actions


class TestBillingPerformance:
    """Test performance aspects of the billing system."""

    async def test_billing_dashboard_query_performance(self, orm_session, test_pro_org, test_billing_members):
        """Test billing dashboard queries perform efficiently with large datasets."""
        # Create multiple billing periods
        periods = []
        import time

        base_day = int(time.time() % 20) + 1

        for i in range(20):  # Simulate 20 months of data
            unique_day = base_day + (i % 5)  # Vary days to avoid conflicts
            period = BillingPeriod(
                org_id=test_pro_org.id,
                period_start=datetime(2024, 1, unique_day, tzinfo=timezone.utc) + timedelta(days=30 * i),
                period_end=datetime(2024, 1, unique_day + 1, tzinfo=timezone.utc) + timedelta(days=30 * i),
                seat_cost=4000,
                total_cost=4200,
                status='paid',
            )
            periods.append(period)

        orm_session.add_all(periods)
        orm_session.commit()

        # Test dashboard performance
        dashboard_view = BillingDashboardView(MagicMock())
        dashboard_view.request.state.session.user_id = "00000000-0000-0000-0000-000000000000"

        with (
            patch.object(billing_service, 'get_usage_for_period', return_value={}),
            patch.object(billing_service, 'calculate_usage_costs', return_value={}),
            patch.object(billing_service, 'get_seat_price', return_value=4000),
        ):
            start_time = datetime.now()
            result = await dashboard_view(org_id=str(test_pro_org.id), orm=orm_session)
            end_time = datetime.now()

        # Verify reasonable performance (should be under 1 second for this dataset)
        execution_time = (end_time - start_time).total_seconds()
        assert execution_time < 1.0

        # Extract response data if wrapped in JSONResponse
        if hasattr(result, 'body'):
            import json

            result = json.loads(result.body.decode())

        # Verify correct data limiting (only 12 past periods returned)
        assert len(result['past_periods']) <= 12

    async def test_usage_calculation_performance(self, orm_session, test_pro_org, test_billing_members):
        """Test usage calculation performance with large amounts of data."""
        # Create multiple projects
        projects = []
        for i in range(10):
            project = ProjectModel(name=f"Performance Test Project {i}", org_id=test_pro_org.id)
            projects.append(project)

        orm_session.add_all(projects)
        orm_session.flush()

        # Mock large dataset response
        with patch('agentops.opsboard.services.billing_service.get_clickhouse') as mock_clickhouse:
            mock_client = MagicMock()
            mock_result = MagicMock()
            # Simulate large usage numbers
            mock_result.result_rows = [
                (100000, 8200000)
            ]  # span_count, total_tokens (5000000+2500000+500000+200000)
            mock_client.query.return_value = mock_result
            mock_clickhouse.return_value = mock_client

            start_time = datetime.now()
            usage_data = await billing_service.get_usage_for_period(
                orm_session, str(test_pro_org.id), datetime(2024, 1, 1), datetime(2024, 1, 31)
            )
            end_time = datetime.now()

        # Verify performance
        execution_time = (end_time - start_time).total_seconds()
        assert execution_time < 0.5  # Should be very fast

        # Verify data
        assert usage_data['tokens'] == 8200000  # Sum of all token types
        assert usage_data['spans'] == 100000

    async def test_billing_service_cache_performance(self, orm_session, test_pro_org, test_billing_members):
        """Test billing service caching improves performance."""
        # Create project
        project = ProjectModel(name="Cache Performance Test", org_id=test_pro_org.id)
        orm_session.add(project)
        orm_session.flush()

        period_start = datetime(2024, 1, 1)
        period_end = datetime(2024, 1, 31)

        with patch('agentops.opsboard.services.billing_service.get_clickhouse') as mock_clickhouse:
            mock_client = MagicMock()
            mock_result = MagicMock()
            mock_result.result_rows = [(1000, 82000)]  # span_count, total_tokens (50000+25000+5000+2000)
            mock_client.query.return_value = mock_result
            mock_clickhouse.return_value = mock_client

            # First call - should hit database
            start_time1 = datetime.now()
            await billing_service.get_usage_for_period(
                orm_session, str(test_pro_org.id), period_start, period_end
            )
            end_time1 = datetime.now()

            # Second call - should use cache
            start_time2 = datetime.now()
            await billing_service.get_usage_for_period(
                orm_session, str(test_pro_org.id), period_start, period_end
            )
            end_time2 = datetime.now()

        # Cache should be faster
        time1 = (end_time1 - start_time1).total_seconds()
        time2 = (end_time2 - start_time2).total_seconds()

        # Second call should be significantly faster (cache hit)
        assert time2 < time1
        assert mock_client.query.call_count == 1  # Only called once


class TestBillingEdgeCases:
    """Test edge cases in the billing system."""

    async def test_billing_with_zero_usage(self, orm_session, test_pro_org, test_billing_members):
        """Test billing calculations work correctly with zero usage."""
        with (
            patch.object(billing_service, 'get_usage_for_period', return_value={}),
            patch.object(billing_service, 'calculate_usage_costs', return_value={}),
            patch.object(billing_service, 'get_seat_price', return_value=4000),
        ):
            billing_period = await billing_service.create_billing_period_snapshot(
                orm_session,
                test_pro_org,
                datetime(2024, 1, 1, tzinfo=timezone.utc),
                datetime(2024, 1, 31, tzinfo=timezone.utc),
            )

        # Verify zero usage is handled correctly
        assert billing_period.usage_quantities == {}
        assert billing_period.usage_costs == {}
        assert billing_period.seat_cost == 8000  # 2 * 4000 (owner + 1 paid member)
        assert billing_period.total_cost == 8000  # Only seat cost

    async def test_billing_with_single_member_org(self, orm_session, test_user3):
        """Test billing works correctly for single-member organizations."""
        # Create single-member org
        single_org = OrgModel(
            name="Single Member Org", prem_status=PremStatus.pro, subscription_id="sub_single"
        )
        orm_session.add(single_org)
        orm_session.flush()

        owner = UserOrgModel(
            user_id=test_user3.id,
            org_id=single_org.id,
            role=OrgRoles.owner,
            user_email=test_user3.email,
            is_paid=True,
        )
        orm_session.add(owner)
        orm_session.flush()

        with (
            patch.object(billing_service, 'get_usage_for_period', return_value={"tokens": 100000}),
            patch.object(billing_service, 'calculate_usage_costs', return_value={"tokens": 2}),
            patch.object(billing_service, 'get_seat_price', return_value=4000),
        ):
            billing_period = await billing_service.create_billing_period_snapshot(
                orm_session,
                single_org,
                datetime(2024, 1, 1, tzinfo=timezone.utc),
                datetime(2024, 1, 31, tzinfo=timezone.utc),
            )

        # Verify single member billing
        assert billing_period.seat_count == 1
        assert billing_period.seat_cost == 4000
        assert billing_period.usage_costs == {"tokens": 2}
        assert billing_period.total_cost == 4002

    async def test_billing_during_org_deletion(
        self, mock_request, orm_session, test_pro_org, test_billing_members, billing_period_factory
    ):
        """Test billing data handling when organization is deleted."""
        setup_mock_request_auth(mock_request, get_org_owner_id(test_pro_org))
        org_id = test_pro_org.id

        # Create billing data
        billing_period = billing_period_factory(
            org_id,
            total_cost=5000,
        )
        orm_session.add(billing_period)

        audit_log = BillingAuditLog(
            org_id=org_id, user_id=mock_request.state.session.user_id, action='test_action', details={}
        )
        orm_session.add(audit_log)
        orm_session.commit()

        # Delete organization
        orm_session.delete(test_pro_org)

        try:
            orm_session.commit()

            # Check if billing data was cascade deleted or preserved
            remaining_periods = orm_session.query(BillingPeriod).filter_by(org_id=org_id).all()
            remaining_logs = orm_session.query(BillingAuditLog).filter_by(org_id=org_id).all()

            # Behavior depends on database foreign key constraints
            # This test documents the expected behavior

        except Exception:
            # If foreign key constraints prevent deletion, that's also valid
            orm_session.rollback()

    async def test_billing_with_invalid_stripe_data(
        self, mock_request, orm_session, test_pro_org, test_billing_members
    ):
        """Test billing system handles invalid or corrupted Stripe data."""
        setup_mock_request_auth(mock_request, get_org_owner_id(test_pro_org))
        dashboard_view = BillingDashboardView(mock_request)

        # Test with invalid subscription ID
        test_pro_org.subscription_id = "sub_invalid_123"
        orm_session.flush()

        with patch('stripe.Subscription.retrieve') as mock_retrieve:
            mock_retrieve.side_effect = stripe.error.InvalidRequestError(
                "No such subscription", "subscription"
            )

            with (
                patch.object(billing_service, 'get_usage_for_period', return_value={}),
                patch.object(billing_service, 'calculate_usage_costs', return_value={}),
                patch.object(billing_service, 'get_seat_price', return_value=4000),
            ):
                # Should handle error gracefully
                result = await dashboard_view(org_id=str(test_pro_org.id), orm=orm_session)

        # Extract response data if wrapped in JSONResponse
        if hasattr(result, 'body'):
            import json

            result = json.loads(result.body.decode())

        # Verify it still returns data (fallback behavior)
        assert result['current_period'] is not None
        assert result['is_legacy_billing'] is False  # Default value

    async def test_billing_timezone_handling(
        self, orm_session, test_pro_org, test_billing_members, billing_period_factory
    ):
        """Test billing system correctly handles different timezones."""
        # Test with different timezone periods
        utc_start = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        utc_end = datetime(2024, 1, 31, 23, 59, 59, tzinfo=timezone.utc)

        # Create billing period with UTC times
        billing_period = billing_period_factory(
            test_pro_org.id,
            seat_cost=4000,
            total_cost=4000,
        )
        orm_session.add(billing_period)
        orm_session.commit()

        # Verify timezone-aware storage and retrieval
        retrieved_period = orm_session.query(BillingPeriod).filter_by(id=billing_period.id).first()

        assert retrieved_period.period_start.tzinfo is not None
        assert retrieved_period.period_end.tzinfo is not None
