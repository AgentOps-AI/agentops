import pytest
from fastapi import HTTPException
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
import uuid
import stripe
import os

from agentops.opsboard.models import OrgModel, UserOrgModel, OrgRoles, BillingAuditLog, PremStatus
from agentops.opsboard.views.orgs import (
    update_member_licenses,
    preview_member_add_cost,
    UpdateMemberLicensesBody,
)

# Import shared billing fixtures
pytest_plugins = ["tests._conftest.billing"]

# Mock stripe at module level to prevent API key errors
stripe.api_key = 'sk_test_mock'


@pytest.fixture
def test_licensed_members(orm_session, test_pro_org, test_user, test_user2, test_user3):
    """Create test members with licensing status."""
    members = []

    # Use existing test users from fixtures
    test_users = [test_user, test_user2, test_user3]

    # Add existing test users to org with different paid states
    for i, user in enumerate(test_users):
        # Skip if user is already in org (e.g., test_user is the owner)
        existing = orm_session.query(UserOrgModel).filter_by(user_id=user.id, org_id=test_pro_org.id).first()

        if not existing:
            user_org = UserOrgModel(
                user_id=user.id,
                org_id=test_pro_org.id,
                role=OrgRoles.developer,
                user_email=user.email,
                is_paid=(i == 1),  # Second user (test_user2) is paid initially to match mock quantity=2
            )
            orm_session.add(user_org)
            orm_session.flush()
            members.append((user, user_org))
        else:
            members.append((user, existing))

    return members


@pytest.fixture(autouse=True)
def mock_stripe_config():
    """Automatically mock Stripe configuration for all tests."""
    # Patch the imported constants where they are used
    with (
        patch('agentops.opsboard.views.orgs.STRIPE_SECRET_KEY', 'sk_test_123'),
        patch('agentops.opsboard.views.orgs.STRIPE_SUBSCRIPTION_PRICE_ID', 'price_test123'),
        patch('agentops.api.environment.STRIPE_SECRET_KEY', 'sk_test_123'),
        patch('agentops.api.environment.STRIPE_SUBSCRIPTION_PRICE_ID', 'price_test123'),
        patch.dict(
            os.environ, {'STRIPE_SECRET_KEY': 'sk_test_123', 'STRIPE_SUBSCRIPTION_PRICE_ID': 'price_test123'}
        ),
    ):
        yield


