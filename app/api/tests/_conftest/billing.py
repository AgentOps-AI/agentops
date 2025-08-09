import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
from agentops.opsboard.models import BillingPeriod, OrgModel, UserOrgModel, OrgRoles, PremStatus
from .billing_constants import (
    STRIPE_SUBSCRIPTION_ID_DEFAULT,
    STRIPE_CUSTOMER_ID_DEFAULT,
    STRIPE_PRICE_ID_CURRENT,
    STRIPE_PRICE_ID_LEGACY,
    STRIPE_ITEM_ID_DEFAULT,
    SEAT_PRICE_DEFAULT,
)


@pytest.fixture
def billing_period_factory():
    """Factory for creating billing periods with unique, predictable dates."""
    counter = 0

    def create_period(org_id, **kwargs):
        nonlocal counter
        counter += 1

        # Use year 2025 + counter to ensure uniqueness and avoid past dates
        base_date = datetime(2025, 1, 1, tzinfo=timezone.utc) + timedelta(days=counter * 2)

        defaults = {
            'period_start': base_date,
            'period_end': base_date + timedelta(days=1),
            'seat_cost': 0,
            'seat_count': 0,
            'usage_costs': {},
            'usage_quantities': {},
            'total_cost': 0,
            'status': 'pending',
        }
        defaults.update(kwargs)

        return BillingPeriod(org_id=org_id, **defaults)

    return create_period


@pytest.fixture
def mock_stripe_subscription():
    """Centralized Stripe subscription mock with consistent behavior."""
    mock_sub = MagicMock()
    mock_sub.id = STRIPE_SUBSCRIPTION_ID_DEFAULT
    mock_sub.customer = STRIPE_CUSTOMER_ID_DEFAULT
    mock_sub.status = "active"
    mock_sub.cancel_at_period_end = False

    # Use dynamic timestamps to avoid hardcoded values
    now = datetime.now()
    mock_sub.current_period_start = int(now.timestamp())
    mock_sub.current_period_end = int((now + timedelta(days=30)).timestamp())

    # Standard subscription item
    mock_item = {
        'id': STRIPE_ITEM_ID_DEFAULT,
        'price': {
            'id': STRIPE_PRICE_ID_CURRENT,  # Matches STRIPE_SUBSCRIPTION_PRICE_ID
            'unit_amount': SEAT_PRICE_DEFAULT,  # Amount in cents
            'currency': 'usd',
            'recurring': {'usage_type': 'licensed', 'interval': 'month', 'interval_count': 1},
        },
        'quantity': 2,
    }

    mock_sub.items = MagicMock()
    mock_sub.items.data = [mock_item]

    def mock_get(key, default=None):
        if key == 'cancel_at_period_end':
            return mock_sub.cancel_at_period_end
        elif key == 'items':
            return {'data': mock_sub.items.data}
        elif key == 'current_period_end':
            return mock_sub.current_period_end
        elif key == 'current_period_start':
            return mock_sub.current_period_start
        elif key == 'status':
            return mock_sub.status
        return default

    mock_sub.get = mock_get
    return mock_sub


@pytest.fixture
def mock_stripe_subscription_legacy():
    """Specialized mock for legacy subscription tests."""
    mock_sub = MagicMock()
    mock_sub.id = "sub_legacy_123"
    mock_sub.customer = STRIPE_CUSTOMER_ID_DEFAULT
    mock_sub.status = "active"
    mock_sub.cancel_at_period_end = False

    now = datetime.now()
    mock_sub.current_period_start = int(now.timestamp())
    mock_sub.current_period_end = int((now + timedelta(days=30)).timestamp())

    # Legacy subscription with old price ID
    legacy_item = {
        'id': 'si_legacy_123',
        'price': {
            'id': STRIPE_PRICE_ID_LEGACY,  # Different from current
            'product': {'name': 'Legacy Seat Plan'},
        },
        'quantity': 1,
    }
    mock_sub.items = MagicMock()
    mock_sub.items.data = [legacy_item]

    def mock_get(key, default=None):
        if key == 'cancel_at_period_end':
            return mock_sub.cancel_at_period_end
        elif key == 'items':
            return {'data': mock_sub.items.data}
        elif key == 'current_period_end':
            return mock_sub.current_period_end
        elif key == 'current_period_start':
            return mock_sub.current_period_start
        elif key == 'status':
            return mock_sub.status
        return default

    mock_sub.get = mock_get
    return mock_sub


@pytest.fixture
def org_factory():
    """Factory for creating organizations with different configurations."""
    created_orgs = []

    def create_org(orm_session, owner_user, **kwargs):
        defaults = {
            'name': f"Test Org {len(created_orgs) + 1}",
            'prem_status': PremStatus.free,
            'subscription_id': None,
        }
        defaults.update(kwargs)

        org = OrgModel(**defaults)
        orm_session.add(org)
        orm_session.flush()

        # Add owner relationship
        owner_member = UserOrgModel(
            user_id=owner_user.id,
            org_id=org.id,
            role=OrgRoles.owner,
            user_email=owner_user.email,
            is_paid=defaults['prem_status'] == PremStatus.pro,
        )
        orm_session.add(owner_member)
        orm_session.flush()

        created_orgs.append(org)
        return org

    return create_org


@pytest.fixture
def test_pro_org(orm_session, test_user, org_factory):
    """Standard pro organization for billing tests."""
    return org_factory(
        orm_session,
        test_user,
        name="Test Pro Org",
        prem_status=PremStatus.pro,
        subscription_id=STRIPE_SUBSCRIPTION_ID_DEFAULT,
    )


@pytest.fixture
def test_free_org(orm_session, test_user, org_factory):
    """Standard free organization for testing upgrades."""
    return org_factory(orm_session, test_user, name="Test Free Org", prem_status=PremStatus.free)


def assert_billing_error(exception_info, expected_code, expected_message_fragment):
    """Standard assertion for billing-related errors."""
    assert exception_info.value.status_code == expected_code
    assert expected_message_fragment in str(exception_info.value.detail)


def assert_stripe_error_handling(exception_info):
    """Standard assertion for Stripe API error handling."""
    assert exception_info.value.status_code == 500
    assert "Stripe API error" in exception_info.value.detail
