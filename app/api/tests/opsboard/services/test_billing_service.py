import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from decimal import Decimal
import os

from agentops.opsboard.services.billing_service import BillingService
from agentops.opsboard.models import ProjectModel, BillingPeriod
from agentops.common.usage_tracking import UsageType


# Mock Stripe environment variables for testing
@pytest.fixture(autouse=True)
def mock_stripe_env_vars():
    with (
        patch.dict(
            os.environ,
            {
                'STRIPE_SECRET_KEY': 'sk_test_mock_key',
                'STRIPE_SUBSCRIPTION_PRICE_ID': 'price_test_subscription',
                'STRIPE_TOKEN_PRICE_ID': 'price_test_token',
                'STRIPE_SPAN_PRICE_ID': 'price_test_span',
            },
        ),
        patch('stripe.Account.retrieve'),
    ):
        yield


@pytest.fixture
def billing_service():
    """Create a billing service instance for testing."""
    # Mock the Stripe validation to avoid API calls during initialization
    with patch('stripe.Account.retrieve'):
        return BillingService()


@pytest.fixture
def mock_stripe_price():
    """Mock Stripe price object."""
    mock_price = MagicMock()
    mock_price.unit_amount = 2000  # $20.00 in cents
    mock_price.transform_quantity = None
    return mock_price


@pytest.fixture
def mock_clickhouse_client():
    """Mock ClickHouse client for usage queries."""
    mock_client = MagicMock()
    mock_result = MagicMock()
    mock_result.result_rows = [
        (1000, 82000)  # span_count, total_tokens (50000+25000+5000+2000)
    ]
    mock_client.query.return_value = mock_result
    return mock_client