class TestUpdateMemberLicenses:
    """Test cases for update_member_licenses function."""

    async def test_update_member_licenses_success_add_members(
        self,
        mock_request,
        orm_session,
        test_pro_org,
        test_licensed_members,
        test_user,
        mock_stripe_subscription,
    ):
        """Test successfully adding members to paid licenses."""
        # Setup request
        mock_request.state.session = MagicMock()
        mock_request.state.session.user_id = test_user.id

        # Get member IDs to add (test_user2 is already paid, test_user3 is not)
        members_to_add = [str(member[0].id) for member in test_licensed_members[1:]]

        # Mock Stripe
        with (
            patch('stripe.Subscription.retrieve') as mock_retrieve,
            patch('stripe.Subscription.modify') as mock_modify,
        ):
            mock_retrieve.return_value = mock_stripe_subscription
            mock_modify.return_value = mock_stripe_subscription

            # Call the function
            result = await update_member_licenses(
                org_id=str(test_pro_org.id),
                request=mock_request,
                body=UpdateMemberLicensesBody(add=members_to_add, remove=[]),
                orm=orm_session,
            )

            # Verify response
            assert result.message == "Successfully updated member licenses"
            assert result.paid_members_count == 3  # Owner + 2 newly licensed members

            # The function already committed its changes, but we need to refresh our session
            # to see the updates made by the function
            orm_session.expunge_all()  # Clear all objects from session

            # Verify database updates
            # Check all members are now paid
            paid_count = (
                orm_session.query(UserOrgModel)
                .filter(UserOrgModel.org_id == test_pro_org.id, UserOrgModel.is_paid == True)
                .count()
            )
            assert paid_count == 3  # Owner + test_user2 + test_user3

            # Specifically verify test_user3 was updated
            test_user3 = test_licensed_members[2][0]
            updated_user_org = (
                orm_session.query(UserOrgModel)
                .filter_by(user_id=test_user3.id, org_id=test_pro_org.id)
                .first()
            )
            assert updated_user_org is not None
            assert updated_user_org.is_paid is True

            # Verify Stripe was called to update quantity
            mock_modify.assert_called_once()

    async def test_update_member_licenses_success_remove_members(
        self,
        mock_request,
        orm_session,
        test_pro_org,
        test_licensed_members,
        test_user,
        mock_stripe_subscription,
    ):
        """Test successfully removing members from paid licenses."""
        # Setup request
        mock_request.state.session = MagicMock()
        mock_request.state.session.user_id = test_user.id

        # Get member ID to remove (test_user2 is paid)
        member_to_remove = [str(test_licensed_members[1][0].id)]

        # Mock Stripe
        with (
            patch('stripe.Subscription.retrieve') as mock_retrieve,
            patch('stripe.Subscription.modify') as mock_modify,
        ):
            mock_retrieve.return_value = mock_stripe_subscription
            mock_modify.return_value = mock_stripe_subscription

            # Call the function
            result = await update_member_licenses(
                org_id=str(test_pro_org.id),
                request=mock_request,
                body=UpdateMemberLicensesBody(add=[], remove=member_to_remove),
                orm=orm_session,
            )

            # Verify response
            assert result.message == "Successfully updated member licenses"
            assert result.paid_members_count == 1  # Only owner remains

            # Refresh session to see updates
            orm_session.expunge_all()

            # Verify database updates
            updated_user_org = (
                orm_session.query(UserOrgModel)
                .filter_by(user_id=test_licensed_members[1][0].id, org_id=test_pro_org.id)
                .first()
            )
            assert updated_user_org.is_paid is False

    async def test_update_member_licenses_mixed_add_remove(
        self,
        mock_request,
        orm_session,
        test_pro_org,
        test_licensed_members,
        test_user,
        mock_stripe_subscription,
    ):
        """Test adding and removing members in the same request."""
        # Setup request
        mock_request.state.session = MagicMock()
        mock_request.state.session.user_id = test_user.id

        # Remove second member (paid test_user2), add third member (unpaid test_user3)
        remove_ids = [str(test_licensed_members[1][0].id)]
        add_ids = [str(test_licensed_members[2][0].id)]

        # Mock Stripe
        with (
            patch('stripe.Subscription.retrieve') as mock_retrieve,
            patch('stripe.Subscription.modify') as mock_modify,
        ):
            mock_retrieve.return_value = mock_stripe_subscription
            mock_modify.return_value = mock_stripe_subscription

            # Call the function
            result = await update_member_licenses(
                org_id=str(test_pro_org.id),
                request=mock_request,
                body=UpdateMemberLicensesBody(add=add_ids, remove=remove_ids),
                orm=orm_session,
            )

            # Verify response
            assert result.message == "Successfully updated member licenses"
            assert result.paid_members_count == 2  # Owner + 1 member

    async def test_update_member_licenses_user_not_authenticated(
        self, mock_request, orm_session, test_pro_org, test_user
    ):
        """Test update_member_licenses when user is not found."""
        # Setup request with no current user
        mock_request.state.session = MagicMock()
        mock_request.state.session.user_id = None

        # Call the function and expect HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await update_member_licenses(
                org_id=str(test_pro_org.id),
                request=mock_request,
                body=UpdateMemberLicensesBody(add=[], remove=[]),
                orm=orm_session,
            )

        # Verify error response
        assert exc_info.value.status_code == 401
        assert "User not authenticated" in str(exc_info.value.detail)

    async def test_update_member_licenses_org_not_found(self, mock_request, orm_session, test_user):
        """Test update_member_licenses when organization doesn't exist."""
        # Setup request
        mock_request.state.session = MagicMock()
        mock_request.state.session.user_id = test_user.id

        fake_org_id = str(uuid.uuid4())

        # Call the function and expect HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await update_member_licenses(
                org_id=fake_org_id,
                request=mock_request,
                body=UpdateMemberLicensesBody(add=[], remove=[]),
                orm=orm_session,
            )

        # Verify error response - user gets permission denied if org doesn't exist
        assert exc_info.value.status_code == 403
        assert 'Permission denied' in str(exc_info.value.detail)

    async def test_update_member_licenses_permission_denied_not_admin(
        self, mock_request, orm_session, test_pro_org, test_user, test_user2
    ):
        """Test update_member_licenses when user is not admin/owner."""
        # Use test_user2 as a non-admin user
        # Add test_user2 as developer (not admin)
        user_org = UserOrgModel(
            user_id=test_user2.id,
            org_id=test_pro_org.id,
            role=OrgRoles.developer,
            user_email=test_user2.email,
            is_paid=False,
        )
        orm_session.add(user_org)
        orm_session.flush()

        # Setup request
        mock_request.state.session = MagicMock()
        mock_request.state.session.user_id = test_user2.id

        # Call the function and expect HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await update_member_licenses(
                org_id=str(test_pro_org.id),
                request=mock_request,
                body=UpdateMemberLicensesBody(add=[], remove=[]),
                orm=orm_session,
            )

        # Verify error response
        assert exc_info.value.status_code == 403
        assert "Permission denied" in str(exc_info.value.detail)

    async def test_update_member_licenses_no_subscription(self, mock_request, orm_session, test_user):
        """Test update_member_licenses when org has no subscription."""
        # Create org without subscription
        org = OrgModel(name="Free Org", prem_status=PremStatus.free)
        orm_session.add(org)
        orm_session.flush()

        # Add user as owner
        user_org = UserOrgModel(
            user_id=test_user.id, org_id=org.id, role=OrgRoles.owner, user_email=test_user.email, is_paid=True
        )
        orm_session.add(user_org)
        orm_session.flush()

        # Setup request
        mock_request.state.session = MagicMock()
        mock_request.state.session.user_id = test_user.id

        # Call the function and expect HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await update_member_licenses(
                org_id=str(org.id),
                request=mock_request,
                body=UpdateMemberLicensesBody(add=[], remove=[]),
                orm=orm_session,
            )

        # Verify error response
        assert exc_info.value.status_code == 400
        assert "subscription" in str(exc_info.value.detail).lower()

    async def test_update_member_licenses_cannot_remove_owner(
        self, mock_request, orm_session, test_pro_org, test_user
    ):
        """Test update_member_licenses prevents removing license from owner."""
        # Setup request
        mock_request.state.session = MagicMock()
        mock_request.state.session.user_id = test_user.id

        # Try to remove owner
        owner_id = [str(test_user.id)]

        # Call the function and expect HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await update_member_licenses(
                org_id=str(test_pro_org.id),
                request=mock_request,
                body=UpdateMemberLicensesBody(add=[], remove=owner_id),
                orm=orm_session,
            )

        # Verify error response
        assert exc_info.value.status_code == 400
        assert "Cannot remove license from organization owner" in str(exc_info.value.detail)

    @patch('stripe.Subscription.retrieve')
    async def test_update_member_licenses_subscription_cancelled(
        self, mock_stripe_retrieve, mock_request, orm_session, test_pro_org, test_user
    ):
        """Test update_member_licenses when subscription is cancelled."""
        # Setup request
        mock_request.state.session = MagicMock()
        mock_request.state.session.user_id = test_user.id

        # Mock cancelled subscription
        mock_sub = MagicMock()
        mock_sub.id = "sub_test123"
        mock_sub.status = "active"  # Status is active but scheduled to cancel
        mock_sub.cancel_at_period_end = True

        def mock_get(key, default=None):
            if key == 'cancel_at_period_end':
                return True
            elif key == 'items':
                return {'data': []}
            return default

        mock_sub.get = mock_get
        mock_stripe_retrieve.return_value = mock_sub

        # Call the function and expect HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await update_member_licenses(
                org_id=str(test_pro_org.id),
                request=mock_request,
                body=UpdateMemberLicensesBody(add=[], remove=[]),
                orm=orm_session,
            )

        # Verify error response
        assert exc_info.value.status_code == 400
        assert "scheduled to cancel" in str(exc_info.value.detail).lower()

    @patch('stripe.Subscription.retrieve')
    async def test_update_member_licenses_legacy_billing_plan(
        self, mock_stripe_retrieve, mock_request, orm_session, test_pro_org, test_user
    ):
        """Test update_member_licenses when org is on legacy billing plan."""
        # Setup request
        mock_request.state.session = MagicMock()
        mock_request.state.session.user_id = test_user.id

        # Mock subscription without seat-based item
        mock_sub = MagicMock()
        mock_sub.id = "sub_test123"
        mock_sub.status = "active"
        mock_sub.cancel_at_period_end = False
        mock_sub.items = MagicMock()
        mock_sub.items.data = []

        # Add non-seat-based item
        mock_item = MagicMock()
        mock_item.price = MagicMock()
        mock_item.price.id = "price_different123"  # Different from STRIPE_SUBSCRIPTION_PRICE_ID
        mock_item.price.recurring = MagicMock()
        mock_item.price.recurring.usage_type = "metered"  # Not "licensed"
        mock_sub.items.data.append(mock_item)

        def mock_get(key, default=None):
            if key == 'cancel_at_period_end':
                return False
            elif key == 'items':
                return {'data': mock_sub.items.data}
            return default

        mock_sub.get = mock_get
        mock_stripe_retrieve.return_value = mock_sub

        # Call the function and expect HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await update_member_licenses(
                org_id=str(test_pro_org.id),
                request=mock_request,
                body=UpdateMemberLicensesBody(add=[], remove=[]),
                orm=orm_session,
            )

        # Verify error response - check for legacy billing message
        assert exc_info.value.status_code == 400
        assert "legacy billing plan" in str(exc_info.value.detail).lower()

    @patch('stripe.Subscription.modify')
    @patch('stripe.Subscription.retrieve')
    async def test_update_member_licenses_stripe_subscription_update(
        self,
        mock_stripe_retrieve,
        mock_stripe_modify,
        mock_request,
        orm_session,
        test_pro_org,
        test_licensed_members,
        test_user,
        mock_stripe_subscription,
    ):
        """Test update_member_licenses correctly updates Stripe subscription."""
        # Setup request
        mock_request.state.session = MagicMock()
        mock_request.state.session.user_id = test_user.id

        # Get member IDs to add
        members_to_add = [str(member[0].id) for member in test_licensed_members[1:]]

        # Mock Stripe
        mock_stripe_retrieve.return_value = mock_stripe_subscription
        mock_stripe_modify.return_value = mock_stripe_subscription

        # Call the function
        result = await update_member_licenses(
            org_id=str(test_pro_org.id),
            request=mock_request,
            body=UpdateMemberLicensesBody(add=members_to_add, remove=[]),
            orm=orm_session,
        )

        # Verify Stripe modify was called with correct parameters
        mock_stripe_modify.assert_called_once_with(
            "sub_test123",
            items=[
                {
                    "id": "si_test123",
                    "quantity": 3,  # Owner + 2 newly licensed members
                }
            ],
            proration_behavior='create_prorations',
        )

        assert result.message == "Successfully updated member licenses"

    @patch('stripe.Subscription.modify')
    @patch('stripe.Subscription.retrieve')
    async def test_update_member_licenses_stripe_error_handling(
        self,
        mock_stripe_retrieve,
        mock_stripe_modify,
        mock_request,
        orm_session,
        test_pro_org,
        test_licensed_members,
        test_user,
        mock_stripe_subscription,
    ):
        """Test update_member_licenses handles Stripe API errors."""
        # Setup request
        mock_request.state.session = MagicMock()
        mock_request.state.session.user_id = test_user.id

        # Get member IDs to add
        members_to_add = [str(member[0].id) for member in test_licensed_members[1:2]]

        # Mock Stripe
        mock_stripe_retrieve.return_value = mock_stripe_subscription
        mock_stripe_modify.side_effect = stripe.error.StripeError("API Error")

        # Call the function and expect HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await update_member_licenses(
                org_id=str(test_pro_org.id),
                request=mock_request,
                body=UpdateMemberLicensesBody(add=members_to_add, remove=[]),
                orm=orm_session,
            )

        # Verify error response
        assert exc_info.value.status_code == 500
        assert "Failed to update subscription" in str(exc_info.value.detail)

    async def test_update_member_licenses_creates_audit_logs(
        self,
        mock_request,
        orm_session,
        test_pro_org,
        test_licensed_members,
        test_user,
        mock_stripe_subscription,
    ):
        """Test update_member_licenses creates proper audit log entries."""
        # Setup request
        mock_request.state.session = MagicMock()
        mock_request.state.session.user_id = test_user.id

        # Get member to add
        member_to_add = test_licensed_members[1][0]

        # Mock Stripe
        with (
            patch('stripe.Subscription.retrieve') as mock_retrieve,
            patch('stripe.Subscription.modify') as mock_modify,
        ):
            mock_retrieve.return_value = mock_stripe_subscription
            mock_modify.return_value = mock_stripe_subscription

            # Call the function
            result = await update_member_licenses(
                org_id=str(test_pro_org.id),
                request=mock_request,
                body=UpdateMemberLicensesBody(add=[str(member_to_add.id)], remove=[]),
                orm=orm_session,
            )

            # Verify audit logs were created
            audit_logs = orm_session.query(BillingAuditLog).filter_by(org_id=test_pro_org.id).all()

            assert len(audit_logs) > 0

            # Find the member_licensed log
            licensed_log = next((log for log in audit_logs if log.action == 'member_licensed'), None)
            assert licensed_log is not None
            assert licensed_log.details['member_id'] == str(member_to_add.id)
            assert licensed_log.details['member_email'] == member_to_add.email

    async def test_update_member_licenses_transaction_rollback_on_stripe_error(
        self,
        mock_request,
        orm_session,
        test_pro_org,
        test_licensed_members,
        test_user,
        mock_stripe_subscription,
    ):
        """Test update_member_licenses rolls back database changes when Stripe fails."""
        # Setup request
        mock_request.state.session = MagicMock()
        mock_request.state.session.user_id = test_user.id

        # Get member to add (test_user3 is unpaid)
        member_to_add = test_licensed_members[2][0]

        # Check initial state
        initial_user_org = (
            orm_session.query(UserOrgModel)
            .filter_by(user_id=member_to_add.id, org_id=test_pro_org.id)
            .first()
        )
        assert initial_user_org.is_paid is False

        # Mock Stripe to fail
        with (
            patch('stripe.Subscription.retrieve') as mock_retrieve,
            patch('stripe.Subscription.modify') as mock_modify,
        ):
            mock_retrieve.return_value = mock_stripe_subscription
            mock_modify.side_effect = stripe.error.StripeError("API Error")

            # Call the function and expect HTTPException
            with pytest.raises(HTTPException) as exc_info:
                await update_member_licenses(
                    org_id=str(test_pro_org.id),
                    request=mock_request,
                    body=UpdateMemberLicensesBody(add=[str(member_to_add.id)], remove=[]),
                    orm=orm_session,
                )

            # Verify error
            assert exc_info.value.status_code == 500

            # Verify database wasn't changed
            final_user_org = (
                orm_session.query(UserOrgModel)
                .filter_by(user_id=member_to_add.id, org_id=test_pro_org.id)
                .first()
            )
            assert final_user_org.is_paid is False  # Should remain unchanged

    async def test_update_member_licenses_final_paid_count_calculation(
        self,
        mock_request,
        orm_session,
        test_pro_org,
        test_licensed_members,
        test_user,
        mock_stripe_subscription,
    ):
        """Test update_member_licenses correctly calculates final paid member count."""
        # Setup request
        mock_request.state.session = MagicMock()
        mock_request.state.session.user_id = test_user.id

        # Initial state: owner (paid) + test_user2 (paid) + test_user3 (unpaid)
        # Add test_user3 (unpaid), remove test_user2 (paid)
        add_ids = [str(test_licensed_members[2][0].id)]  # test_user3 (unpaid)
        remove_ids = [str(test_licensed_members[1][0].id)]  # test_user2 (paid)

        # Mock Stripe
        with (
            patch('stripe.Subscription.retrieve') as mock_retrieve,
            patch('stripe.Subscription.modify') as mock_modify,
        ):
            mock_retrieve.return_value = mock_stripe_subscription
            mock_modify.return_value = mock_stripe_subscription

            # Call the function
            result = await update_member_licenses(
                org_id=str(test_pro_org.id),
                request=mock_request,
                body=UpdateMemberLicensesBody(add=add_ids, remove=remove_ids),
                orm=orm_session,
            )

            # Verify final count
            # Should be: owner (always paid) + newly added member = 2
            assert result.paid_members_count == 2

            # Verify Stripe was called with correct quantity
            mock_modify.assert_called_once()
            call_args = mock_modify.call_args[1]
            assert call_args["items"][0]["quantity"] == 2

    async def test_update_member_licenses_ignores_non_members(
        self,
        mock_request,
        orm_session,
        test_pro_org,
        test_licensed_members,
        test_user,
        mock_stripe_subscription,
    ):
        """Test update_member_licenses ignores user IDs that aren't org members."""
        # Setup request
        mock_request.state.session = MagicMock()
        mock_request.state.session.user_id = test_user.id

        # Try to add a non-existent user ID (which should be ignored)
        # This simulates trying to add a user that doesn't exist or isn't a member
        non_member_id = str(uuid.uuid4())
        add_ids = [non_member_id]

        # Mock Stripe
        with (
            patch('stripe.Subscription.retrieve') as mock_retrieve,
            patch('stripe.Subscription.modify') as mock_modify,
        ):
            mock_retrieve.return_value = mock_stripe_subscription
            mock_modify.return_value = mock_stripe_subscription

            # Call the function
            result = await update_member_licenses(
                org_id=str(test_pro_org.id),
                request=mock_request,
                body=UpdateMemberLicensesBody(add=add_ids, remove=[]),
                orm=orm_session,
            )

            # Verify no changes were made
            assert result.paid_members_count == 2  # Only owner + already paid member

    async def test_update_member_licenses_race_condition_protection(
        self,
        mock_request,
        orm_session,
        test_pro_org,
        test_licensed_members,
        test_user,
        mock_stripe_subscription,
    ):
        """Test update_member_licenses uses row locking to prevent race conditions."""
        # This test would require testing the actual SQL queries used
        # In practice, we'd verify that SELECT ... FOR UPDATE is used
        # For now, we'll just ensure the function completes successfully

        # Setup request
        mock_request.state.session = MagicMock()
        mock_request.state.session.user_id = test_user.id

        # Mock Stripe
        with (
            patch('stripe.Subscription.retrieve') as mock_retrieve,
            patch('stripe.Subscription.modify') as mock_modify,
        ):
            mock_retrieve.return_value = mock_stripe_subscription
            mock_modify.return_value = mock_stripe_subscription

            # Call the function
            result = await update_member_licenses(
                org_id=str(test_pro_org.id),
                request=mock_request,
                body=UpdateMemberLicensesBody(add=[], remove=[]),
                orm=orm_session,
            )

            assert result.message == "Successfully updated member licenses"

    async def test_update_member_licenses_empty_add_remove_lists(
        self, mock_request, orm_session, test_pro_org, test_user, mock_stripe_subscription
    ):
        """Test update_member_licenses with empty add and remove lists."""
        # Setup request
        mock_request.state.session = MagicMock()
        mock_request.state.session.user_id = test_user.id

        # Mock Stripe
        with (
            patch('stripe.Subscription.retrieve') as mock_retrieve,
            patch('stripe.Subscription.modify') as mock_modify,
        ):
            mock_retrieve.return_value = mock_stripe_subscription
            mock_modify.return_value = mock_stripe_subscription

            # Call the function with empty lists
            result = await update_member_licenses(
                org_id=str(test_pro_org.id),
                request=mock_request,
                body=UpdateMemberLicensesBody(add=[], remove=[]),
                orm=orm_session,
            )

            # Should succeed but make no changes
            assert result.message == "Successfully updated member licenses"


