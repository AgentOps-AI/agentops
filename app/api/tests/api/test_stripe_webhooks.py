"""
Tests for Stripe webhook handlers.

This test suite validates the fix for the reference ID issue where legacy subscriptions
sunset via scripts/sunset_legacy_subscriptions.py could create checkout sessions with
missing client_reference_id, causing webhook processing failures.

The tests follow the same patterns as other billing tests and validate the fallback
mechanism that uses org_id from metadata when client_reference_id is missing.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from fastapi import HTTPException
import stripe

# Import shared billing fixtures
pytest_plugins = ["tests._conftest.billing"]

from agentops.api.routes.v4.stripe_webhooks import (
    handle_checkout_completed,
    handle_subscription_updated,
)
from agentops.opsboard.models import (
    OrgModel,
    UserOrgModel,
    BillingAuditLog,
    PremStatus,
    OrgRoles,
)


# Mock stripe at module level to prevent API key errors
stripe.api_key = 'sk_test_mock'


@pytest.fixture(autouse=True)
def mock_stripe_config():
    """Mock Stripe configuration for all tests."""
    with (
        patch('agentops.api.environment.STRIPE_SECRET_KEY', 'sk_test_123'),
        patch('agentops.api.environment.STRIPE_SUBSCRIPTION_PRICE_ID', 'price_test123'),
        patch('agentops.api.routes.v4.stripe_webhooks.STRIPE_SUBSCRIPTION_PRICE_ID', 'price_test123'),
        patch.dict(
            'os.environ',
            {'STRIPE_SECRET_KEY': 'sk_test_123', 'STRIPE_SUBSCRIPTION_PRICE_ID': 'price_test123'},
        ),
    ):
        yield


@pytest.fixture
def test_org_with_subscription(orm_session, test_user):
    """Create a test organization with an active subscription."""
    org = OrgModel(name="Test Org", prem_status=PremStatus.pro, subscription_id="sub_test_123")
    orm_session.add(org)
    orm_session.flush()

    # Add owner member
    owner_member = UserOrgModel(
        user_id=test_user.id, org_id=org.id, role=OrgRoles.owner, user_email=test_user.email, is_paid=True
    )
    orm_session.add(owner_member)
    orm_session.flush()

    return org


@pytest.fixture
def test_free_org(orm_session, test_user):
    """Create a test organization without a subscription."""
    org = OrgModel(name="Test Free Org", prem_status=PremStatus.free, subscription_id=None)
    orm_session.add(org)
    orm_session.flush()

    # Add owner member
    owner_member = UserOrgModel(
        user_id=test_user.id, org_id=org.id, role=OrgRoles.owner, user_email=test_user.email, is_paid=False
    )
    orm_session.add(owner_member)
    orm_session.flush()

    return org


@pytest.fixture
def mock_checkout_event():
    """Create a mock Stripe checkout.session.completed event."""
    event = MagicMock()
    event.id = "evt_test_123"
    event.type = "checkout.session.completed"
    event.data = MagicMock()
    event.data.object = {
        "id": "cs_test_session_123",
        "subscription": "sub_new_123",
        "client_reference_id": None,  # This will be set per test
        "metadata": {},  # This will be set per test
    }
    return event


@pytest.fixture
def mock_subscription_event():
    """Create a mock Stripe subscription.updated event."""
    event = MagicMock()
    event.id = "evt_test_subscription_123"
    event.type = "subscription.updated"
    event.data = MagicMock()
    event.data.object = {
        "id": "sub_test_123",
        "status": "active",
        "current_period_end": int((datetime.now() + timedelta(days=30)).timestamp()),
        "cancel_at_period_end": False,
        "items": {"data": [{"id": "si_test_123", "quantity": 1, "price": {"id": "price_test123"}}]},
    }
    return event


@pytest.fixture
def mock_legacy_subscription_event():
    """Create a mock Stripe subscription.updated event for legacy subscription."""
    event = MagicMock()
    event.id = "evt_test_legacy_123"
    event.type = "subscription.updated"
    event.data = MagicMock()
    event.data.object = {
        "id": "sub_legacy_123",
        "status": "active",
        "current_period_end": int((datetime.now() + timedelta(days=30)).timestamp()),
        "cancel_at_period_end": False,
        "items": {
            "data": [
                {
                    "id": "si_legacy_123",
                    "quantity": 1,
                    "price": {
                        "id": "price_legacy_old_123",  # Different from current price ID
                        "product": {"name": "Legacy Seat Plan"},
                    },
                }
            ]
        },
    }
    return event


class TestStripeWebhooks:
    """Test Stripe webhook handlers."""

    @pytest.mark.asyncio
    @patch('agentops.api.routes.v4.stripe_webhooks.is_event_processed')
    @patch('agentops.api.routes.v4.stripe_webhooks.mark_event_processed')
    @patch('agentops.api.routes.v4.stripe_webhooks.log_webhook_metric')
    @patch('stripe.Subscription.retrieve')
    async def test_checkout_completed_with_client_reference_id(
        self,
        mock_stripe_retrieve,
        mock_log_metric,
        mock_mark_processed,
        mock_is_processed,
        orm_session,
        test_free_org,
        mock_checkout_event,
        mock_stripe_subscription,
    ):
        """Test successful checkout completion with client_reference_id present."""
        mock_is_processed.return_value = False
        mock_mark_processed.return_value = None
        mock_stripe_retrieve.return_value = mock_stripe_subscription

        # Set the client_reference_id to the org ID
        mock_checkout_event.data.object["client_reference_id"] = str(test_free_org.id)

        result = await handle_checkout_completed(mock_checkout_event, orm_session)

        # Verify the org was updated
        orm_session.refresh(test_free_org)
        assert test_free_org.subscription_id == "sub_new_123"
        assert test_free_org.prem_status == PremStatus.pro

        # Verify owner was marked as paid
        owner = (
            orm_session.query(UserOrgModel)
            .filter(UserOrgModel.org_id == test_free_org.id, UserOrgModel.role == OrgRoles.owner)
            .first()
        )
        assert owner.is_paid is True

        mock_mark_processed.assert_called_once_with(mock_checkout_event.id, orm_session)

    @pytest.mark.asyncio
    @patch('agentops.api.routes.v4.stripe_webhooks.is_event_processed')
    @patch('agentops.api.routes.v4.stripe_webhooks.mark_event_processed')
    @patch('agentops.api.routes.v4.stripe_webhooks.log_webhook_metric')
    @patch('stripe.Subscription.retrieve')
    async def test_checkout_completed_missing_reference_id_with_metadata_fallback(
        self,
        mock_stripe_retrieve,
        mock_log_metric,
        mock_mark_processed,
        mock_is_processed,
        orm_session,
        test_free_org,
        mock_checkout_event,
        mock_stripe_subscription,
    ):
        """Test checkout completion when client_reference_id is missing but org_id is in metadata."""
        mock_is_processed.return_value = False
        mock_mark_processed.return_value = None
        mock_stripe_retrieve.return_value = mock_stripe_subscription

        # Simulate the scenario where client_reference_id is missing but org_id is in metadata
        mock_checkout_event.data.object["client_reference_id"] = None
        mock_checkout_event.data.object["metadata"] = {"org_id": str(test_free_org.id)}

        result = await handle_checkout_completed(mock_checkout_event, orm_session)

        # Verify the org was updated despite missing client_reference_id
        orm_session.refresh(test_free_org)
        assert test_free_org.subscription_id == "sub_new_123"
        assert test_free_org.prem_status == PremStatus.pro

        # Verify owner was marked as paid
        owner = (
            orm_session.query(UserOrgModel)
            .filter(UserOrgModel.org_id == test_free_org.id, UserOrgModel.role == OrgRoles.owner)
            .first()
        )
        assert owner.is_paid is True

        mock_mark_processed.assert_called_once_with(mock_checkout_event.id, orm_session)

        # Verify that the Stripe subscription was retrieved to validate the purchase
        mock_stripe_retrieve.assert_called_once_with("sub_new_123", expand=['items'])

        # This test specifically validates the fix for the reference ID issue
        # The warning should be logged when using metadata fallback (captured in test output)

    @pytest.mark.asyncio
    @patch('agentops.api.routes.v4.stripe_webhooks.is_event_processed')
    @patch('agentops.api.routes.v4.stripe_webhooks.log_webhook_metric')
    async def test_checkout_completed_missing_reference_id_and_metadata(
        self, mock_log_metric, mock_is_processed, orm_session, test_free_org, mock_checkout_event
    ):
        """Test checkout completion when both client_reference_id and org_id metadata are missing."""
        mock_is_processed.return_value = False

        # Simulate the scenario where both client_reference_id and org_id metadata are missing
        mock_checkout_event.data.object["client_reference_id"] = None
        mock_checkout_event.data.object["metadata"] = {}

        result = await handle_checkout_completed(mock_checkout_event, orm_session)

        # Should return early without processing
        assert result is None

        # Verify metric was logged for missing reference ID
        mock_log_metric.assert_called_once_with(
            "checkout.session.completed",
            "missing_reference_id",
            {"session_id": "cs_test_session_123", "subscription_id": "sub_new_123"},
        )

        # Verify org was not updated
        orm_session.refresh(test_free_org)
        assert test_free_org.subscription_id is None
        assert test_free_org.prem_status == PremStatus.free

    @pytest.mark.asyncio
    @patch('agentops.api.routes.v4.stripe_webhooks.is_event_processed')
    @patch('agentops.api.routes.v4.stripe_webhooks.log_webhook_metric')
    @patch('stripe.Subscription.retrieve')
    async def test_checkout_completed_org_not_found(
        self,
        mock_stripe_retrieve,
        mock_log_metric,
        mock_is_processed,
        orm_session,
        mock_checkout_event,
        mock_stripe_subscription,
    ):
        """Test checkout completion when org is not found."""
        mock_is_processed.return_value = False
        mock_stripe_retrieve.return_value = mock_stripe_subscription

        # Set client_reference_id to a non-existent org ID
        mock_checkout_event.data.object["client_reference_id"] = "00000000-0000-0000-0000-000000000000"

        result = await handle_checkout_completed(mock_checkout_event, orm_session)

        # Verify metric was logged for org not found
        mock_log_metric.assert_called_once_with(
            "checkout.session.completed",
            "org_not_found",
            {
                "client_reference_id": "00000000-0000-0000-0000-000000000000",
                "subscription_id": "sub_new_123",
                "session_id": "cs_test_session_123",
            },
        )

    @pytest.mark.asyncio
    @patch('agentops.api.routes.v4.stripe_webhooks.is_event_processed')
    @patch('agentops.api.routes.v4.stripe_webhooks.mark_event_processed')
    @patch('agentops.api.routes.v4.stripe_webhooks.log_webhook_metric')
    @patch('stripe.Subscription.retrieve')
    async def test_checkout_completed_duplicate_processing(
        self,
        mock_stripe_retrieve,
        mock_log_metric,
        mock_mark_processed,
        mock_is_processed,
        orm_session,
        test_org_with_subscription,
        mock_checkout_event,
        mock_stripe_subscription,
    ):
        """Test checkout completion when org already has the same subscription."""
        mock_is_processed.return_value = False
        mock_stripe_retrieve.return_value = mock_stripe_subscription

        # Set up scenario where org already has this subscription
        test_org_with_subscription.subscription_id = "sub_new_123"
        orm_session.commit()

        mock_checkout_event.data.object["client_reference_id"] = str(test_org_with_subscription.id)
        mock_checkout_event.data.object["subscription"] = "sub_new_123"

        result = await handle_checkout_completed(mock_checkout_event, orm_session)

        # Should return early due to duplicate subscription
        assert result is None

        # Should not call mark_event_processed since it's a duplicate
        mock_mark_processed.assert_not_called()

        # Should log the duplicate processing
        mock_log_metric.assert_called_once_with(
            "checkout.session.completed",
            "duplicate_processing",
            {"org_id": str(test_org_with_subscription.id), "subscription_id": "sub_new_123"},
        )

    @pytest.mark.asyncio
    @patch('agentops.api.routes.v4.stripe_webhooks.is_event_processed')
    @patch('agentops.api.routes.v4.stripe_webhooks.mark_event_processed')
    @patch('stripe.Subscription.modify')
    @patch('agentops.api.routes.v4.stripe_webhooks.send_legacy_billing_notification')
    async def test_subscription_updated_legacy_subscription_sunset(
        self,
        mock_send_notification,
        mock_stripe_modify,
        mock_mark_processed,
        mock_is_processed,
        orm_session,
        test_org_with_subscription,
        mock_legacy_subscription_event,
    ):
        """Test subscription updated webhook handling legacy subscription that should be sunset."""
        mock_is_processed.return_value = False
        # Mock single Stripe modify call to succeed
        mock_stripe_modify.return_value = MagicMock(id="sub_legacy_123")

        # Make sure the notification mock doesn't raise any exceptions or interfere with session
        async def mock_notification(*args, **kwargs):
            # Do nothing, don't call orm.commit() or any other session operations
            pass

        mock_send_notification.side_effect = mock_notification

        # Set up org with legacy subscription
        test_org_with_subscription.subscription_id = "sub_legacy_123"
        orm_session.commit()

        mock_legacy_subscription_event.data.object["id"] = "sub_legacy_123"

        # Debug: print the subscription data that will be processed
        subscription_data = mock_legacy_subscription_event.data.object
        print(f"DEBUG: Subscription data - id: {subscription_data.get('id')}")
        print(f"DEBUG: Subscription data - status: {subscription_data.get('status')}")
        print(
            f"DEBUG: Subscription data - cancel_at_period_end: {subscription_data.get('cancel_at_period_end')}"
        )
        items = subscription_data.get('items', {}).get('data', [])
        for i, item in enumerate(items):
            price = item.get('price', {})
            print(
                f"DEBUG: Item {i} - price_id: {price.get('id')}, product_name: {price.get('product', {}).get('name')}"
            )

        # Ensure the mock returns the expected subscription data
        # The function uses event.data.object directly, not a Stripe API call
        try:
            result = await handle_subscription_updated(mock_legacy_subscription_event, orm_session)
            print(f"DEBUG: handle_subscription_updated returned: {result}")
        except Exception as e:
            print(f"DEBUG: Exception in handle_subscription_updated: {e}")
            import traceback

            traceback.print_exc()
            raise

        # Verify Stripe subscription was modified to cancel at period end
        mock_stripe_modify.assert_called()
        call_args = mock_stripe_modify.call_args_list[0]
        assert call_args[0][0] == "sub_legacy_123"  # subscription_id
        assert call_args[1]["cancel_at_period_end"] is True
        assert "billing_model_change" in call_args[1]["metadata"]["cancellation_reason"]

        # Explicitly flush and commit all pending changes
        orm_session.flush()
        orm_session.commit()

        # Query audit logs with more debugging
        all_audit_logs = (
            orm_session.query(BillingAuditLog)
            .filter(BillingAuditLog.org_id == test_org_with_subscription.id)
            .all()
        )
        print(f"DEBUG: Found {len(all_audit_logs)} audit logs for org {test_org_with_subscription.id}")
        for log in all_audit_logs:
            print(f"DEBUG: Audit log - action: {log.action}, details: {log.details}")

        # Verify audit log was created
        audit_log = (
            orm_session.query(BillingAuditLog)
            .filter(
                BillingAuditLog.org_id == test_org_with_subscription.id,
                BillingAuditLog.action == 'legacy_subscription_sunset',
            )
            .first()
        )
        assert audit_log is not None, f"No audit log found for org {test_org_with_subscription.id}"
        assert audit_log.details["subscription_id"] == "sub_legacy_123"

        # Verify notification was sent
        mock_send_notification.assert_called_once()

        mock_mark_processed.assert_called_once_with(mock_legacy_subscription_event.id, orm_session)

    @pytest.mark.asyncio
    @patch('agentops.api.routes.v4.stripe_webhooks.is_event_processed')
    @patch('agentops.api.routes.v4.stripe_webhooks.mark_event_processed')
    async def test_subscription_updated_current_subscription(
        self,
        mock_mark_processed,
        mock_is_processed,
        orm_session,
        test_org_with_subscription,
        mock_subscription_event,
    ):
        """Test subscription updated webhook for current (non-legacy) subscription."""
        mock_is_processed.return_value = False

        result = await handle_subscription_updated(mock_subscription_event, orm_session)

        # Should process normally without legacy subscription handling
        mock_mark_processed.assert_called_once_with(mock_subscription_event.id, orm_session)

    @pytest.mark.asyncio
    @patch('agentops.api.routes.v4.stripe_webhooks.is_event_processed')
    @patch('agentops.api.routes.v4.stripe_webhooks.log_webhook_metric')
    async def test_subscription_updated_org_not_found(
        self, mock_log_metric, mock_is_processed, orm_session, mock_subscription_event
    ):
        """Test subscription updated webhook when org is not found."""
        mock_is_processed.return_value = False

        # Set subscription ID that doesn't match any org
        mock_subscription_event.data.object["id"] = "sub_nonexistent_123"

        result = await handle_subscription_updated(mock_subscription_event, orm_session)

        # Should return early
        assert result is None

    @pytest.mark.asyncio
    @patch('agentops.api.routes.v4.stripe_webhooks.is_event_processed')
    async def test_event_already_processed(self, mock_is_processed, orm_session, mock_checkout_event):
        """Test that already processed events are skipped."""
        mock_is_processed.return_value = True

        result = await handle_checkout_completed(mock_checkout_event, orm_session)

        assert result == {"status": "already_processed"}


class TestWebhookEdgeCases:
    """Test edge cases and error scenarios for webhook handlers."""

    @pytest.mark.asyncio
    @patch('agentops.api.routes.v4.stripe_webhooks.is_event_processed')
    @patch('agentops.api.routes.v4.stripe_webhooks.mark_event_processed')
    @patch('agentops.api.routes.v4.stripe_webhooks.log_webhook_metric')
    async def test_checkout_completed_empty_metadata_org_id(
        self,
        mock_log_metric,
        mock_mark_processed,
        mock_is_processed,
        orm_session,
        test_free_org,
        mock_checkout_event,
    ):
        """Test checkout completion when org_id in metadata is empty string."""
        mock_is_processed.return_value = False

        # Simulate the scenario where client_reference_id is missing and org_id is empty
        mock_checkout_event.data.object["client_reference_id"] = None
        mock_checkout_event.data.object["metadata"] = {"org_id": ""}

        result = await handle_checkout_completed(mock_checkout_event, orm_session)

        # Should return early without processing due to empty org_id
        assert result is None

        # Verify metric was logged for missing reference ID
        mock_log_metric.assert_called_once_with(
            "checkout.session.completed",
            "missing_reference_id",
            {"session_id": "cs_test_session_123", "subscription_id": "sub_new_123"},
        )

    @pytest.mark.asyncio
    @patch('agentops.api.routes.v4.stripe_webhooks.is_event_processed')
    @patch('agentops.api.routes.v4.stripe_webhooks.mark_event_processed')
    async def test_checkout_completed_missing_subscription_id(
        self, mock_mark_processed, mock_is_processed, orm_session, test_free_org, mock_checkout_event
    ):
        """Test checkout completion when subscription_id is missing."""
        mock_is_processed.return_value = False

        # Set up valid client_reference_id but missing subscription
        mock_checkout_event.data.object["client_reference_id"] = str(test_free_org.id)
        mock_checkout_event.data.object["subscription"] = None

        result = await handle_checkout_completed(mock_checkout_event, orm_session)

        # Should return early without processing
        assert result is None

        # Verify org was not updated
        orm_session.refresh(test_free_org)
        assert test_free_org.subscription_id is None
        assert test_free_org.prem_status == PremStatus.free

    @pytest.mark.asyncio
    @patch('agentops.api.routes.v4.stripe_webhooks.is_event_processed')
    async def test_checkout_completed_stripe_error_handling(
        self, mock_is_processed, orm_session, test_free_org, mock_checkout_event
    ):
        """Test that Stripe errors are properly logged and handled."""
        mock_is_processed.return_value = False

        # Set up valid data
        mock_checkout_event.data.object["client_reference_id"] = str(test_free_org.id)

        # Simulate a Stripe error during processing
        with patch('stripe.Subscription.retrieve') as mock_retrieve:
            mock_retrieve.side_effect = stripe.error.StripeError("Test Stripe error")

            with pytest.raises(HTTPException) as exc_info:
                await handle_checkout_completed(mock_checkout_event, orm_session)

            assert exc_info.value.status_code == 500
            assert "Stripe API error" in exc_info.value.detail