class TestBillingService:
    """Test cases for BillingService class."""

    def test_init(self):
        """Test BillingService initialization."""
        service = BillingService()

        assert service._pricing_cache is None
        assert service._cache_timestamp is None
        assert service._cache_duration == 3600  # 1 hour
        assert service._usage_cache == {}
        assert service._usage_cache_ttl == 300  # 5 minutes

    def test_should_refresh_cache_when_no_cache(self, billing_service):
        """Test _should_refresh_cache returns True when no cache exists."""
        # Ensure no cache exists
        billing_service._pricing_cache = None
        billing_service._cache_timestamp = None

        assert billing_service._should_refresh_cache() is True

    def test_should_refresh_cache_when_cache_expired(self, billing_service):
        """Test _should_refresh_cache returns True when cache is expired."""
        # Set cache with expired timestamp
        billing_service._pricing_cache = {"test": "data"}
        billing_service._cache_timestamp = datetime.now() - timedelta(seconds=3700)  # Older than 1 hour

        assert billing_service._should_refresh_cache() is True

    def test_should_refresh_cache_when_cache_valid(self, billing_service):
        """Test _should_refresh_cache returns False when cache is still valid."""
        # Set cache with recent timestamp
        billing_service._pricing_cache = {"test": "data"}
        billing_service._cache_timestamp = datetime.now() - timedelta(seconds=1800)  # 30 minutes ago

        assert billing_service._should_refresh_cache() is False

    @patch('agentops.opsboard.services.billing_service.STRIPE_SPAN_PRICE_ID', 'price_span123')
    @patch('agentops.opsboard.services.billing_service.STRIPE_TOKEN_PRICE_ID', 'price_token123')
    @patch('stripe.Price.retrieve')
    def test_get_usage_pricing_with_stripe_success(self, mock_price_retrieve, billing_service):
        """Test get_usage_pricing successfully fetches from Stripe."""
        # Clear cache to ensure fresh call
        billing_service._pricing_cache = None
        billing_service._cache_timestamp = None

        # Mock Stripe price objects
        token_price = MagicMock()
        token_price.unit_amount = 2  # $0.02 in cents for 1000 tokens
        token_price.unit_amount_decimal = None
        token_price.custom_unit_amount = None
        token_price.tiers = None
        token_price.currency_options = None
        token_price.transform_quantity = MagicMock()
        token_price.transform_quantity.divide_by = 1000

        span_price = MagicMock()
        span_price.unit_amount = 100  # $1.00 in cents per span
        span_price.unit_amount_decimal = None
        span_price.custom_unit_amount = None
        span_price.tiers = None
        span_price.currency_options = None
        span_price.transform_quantity = None

        mock_price_retrieve.side_effect = [token_price, span_price]

        pricing = billing_service.get_usage_pricing()

        assert UsageType.TOKENS in pricing
        assert UsageType.SPANS in pricing

        # Check token pricing - unit_amount 2 becomes 2/100 = 0.02 dollars
        token_config = pricing[UsageType.TOKENS]
        assert token_config['price_per_unit'] == Decimal('0.02')
        assert token_config['unit_size'] == 1000
        assert token_config['display_unit'] == 'thousand tokens'
        assert token_config['stripe_price_id'] == 'price_token123'

        # Check span pricing
        span_config = pricing[UsageType.SPANS]
        assert span_config['price_per_unit'] == Decimal('1.00')
        assert span_config['unit_size'] == 1000
        assert span_config['display_unit'] == 'thousand spans'
        assert span_config['stripe_price_id'] == 'price_span123'

    @patch('stripe.Price.retrieve')
    def test_get_usage_pricing_with_stripe_error(self, mock_price_retrieve, billing_service):
        """Test get_usage_pricing falls back to defaults when Stripe fails."""
        import stripe

        mock_price_retrieve.side_effect = stripe.error.StripeError("API Error")

        pricing = billing_service.get_usage_pricing()

        # Should return default values
        assert UsageType.TOKENS in pricing
        assert UsageType.SPANS in pricing

        token_config = pricing[UsageType.TOKENS]
        assert token_config['price_per_unit'] == Decimal('0.0002')
        assert token_config['unit_size'] == 1000
        assert token_config['display_unit'] == 'thousand tokens'

        span_config = pricing[UsageType.SPANS]
        assert span_config['price_per_unit'] == Decimal('0.0001')
        assert span_config['unit_size'] == 1000
        assert span_config['display_unit'] == 'thousand spans'

    @patch('agentops.opsboard.services.billing_service.STRIPE_SPAN_PRICE_ID', 'price_span123')
    @patch('agentops.opsboard.services.billing_service.STRIPE_TOKEN_PRICE_ID', 'price_token123')
    def test_get_usage_pricing_with_env_vars(self, billing_service):
        """Test get_usage_pricing uses environment variable price IDs."""
        # Clear cache to ensure fresh call
        billing_service._pricing_cache = None
        billing_service._cache_timestamp = None

        with patch('stripe.Price.retrieve') as mock_retrieve:
            token_price = MagicMock()
            token_price.unit_amount = 5
            token_price.unit_amount_decimal = None
            token_price.custom_unit_amount = None
            token_price.tiers = None
            token_price.currency_options = None
            token_price.transform_quantity = None

            span_price = MagicMock()
            span_price.unit_amount = 150
            span_price.unit_amount_decimal = None
            span_price.custom_unit_amount = None
            span_price.tiers = None
            span_price.currency_options = None
            span_price.transform_quantity = None

            mock_retrieve.side_effect = [token_price, span_price]

            billing_service.get_usage_pricing()

            # Verify that Stripe was called with the environment variable price IDs
            assert mock_retrieve.call_count == 2
            mock_retrieve.assert_any_call('price_token123', expand=['currency_options', 'tiers'])
            mock_retrieve.assert_any_call('price_span123', expand=['currency_options', 'tiers'])

    def test_get_usage_pricing_returns_cached_values(self, billing_service):
        """Test get_usage_pricing returns cached values when cache is valid."""
        # Set up valid cache
        cached_pricing = {
            UsageType.TOKENS: {'price_per_unit': Decimal('0.01'), 'unit_size': 1000},
            UsageType.SPANS: {'price_per_unit': Decimal('0.002'), 'unit_size': 1},
        }
        billing_service._pricing_cache = cached_pricing
        billing_service._cache_timestamp = datetime.now()

        with patch('stripe.Price.retrieve') as mock_retrieve:
            pricing = billing_service.get_usage_pricing()

            # Should return cached values without calling Stripe
            assert pricing == cached_pricing
            mock_retrieve.assert_not_called()

    @patch('agentops.opsboard.services.billing_service.STRIPE_SUBSCRIPTION_PRICE_ID', 'price_sub123')
    @patch('stripe.Price.retrieve')
    def test_get_seat_price_from_stripe_success(self, mock_price_retrieve, billing_service):
        """Test get_seat_price successfully fetches from Stripe."""
        mock_price = MagicMock()
        mock_price.unit_amount = 5000  # $50.00 in cents
        mock_price.unit_amount_decimal = None
        mock_price.custom_unit_amount = None
        mock_price.tiers = None
        mock_price.currency_options = None
        mock_price.recurring = MagicMock()
        mock_price.recurring.usage_type = 'licensed'

        mock_price_retrieve.return_value = mock_price

        seat_price = billing_service.get_seat_price()

        assert seat_price == 5000
        mock_price_retrieve.assert_called_once_with('price_sub123', expand=['currency_options', 'tiers'])

    @patch('stripe.Price.retrieve')
    def test_get_seat_price_stripe_error_fallback(self, mock_price_retrieve, billing_service):
        """Test get_seat_price falls back to environment variable when Stripe fails."""
        import stripe

        mock_price_retrieve.side_effect = stripe.error.StripeError("API Error")

        with patch.dict(os.environ, {'STRIPE_SEAT_PRICE_CENTS': '6000'}):
            seat_price = billing_service.get_seat_price()

        assert seat_price == 6000

    @patch.dict('os.environ', {'STRIPE_SEAT_PRICE_CENTS': '5000'})
    def test_get_seat_price_from_env_var(self, billing_service):
        """Test get_seat_price uses environment variable when no Stripe config."""
        # No STRIPE_SUBSCRIPTION_PRICE_ID set
        with patch.dict(os.environ, {}, clear=True):
            os.environ['STRIPE_SEAT_PRICE_CENTS'] = '5000'
            seat_price = billing_service.get_seat_price()

        assert seat_price == 5000

    @patch('agentops.opsboard.services.billing_service.get_clickhouse')
    async def test_get_usage_for_period_success(
        self, mock_get_clickhouse, billing_service, orm_session, test_org, mock_clickhouse_client
    ):
        """Test get_usage_for_period successfully queries ClickHouse."""
        # Create test projects for the org
        project1 = ProjectModel(name="Test Project 1", org_id=test_org.id)
        project2 = ProjectModel(name="Test Project 2", org_id=test_org.id)
        orm_session.add_all([project1, project2])
        orm_session.flush()

        # Mock ClickHouse response
        mock_get_clickhouse.return_value = mock_clickhouse_client

        period_start = datetime(2024, 1, 1)
        period_end = datetime(2024, 1, 31)

        result = await billing_service.get_usage_for_period(
            orm_session, str(test_org.id), period_start, period_end
        )

        assert result == {'tokens': 82000, 'spans': 1000}  # 50000+25000+5000+2000 tokens, 1000 spans
        mock_clickhouse_client.query.assert_called_once()

    async def test_get_usage_for_period_no_projects(self, billing_service, orm_session, test_org):
        """Test get_usage_for_period returns empty when org has no projects."""
        period_start = datetime(2024, 1, 1)
        period_end = datetime(2024, 1, 31)

        result = await billing_service.get_usage_for_period(
            orm_session, str(test_org.id), period_start, period_end
        )

        assert result == {}

    @patch('agentops.opsboard.services.billing_service.get_clickhouse')
    async def test_get_usage_for_period_clickhouse_error(
        self, mock_get_clickhouse, billing_service, orm_session, test_org
    ):
        """Test get_usage_for_period handles ClickHouse errors gracefully."""
        # Create test project
        project = ProjectModel(name="Test Project", org_id=test_org.id)
        orm_session.add(project)
        orm_session.flush()

        # Mock ClickHouse to raise an error
        mock_client = MagicMock()
        mock_client.query.side_effect = Exception("ClickHouse connection failed")
        mock_get_clickhouse.return_value = mock_client

        period_start = datetime(2024, 1, 1)
        period_end = datetime(2024, 1, 31)

        result = await billing_service.get_usage_for_period(
            orm_session, str(test_org.id), period_start, period_end
        )

        assert result == {}

    async def test_get_usage_for_period_uses_cache(self, billing_service, orm_session, test_org):
        """Test get_usage_for_period returns cached data when available."""
        from datetime import timezone

        period_start = datetime(2024, 1, 1)
        period_end = datetime(2024, 1, 31)

        # Convert to UTC as the implementation does
        period_start_utc = period_start.replace(tzinfo=timezone.utc)
        period_end_utc = period_end.replace(tzinfo=timezone.utc)

        cache_key = f"{test_org.id}:{period_start_utc.isoformat()}:{period_end_utc.isoformat()}:all"

        # Set cache data
        cached_data = {'tokens': 5000, 'spans': 100}
        billing_service._usage_cache[cache_key] = (cached_data, datetime.now())

        result = await billing_service.get_usage_for_period(
            orm_session, str(test_org.id), period_start, period_end
        )

        assert result == cached_data

    async def test_get_usage_for_period_cache_expiry(
        self, billing_service, orm_session, test_org, mock_clickhouse_client
    ):
        """Test get_usage_for_period refreshes data when cache is expired."""
        from datetime import timezone

        period_start = datetime(2024, 1, 1)
        period_end = datetime(2024, 1, 31)

        # Convert to UTC as the implementation does
        period_start_utc = period_start.replace(tzinfo=timezone.utc)
        period_end_utc = period_end.replace(tzinfo=timezone.utc)

        cache_key = f"{test_org.id}:{period_start_utc.isoformat()}:{period_end_utc.isoformat()}:all"

        # Set expired cache data
        expired_data = {'tokens': 1000, 'spans': 50}
        expired_time = datetime.now() - timedelta(seconds=400)  # Older than 5 minutes
        billing_service._usage_cache[cache_key] = (expired_data, expired_time)

        with patch('agentops.opsboard.services.billing_service.get_clickhouse') as mock_get_clickhouse:
            mock_get_clickhouse.return_value = mock_clickhouse_client

            # Create test project
            project = ProjectModel(name="Test Project", org_id=test_org.id)
            orm_session.add(project)
            orm_session.flush()

            result = await billing_service.get_usage_for_period(
                orm_session, str(test_org.id), period_start, period_end
            )

            # Should get fresh data, not expired cache
            assert result == {'tokens': 82000, 'spans': 1000}

    async def test_calculate_usage_costs_tokens(self, billing_service):
        """Test calculate_usage_costs correctly calculates token costs."""
        # Mock pricing
        billing_service._pricing_cache = {
            UsageType.TOKENS: {'price_per_unit': Decimal('0.0002'), 'unit_size': 1000}
        }
        billing_service._cache_timestamp = datetime.now()

        usage_quantities = {'tokens': 5000000}  # 5M tokens

        result = await billing_service.calculate_usage_costs(usage_quantities)

        # 5M tokens / 1000 units * $0.0002 = $1.00 = 100 cents
        assert result == {'tokens': 100}

    async def test_calculate_usage_costs_spans(self, billing_service):
        """Test calculate_usage_costs correctly calculates span costs."""
        # Mock pricing
        billing_service._pricing_cache = {
            UsageType.SPANS: {'price_per_unit': Decimal('0.0001'), 'unit_size': 1000}
        }
        billing_service._cache_timestamp = datetime.now()

        usage_quantities = {'spans': 1000000}  # 1M spans

        result = await billing_service.calculate_usage_costs(usage_quantities)

        # 1M spans / 1000 units * $0.0001 = $0.10 = 10 cents
        assert result == {'spans': 10}

    async def test_calculate_usage_costs_mixed_usage(self, billing_service):
        """Test calculate_usage_costs handles multiple usage types."""
        # Mock pricing
        billing_service._pricing_cache = {
            UsageType.TOKENS: {'price_per_unit': Decimal('0.0002'), 'unit_size': 1000},
            UsageType.SPANS: {'price_per_unit': Decimal('0.0001'), 'unit_size': 1000},
        }
        billing_service._cache_timestamp = datetime.now()

        usage_quantities = {'tokens': 2000000, 'spans': 500000}

        result = await billing_service.calculate_usage_costs(usage_quantities)

        # Tokens: 2M / 1000 * $0.0002 = $0.40 = 40 cents
        # Spans: 500K / 1000 * $0.0001 = $0.05 = 5 cents
        assert result == {'tokens': 40, 'spans': 5}

    async def test_calculate_usage_costs_unknown_usage_type(self, billing_service):
        """Test calculate_usage_costs ignores unknown usage types."""
        # Mock pricing
        billing_service._pricing_cache = {
            UsageType.TOKENS: {'price_per_unit': Decimal('0.0002'), 'unit_size': 1000}
        }
        billing_service._cache_timestamp = datetime.now()

        usage_quantities = {'tokens': 1000000, 'unknown_type': 500}

        result = await billing_service.calculate_usage_costs(usage_quantities)

        # Should only calculate known types
        assert result == {'tokens': 20}
        assert 'unknown_type' not in result

    async def test_calculate_usage_costs_zero_quantities(self, billing_service):
        """Test calculate_usage_costs handles zero quantities."""
        # Mock pricing
        billing_service._pricing_cache = {
            UsageType.TOKENS: {'price_per_unit': Decimal('0.0002'), 'unit_size': 1000},
            UsageType.SPANS: {'price_per_unit': Decimal('0.0001'), 'unit_size': 1000},
        }
        billing_service._cache_timestamp = datetime.now()

        usage_quantities = {'tokens': 0, 'spans': 0}

        result = await billing_service.calculate_usage_costs(usage_quantities)

        # With minimum charge threshold, zero quantities return empty dict
        assert result == {}

    async def test_create_billing_period_snapshot_success(
        self, billing_service, orm_session, test_org, test_user, test_user2, test_user3
    ):
        """Test create_billing_period_snapshot creates a complete snapshot."""
        # Set up org with paid members using existing test user fixtures
        from agentops.opsboard.models import UserOrgModel, OrgRoles

        # Create 3 paid member relationships using existing test users
        test_users = [test_user, test_user2, test_user3]

        for user in test_users:
            user_org = UserOrgModel(
                user_id=user.id,
                org_id=test_org.id,
                role=OrgRoles.developer,
                user_email=user.email,
                is_paid=True,
            )
            orm_session.add(user_org)

        orm_session.flush()

        # Mock the get_usage_for_period method
        with (
            patch.object(billing_service, 'get_usage_for_period') as mock_get_usage,
            patch.object(billing_service, 'calculate_usage_costs') as mock_calc_costs,
            patch.object(billing_service, 'get_seat_price') as mock_seat_price,
        ):
            mock_get_usage.return_value = {'tokens': 1000000, 'spans': 500}
            mock_calc_costs.return_value = {'tokens': 20, 'spans': 50}
            mock_seat_price.return_value = 4000  # $40 per seat

            period_start = datetime(2024, 1, 1)
            period_end = datetime(2024, 1, 31)

            result = await billing_service.create_billing_period_snapshot(
                orm_session, test_org, period_start, period_end
            )

            assert isinstance(result, BillingPeriod)
            assert result.org_id == test_org.id
            assert result.period_start == period_start
            assert result.period_end == period_end
            assert result.seat_cost == 12000  # 3 seats * $40
            assert result.seat_count == 3
            assert result.usage_costs == {'tokens': 20, 'spans': 50}
            assert result.usage_quantities == {'tokens': 1000000, 'spans': 500}
            assert result.total_cost == 12070  # 12000 + 20 + 50
            assert result.status == 'pending'

    async def test_create_billing_period_snapshot_no_usage(
        self, billing_service, orm_session, test_org, test_user
    ):
        """Test create_billing_period_snapshot works with zero usage."""
        # Set up org with one paid member using existing test user fixture
        from agentops.opsboard.models import UserOrgModel, OrgRoles

        user_org = UserOrgModel(
            user_id=test_user.id,
            org_id=test_org.id,
            role=OrgRoles.owner,
            user_email=test_user.email,
            is_paid=True,
        )
        orm_session.add(user_org)
        orm_session.flush()

        with (
            patch.object(billing_service, 'get_usage_for_period') as mock_get_usage,
            patch.object(billing_service, 'calculate_usage_costs') as mock_calc_costs,
            patch.object(billing_service, 'get_seat_price') as mock_seat_price,
        ):
            mock_get_usage.return_value = {}
            mock_calc_costs.return_value = {}
            mock_seat_price.return_value = 4000

            period_start = datetime(2024, 1, 1)
            period_end = datetime(2024, 1, 31)

            result = await billing_service.create_billing_period_snapshot(
                orm_session, test_org, period_start, period_end
            )

            assert result.seat_cost == 4000
            assert result.usage_costs == {}
            assert result.total_cost == 4000

    async def test_create_billing_period_snapshot_multiple_seats(
        self, billing_service, orm_session, test_org, test_user, test_user2, test_user3
    ):
        """Test create_billing_period_snapshot calculates multiple seat costs correctly."""
        # Set up org with multiple paid members using existing test user fixtures
        from agentops.opsboard.models import UserOrgModel, OrgRoles

        # Create 3 paid member relationships using existing test users (can't reuse same user for same org)
        test_users = [test_user, test_user2, test_user3]

        for user in test_users:
            user_org = UserOrgModel(
                user_id=user.id,
                org_id=test_org.id,
                role=OrgRoles.developer,
                user_email=user.email,
                is_paid=True,
            )
            orm_session.add(user_org)

        orm_session.flush()

        with (
            patch.object(billing_service, 'get_usage_for_period') as mock_get_usage,
            patch.object(billing_service, 'calculate_usage_costs') as mock_calc_costs,
            patch.object(billing_service, 'get_seat_price') as mock_seat_price,
        ):
            mock_get_usage.return_value = {'tokens': 500000}
            mock_calc_costs.return_value = {'tokens': 10}
            mock_seat_price.return_value = 3500  # $35 per seat

            period_start = datetime(2024, 1, 1)
            period_end = datetime(2024, 1, 31)

            result = await billing_service.create_billing_period_snapshot(
                orm_session, test_org, period_start, period_end
            )

            assert result.seat_cost == 10500  # 3 seats * $35
            assert result.seat_count == 3
            assert result.total_cost == 10510  # 10500 + 10

    async def test_create_billing_period_snapshot_commits_to_db(
        self, billing_service, orm_session, test_org, test_user
    ):
        """Test create_billing_period_snapshot commits the billing period to database."""
        # Set up org with one paid member using existing test user fixture
        from agentops.opsboard.models import UserOrgModel, OrgRoles

        user_org = UserOrgModel(
            user_id=test_user.id,
            org_id=test_org.id,
            role=OrgRoles.owner,
            user_email=test_user.email,
            is_paid=True,
        )
        orm_session.add(user_org)
        orm_session.flush()

        with (
            patch.object(billing_service, 'get_usage_for_period') as mock_get_usage,
            patch.object(billing_service, 'calculate_usage_costs') as mock_calc_costs,
            patch.object(billing_service, 'get_seat_price') as mock_seat_price,
        ):
            mock_get_usage.return_value = {}
            mock_calc_costs.return_value = {}
            mock_seat_price.return_value = 4000

            period_start = datetime(2024, 1, 1)
            period_end = datetime(2024, 1, 31)

            result = await billing_service.create_billing_period_snapshot(
                orm_session, test_org, period_start, period_end
            )

            # Verify it was added to the session and committed
            billing_period_in_db = orm_session.query(BillingPeriod).filter_by(id=result.id).first()
            assert billing_period_in_db is not None
            assert billing_period_in_db.org_id == test_org.id