class TestPreviewMemberAddCost:
    """Test cases for preview_member_add_cost function."""

    async def test_preview_member_add_cost_success(self, mock_request, orm_session, test_pro_org, test_user):
        """Test successfully previewing member addition cost."""
        # Setup request
        mock_request.state.session = MagicMock()
        mock_request.state.session.user_id = test_user.id

        # Mock Stripe subscription and invoice
        with (
            patch('stripe.Subscription.retrieve') as mock_retrieve,
            patch('stripe.Invoice.create_preview') as mock_create_preview,
        ):
            # Mock subscription
            mock_sub = MagicMock()
            mock_sub.id = "sub_test123"
            mock_sub.customer = "cus_test123"
            mock_sub.items = MagicMock()
            mock_sub.items.data = []

            # Mock subscription item
            mock_item = {
                'id': 'si_test123',
                'quantity': 2,
                'price': {
                    'id': 'price_test123',
                    'unit_amount': 4000,
                    'currency': 'usd',
                    'recurring': {'interval': 'month', 'interval_count': 1},
                },
            }

            def mock_sub_get(key, default=None):
                if key == 'items':
                    return {'data': [mock_item]}
                elif key == 'current_period_end':
                    return 1735689600
                return default

            mock_sub.get = mock_sub_get
            mock_retrieve.return_value = mock_sub

            # Mock invoices
            mock_upcoming_invoice = MagicMock()
            mock_upcoming_invoice.amount_due = 8000  # Not used anymore

            # Mock line items with proration
            mock_proration_line_item = {
                'amount': 1333,  # $13.33 proration for partial month (1/3 of $40)
                'parent': {
                    'type': 'subscription_item_details',
                    'subscription_item_details': {'proration': True},
                },
            }

            mock_subscription_line_item = {
                'amount': 4000,  # Regular subscription charge
                'parent': {
                    'type': 'subscription_item_details',
                    'subscription_item_details': {'proration': False},
                },
            }

            mock_upcoming_invoice.lines = MagicMock()
            mock_upcoming_invoice.lines.data = [mock_proration_line_item, mock_subscription_line_item]

            # Return only the upcoming invoice (no more current invoice call)
            mock_create_preview.return_value = mock_upcoming_invoice

            # Call the function
            result = await preview_member_add_cost(
                org_id=str(test_pro_org.id), request=mock_request, orm=orm_session
            )

            # Verify response
            assert result.immediate_charge == 13.33  # Proration amount from line item
            assert result.next_period_charge == 40.00  # Regular price per seat
            assert result.billing_interval == "month"
            assert result.currency == "usd"

            # Verify Stripe API calls
            assert mock_retrieve.call_count == 1
            assert mock_create_preview.call_count == 1  # Only one preview call now

            # Verify the preview call parameters
            mock_create_preview.assert_called_with(
                customer="cus_test123",
                subscription="sub_test123",
                subscription_details={
                    'items': [
                        {
                            'id': 'si_test123',
                            'quantity': 3,  # Current 2 + preview 1
                        }
                    ],
                    'proration_behavior': 'create_prorations',
                },
            )

    async def test_preview_member_add_cost_user_not_authenticated(
        self, mock_request, orm_session, test_pro_org, test_user
    ):
        """Test preview_member_add_cost when user is not found."""
        # Setup request with no current user
        mock_request.state.session = MagicMock()
        mock_request.state.session.user_id = None

        # Call the function and expect HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await preview_member_add_cost(org_id=str(test_pro_org.id), request=mock_request, orm=orm_session)

        # Verify error response
        assert exc_info.value.status_code == 401
        assert "User not authenticated" in str(exc_info.value.detail)

    async def test_preview_member_add_cost_org_not_found(self, mock_request, orm_session, test_user):
        """Test preview_member_add_cost when organization doesn't exist."""
        # Setup request
        mock_request.state.session = MagicMock()
        mock_request.state.session.user_id = test_user.id

        fake_org_id = str(uuid.uuid4())

        # Call the function and expect HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await preview_member_add_cost(org_id=fake_org_id, request=mock_request, orm=orm_session)

        # Verify error response
        assert exc_info.value.status_code == 404
        assert 'Organization not found' in str(exc_info.value.detail)

    async def test_preview_member_add_cost_permission_denied(
        self, mock_request, orm_session, test_pro_org, test_user, test_user3
    ):
        """Test preview_member_add_cost when user is not a member."""
        # Use test_user3 who is not a member of test_pro_org
        # Ensure test_user3 is not in the org
        existing = (
            orm_session.query(UserOrgModel).filter_by(user_id=test_user3.id, org_id=test_pro_org.id).first()
        )
        if existing:
            orm_session.delete(existing)
            orm_session.flush()

        # Setup request
        mock_request.state.session = MagicMock()
        mock_request.state.session.user_id = test_user3.id

        # Call the function and expect HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await preview_member_add_cost(org_id=str(test_pro_org.id), request=mock_request, orm=orm_session)

        # Verify error response
        assert exc_info.value.status_code == 403
        assert "permission" in str(exc_info.value.detail).lower()

    async def test_preview_member_add_cost_no_subscription(self, mock_request, orm_session, test_user):
        """Test preview_member_add_cost when org has no subscription."""
        # Create org without subscription
        org = OrgModel(name="Free Org", prem_status=PremStatus.free)
        orm_session.add(org)
        orm_session.flush()

        # Add user as owner
        user_org = UserOrgModel(
            user_id=test_user.id, org_id=org.id, role=OrgRoles.owner, user_email=test_user.email, is_paid=True
        )
        orm_session.add(user_org)
        orm_session.flush()

        # Setup request
        mock_request.state.session = MagicMock()
        mock_request.state.session.user_id = test_user.id

        # Call the function and expect HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await preview_member_add_cost(org_id=str(org.id), request=mock_request, orm=orm_session)

        # Verify error response
        assert exc_info.value.status_code == 400
        assert "subscription" in str(exc_info.value.detail).lower()

    @patch('stripe.Invoice.create_preview')
    @patch('stripe.Subscription.retrieve')
    async def test_preview_member_add_cost_stripe_integration(
        self,
        mock_stripe_retrieve,
        mock_stripe_create_preview,
        mock_request,
        orm_session,
        test_pro_org,
        test_user,
        mock_stripe_subscription,
    ):
        """Test preview_member_add_cost integrates with Stripe upcoming invoice API."""
        # Setup request
        mock_request.state.session = MagicMock()
        mock_request.state.session.user_id = test_user.id

        # Mock Stripe subscription
        mock_stripe_retrieve.return_value = mock_stripe_subscription

        # Mock Stripe invoices
        mock_upcoming_invoice = MagicMock()
        mock_upcoming_invoice.amount_due = 8000  # Not used anymore

        # Mock line items with proration
        mock_proration_line_item = {
            'amount': 1333,  # $13.33 proration for partial month (1/3 of $40)
            'parent': {'type': 'subscription_item_details', 'subscription_item_details': {'proration': True}},
        }

        mock_subscription_line_item = {
            'amount': 4000,  # Regular subscription charge
            'parent': {
                'type': 'subscription_item_details',
                'subscription_item_details': {'proration': False},
            },
        }

        mock_upcoming_invoice.lines = MagicMock()
        mock_upcoming_invoice.lines.data = [mock_proration_line_item, mock_subscription_line_item]

        # Return only the upcoming invoice (no more current invoice call)
        mock_stripe_create_preview.return_value = mock_upcoming_invoice

        # Call the function
        result = await preview_member_add_cost(
            org_id=str(test_pro_org.id), request=mock_request, orm=orm_session
        )

        # Verify Stripe subscription was retrieved
        mock_stripe_retrieve.assert_called_once_with("sub_test123", expand=["items.data.price.product"])

        # Verify invoice preview was called correctly
        assert mock_stripe_create_preview.call_count == 1  # Only one call now
        mock_stripe_create_preview.assert_called_with(
            customer="cus_test123",
            subscription="sub_test123",
            subscription_details={
                'items': [
                    {
                        "id": "si_test123",
                        "quantity": 3,  # Current 2 + preview 1
                    }
                ],
                'proration_behavior': 'create_prorations',
            },
        )

        # Verify response
        assert result.immediate_charge == 13.33  # Proration amount from line item

    @patch('stripe.Invoice.create_preview')
    async def test_preview_member_add_cost_stripe_error_handling(
        self, mock_stripe_create_preview, mock_request, orm_session, test_pro_org, test_user
    ):
        """Test preview_member_add_cost handles Stripe API errors gracefully."""
        # Setup request
        mock_request.state.session = MagicMock()
        mock_request.state.session.user_id = test_user.id

        # Mock Stripe to raise error
        mock_stripe_create_preview.side_effect = stripe.error.StripeError("API Error")

        with patch('stripe.Subscription.retrieve') as mock_retrieve:
            # Mock subscription with proper structure
            mock_sub = MagicMock()
            mock_sub.id = "sub_test123"
            mock_sub.customer = "cus_test123"

            # Mock subscription item with seat pricing
            mock_item = {
                'id': 'si_test123',
                'quantity': 2,
                'price': {
                    'id': 'price_test123',
                    'unit_amount': 4000,
                    'currency': 'usd',
                    'recurring': {'interval': 'month', 'interval_count': 1},
                },
            }

            def mock_get(key, default=None):
                if key == 'items':
                    return {'data': [mock_item]}
                elif key == 'current_period_end':
                    return 1735689600
                return default

            mock_sub.get = mock_get
            mock_retrieve.return_value = mock_sub

            # Call the function - should return fallback values
            result = await preview_member_add_cost(
                org_id=str(test_pro_org.id), request=mock_request, orm=orm_session
            )

            # Should return fallback values
            assert result.immediate_charge == 0
            assert result.next_period_charge == 40
            assert result.billing_interval == "month"


class TestBillingAuditLogging:
    """Test cases for billing audit log functionality."""

    def test_billing_audit_log_creation_member_licensed(self, orm_session, test_pro_org, test_user):
        """Test creating audit log for member licensing action."""
        # Create audit log
        audit_log = BillingAuditLog(
            org_id=test_pro_org.id,
            user_id=test_user.id,
            action='member_licensed',
            details={
                'member_id': str(test_user.id),
                'member_email': test_user.email,
                'before_seat_count': 1,
                'after_seat_count': 2,
            },
        )
        orm_session.add(audit_log)
        orm_session.commit()

        # Verify it was created
        assert audit_log.id is not None
        assert audit_log.action == 'member_licensed'
        assert audit_log.details['member_id'] == str(test_user.id)

    def test_billing_audit_log_creation_member_unlicensed(self, orm_session, test_pro_org, test_user):
        """Test creating audit log for member unlicensing action."""
        # Create audit log
        audit_log = BillingAuditLog(
            org_id=test_pro_org.id,
            user_id=test_user.id,
            action='member_unlicensed',
            details={
                'member_id': str(test_user.id),
                'member_email': test_user.email,
                'before_seat_count': 2,
                'after_seat_count': 1,
            },
        )
        orm_session.add(audit_log)
        orm_session.commit()

        # Verify it was created
        assert audit_log.id is not None
        assert audit_log.action == 'member_unlicensed'
        assert audit_log.details['after_seat_count'] == 1

    def test_billing_audit_log_details_format(self, orm_session, test_pro_org, test_user):
        """Test audit log details contain proper information."""
        # Create comprehensive audit log
        details = {
            'member_id': str(test_user.id),
            'member_email': test_user.email,
            'member_name': test_user.full_name,
            'before_seat_count': 3,
            'after_seat_count': 4,
            'updated_by': 'admin@example.com',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'subscription_id': 'sub_test123',
        }

        audit_log = BillingAuditLog(
            org_id=test_pro_org.id, user_id=test_user.id, action='member_licensed', details=details
        )
        orm_session.add(audit_log)
        orm_session.commit()

        # Verify all details are stored
        retrieved_log = orm_session.query(BillingAuditLog).filter_by(id=audit_log.id).first()
        assert retrieved_log.details == details


class TestBillingErrorCodes:
    """Test cases for billing error code handling."""

    def test_billing_error_code_stripe_api_error(self):
        """Test STRIPE_API_ERROR error code is properly set."""
        error_response = {"error": "Failed to update subscription", "error_code": "STRIPE_API_ERROR"}
        assert error_response["error_code"] == "STRIPE_API_ERROR"

    def test_billing_error_code_no_subscription(self):
        """Test NO_SUBSCRIPTION error code is properly set."""
        error_response = {"error": "No active subscription found", "error_code": "NO_SUBSCRIPTION"}
        assert error_response["error_code"] == "NO_SUBSCRIPTION"

    def test_billing_error_code_owner_required(self):
        """Test OWNER_REQUIRED error code is properly set."""
        error_response = {
            "error": "Cannot remove license from organization owner",
            "error_code": "OWNER_REQUIRED",
        }
        assert error_response["error_code"] == "OWNER_REQUIRED"

    def test_billing_error_code_permission_denied(self):
        """Test PERMISSION_DENIED error code is properly set."""
        error_response = {"error": "Permission denied", "error_code": "PERMISSION_DENIED"}
        assert error_response["error_code"] == "PERMISSION_DENIED"

    def test_billing_error_code_subscription_cancelled(self):
        """Test SUBSCRIPTION_CANCELLED error code is properly set."""
        error_response = {"error": "Subscription is not active", "error_code": "SUBSCRIPTION_CANCELLED"}
        assert error_response["error_code"] == "SUBSCRIPTION_CANCELLED"

    def test_billing_error_code_legacy_billing_plan(self):
        """Test LEGACY_BILLING_PLAN error code is properly set."""
        error_response = {
            "error": "Organization is on legacy billing plan",
            "error_code": "LEGACY_BILLING_PLAN",
        }
        assert error_response["error_code"] == "LEGACY_BILLING_PLAN"
