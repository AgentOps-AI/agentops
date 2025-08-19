import os
import stripe
import logging
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone
from typing import Dict, Optional
from sqlalchemy.orm import Session

from ...common.usage_tracking import UsageType
from ..models import OrgModel, BillingPeriod
from ...api.db.clickhouse_client import get_clickhouse
from ...api.environment import (
    STRIPE_SECRET_KEY,
    STRIPE_SUBSCRIPTION_PRICE_ID,
    STRIPE_TOKEN_PRICE_ID,
    STRIPE_SPAN_PRICE_ID,
)

logger = logging.getLogger(__name__)


class BillingService:
    def __init__(self):
        # Validate and set Stripe configuration with detailed logging
        self._validate_stripe_config()
        stripe.api_key = STRIPE_SECRET_KEY
        self._pricing_cache: Optional[Dict] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_duration = 3600  # Cache for 1 hour

        self._usage_cache: Dict[str, tuple[Dict[str, int], datetime]] = {}
        self._usage_cache_ttl = 300  # 5 minutes for usage data

    def _validate_stripe_config(self):
        """Validate Stripe configuration and log detailed status"""
        logger.info("=== BillingService Stripe Validation ===")

        # Check all required Stripe variables
        required_vars = {
            "STRIPE_SECRET_KEY": STRIPE_SECRET_KEY,
            "STRIPE_SUBSCRIPTION_PRICE_ID": STRIPE_SUBSCRIPTION_PRICE_ID,
            "STRIPE_TOKEN_PRICE_ID": STRIPE_TOKEN_PRICE_ID,
            "STRIPE_SPAN_PRICE_ID": STRIPE_SPAN_PRICE_ID,
        }

        all_present = True
        for var_name, var_value in required_vars.items():
            if var_value:
                masked_value = f"{var_value[:8]}..." if len(var_value) > 8 else var_value
                logger.info(f"✓ {var_name}: {masked_value}")
            else:
                logger.error(f"✗ {var_name}: NOT FOUND - This will cause billing failures!")
                all_present = False

        if all_present:
            logger.info("✓ All required Stripe variables present, attempting Stripe API test...")
            try:
                # Test Stripe API connectivity with a simple call
                if STRIPE_SECRET_KEY:
                    stripe.api_key = STRIPE_SECRET_KEY
                    # This is a lightweight test call
                    stripe.Account.retrieve()
                    logger.info("✓ Stripe API connection successful")
                else:
                    logger.error("✗ Cannot test Stripe API - STRIPE_SECRET_KEY missing")
            except stripe.error.AuthenticationError as e:
                logger.error(f"✗ Stripe API authentication failed: {e}")
            except stripe.error.StripeError as e:
                logger.error(f"✗ Stripe API error: {e}")
            except Exception as e:
                logger.error(f"✗ Unexpected error testing Stripe API: {e}")
        else:
            logger.error("✗ Missing required Stripe variables - billing service will not work properly")

        logger.info("=========================================")

    def _should_refresh_cache(self) -> bool:
        if not self._pricing_cache or not self._cache_timestamp:
            return True
        return (datetime.now() - self._cache_timestamp).total_seconds() > self._cache_duration

    def _extract_price_amount(self, price_object, price_id: str) -> Optional[float]:
        """
        Extract price amount from Stripe price object handling all pricing models.
        Returns price in cents (float for micro-pricing) or None if no valid pricing found.

        For micro-pricing (like $0.0001), Stripe uses unit_amount_decimal field.
        This method converts all pricing to cents for consistent handling.
        """
        logger.info(
            f"Extracting price from {price_id}: "
            f"billing_scheme={getattr(price_object, 'billing_scheme', 'missing')}, "
            f"type={getattr(price_object, 'type', 'missing')}, "
            f"active={getattr(price_object, 'active', 'missing')}"
        )

        # Log all available price-related attributes for debugging
        unit_amount = getattr(price_object, 'unit_amount', None)
        unit_amount_decimal = getattr(price_object, 'unit_amount_decimal', None)
        custom_unit_amount = getattr(price_object, 'custom_unit_amount', None)
        tiers = getattr(price_object, 'tiers', None)
        currency_options = getattr(price_object, 'currency_options', None)

        logger.info(
            f"Price object attributes for {price_id}: "
            f"unit_amount={unit_amount}, "
            f"unit_amount_decimal={unit_amount_decimal}, "
            f"custom_unit_amount={custom_unit_amount is not None}, "
            f"tiers_count={len(tiers) if tiers else 0}, "
            f"currency_options={list(currency_options.keys()) if currency_options else []}"
        )

        # 1. Check unit_amount_decimal FIRST for micro-pricing (like $0.0001, $0.0002)
        if unit_amount_decimal is not None:
            try:
                # Parse as string to avoid float precision issues
                decimal_str = str(unit_amount_decimal).strip()
                logger.info(f"Processing unit_amount_decimal: '{decimal_str}'")

                # Convert to Decimal for precise calculations
                decimal_value = Decimal(decimal_str)

                # For micro-pricing, unit_amount_decimal appears to already be in the correct scale
                # Dashboard shows $0.0002, API returns 0.02 -> this IS 0.02 cents
                # Dashboard shows $0.0001, API returns 0.01 -> this IS 0.01 cents
                # Dashboard shows $40.00, API returns 4000 -> this IS 4000 cents
                price_amount = float(decimal_value)

                logger.info(f"Using unit_amount_decimal directly: {decimal_str} -> {price_amount} cents")
                return price_amount

            except (ValueError, TypeError, InvalidOperation) as e:
                logger.warning(f"Failed to parse unit_amount_decimal '{unit_amount_decimal}': {e}")

        # 2. Standard case: unit_amount (for regular pricing in cents)
        if unit_amount is not None and unit_amount > 0:
            logger.info(f"Using unit_amount: {unit_amount} cents")
            return float(unit_amount)

        # 3. Check custom_unit_amount for variable pricing
        if custom_unit_amount is not None:
            if hasattr(custom_unit_amount, 'minimum') and custom_unit_amount.minimum is not None:
                logger.info(f"Using custom_unit_amount.minimum: {custom_unit_amount.minimum}")
                return float(custom_unit_amount.minimum)
            elif hasattr(custom_unit_amount, 'maximum') and custom_unit_amount.maximum is not None:
                logger.info(f"Using custom_unit_amount.maximum: {custom_unit_amount.maximum}")
                return float(custom_unit_amount.maximum)

        # 4. Check tiered pricing
        if tiers and len(tiers) > 0:
            first_tier = tiers[0]
            logger.info(
                f"Checking first tier: {vars(first_tier) if hasattr(first_tier, '__dict__') else first_tier}"
            )

            # Check first tier for unit_amount
            if hasattr(first_tier, 'unit_amount') and first_tier.unit_amount is not None:
                logger.info(f"Using first tier unit_amount: {first_tier.unit_amount}")
                return float(first_tier.unit_amount)
            # Check first tier for unit_amount_decimal
            elif hasattr(first_tier, 'unit_amount_decimal') and first_tier.unit_amount_decimal is not None:
                try:
                    decimal_value = Decimal(str(first_tier.unit_amount_decimal))
                    price_amount = float(decimal_value * 100)
                    logger.info(
                        f"Using first tier unit_amount_decimal: {first_tier.unit_amount_decimal} -> {price_amount} cents"
                    )
                    return price_amount
                except (ValueError, TypeError, InvalidOperation) as e:
                    logger.warning(f"Failed to parse tier unit_amount_decimal: {e}")
            # Check first tier for flat_amount
            elif hasattr(first_tier, 'flat_amount') and first_tier.flat_amount is not None:
                logger.info(f"Using first tier flat_amount: {first_tier.flat_amount}")
                return float(first_tier.flat_amount)

        # 5. Check currency_options for multi-currency prices
        if currency_options:
            # Try USD first, then any available currency
            currencies_to_try = ['usd'] + [c for c in currency_options.keys() if c != 'usd']
            for currency in currencies_to_try:
                if currency in currency_options:
                    options = currency_options[currency]
                    logger.info(
                        f"Checking currency_options[{currency}]: {vars(options) if hasattr(options, '__dict__') else options}"
                    )

                    # Check unit_amount_decimal first
                    if hasattr(options, 'unit_amount_decimal') and options.unit_amount_decimal is not None:
                        try:
                            decimal_value = Decimal(str(options.unit_amount_decimal))
                            price_amount = float(decimal_value * 100)
                            logger.info(
                                f"Using currency_options[{currency}].unit_amount_decimal: {options.unit_amount_decimal} -> {price_amount} cents"
                            )
                            return price_amount
                        except (ValueError, TypeError, InvalidOperation) as e:
                            logger.warning(f"Failed to parse currency option unit_amount_decimal: {e}")

                    # Check unit_amount
                    if hasattr(options, 'unit_amount') and options.unit_amount is not None:
                        logger.info(f"Using currency_options[{currency}].unit_amount: {options.unit_amount}")
                        return float(options.unit_amount)

        logger.warning(
            f"No valid pricing amount found for {price_id}. "
            f"unit_amount={unit_amount}, "
            f"unit_amount_decimal={unit_amount_decimal}, "
            f"custom_unit_amount={custom_unit_amount}, "
            f"tiers={len(tiers) if tiers else 0}, "
            f"currency_options={list(currency_options.keys()) if currency_options else []}"
        )
        return None

    def get_usage_pricing(self) -> Dict[UsageType, Dict]:
        """Fetch usage pricing from Stripe or return cached values"""
        if not self._should_refresh_cache():
            return self._pricing_cache

        try:
            token_price_id = STRIPE_TOKEN_PRICE_ID
            span_price_id = STRIPE_SPAN_PRICE_ID

            pricing = {}

            if token_price_id:
                try:
                    token_price = stripe.Price.retrieve(token_price_id, expand=['currency_options', 'tiers'])

                    # Add detailed logging for debugging price configuration
                    logger.info(
                        f"Retrieved token price {token_price_id}: type={getattr(token_price, 'type', 'unknown')}, "
                        f"unit_amount={getattr(token_price, 'unit_amount', 'missing')}, "
                        f"billing_scheme={getattr(token_price, 'billing_scheme', 'missing')}, "
                        f"active={getattr(token_price, 'active', 'missing')}"
                    )

                    price_amount = self._extract_price_amount(token_price, token_price_id)

                    if price_amount is not None:
                        pricing[UsageType.TOKENS] = {
                            'price_per_unit': Decimal(str(price_amount)) / 100,
                            'unit_size': getattr(token_price.transform_quantity, 'divide_by', 1000)
                            if hasattr(token_price, 'transform_quantity') and token_price.transform_quantity
                            else 1000,
                            'display_unit': 'thousand tokens',
                            'stripe_price_id': token_price_id,
                        }
                        logger.info(
                            f"Token pricing configured: ${price_amount / 100:.4f} per {pricing[UsageType.TOKENS]['unit_size']} tokens"
                        )
                    else:
                        logger.error(f"Token price {token_price_id} has no valid pricing amount")
                        raise ValueError("Token price has no valid pricing amount")

                except (stripe.error.StripeError, ValueError, TypeError, AttributeError) as e:
                    logger.warning(f"Failed to retrieve token price {token_price_id}: {e}, using default")
                    pricing[UsageType.TOKENS] = {
                        'price_per_unit': Decimal("0.0002"),  # $0.0002 per 1000 tokens
                        'unit_size': 1000,
                        'display_unit': 'thousand tokens',
                    }
            else:
                logger.info("No STRIPE_TOKEN_PRICE_ID configured, using default token pricing")
                pricing[UsageType.TOKENS] = {
                    'price_per_unit': Decimal("0.0002"),  # $0.0002 per 1000 tokens
                    'unit_size': 1000,
                    'display_unit': 'thousand tokens',
                }

            if span_price_id:
                try:
                    span_price = stripe.Price.retrieve(span_price_id, expand=['currency_options', 'tiers'])

                    # Add detailed logging for debugging price configuration
                    logger.info(
                        f"Retrieved span price {span_price_id}: type={getattr(span_price, 'type', 'unknown')}, "
                        f"unit_amount={getattr(span_price, 'unit_amount', 'missing')}, "
                        f"billing_scheme={getattr(span_price, 'billing_scheme', 'missing')}, "
                        f"active={getattr(span_price, 'active', 'missing')}"
                    )

                    price_amount = self._extract_price_amount(span_price, span_price_id)

                    if price_amount is not None:
                        pricing[UsageType.SPANS] = {
                            'price_per_unit': Decimal(str(price_amount)) / 100,
                            'unit_size': getattr(span_price.transform_quantity, 'divide_by', 1000)
                            if hasattr(span_price, 'transform_quantity') and span_price.transform_quantity
                            else 1000,
                            'display_unit': 'thousand spans',
                            'stripe_price_id': span_price_id,
                        }
                        logger.info(
                            f"Span pricing configured: ${price_amount / 100:.4f} per {pricing[UsageType.SPANS]['unit_size']} spans"
                        )
                    else:
                        logger.error(f"Span price {span_price_id} has no valid pricing amount")
                        raise ValueError("Span price has no valid pricing amount")

                except (stripe.error.StripeError, ValueError, TypeError, AttributeError) as e:
                    logger.warning(f"Failed to retrieve span price {span_price_id}: {e}, using default")
                    pricing[UsageType.SPANS] = {
                        'price_per_unit': Decimal("0.0001"),  # $0.0001 per 1000 spans
                        'unit_size': 1000,
                        'display_unit': 'thousand spans',
                    }
            else:
                logger.info("No STRIPE_SPAN_PRICE_ID configured, using default span pricing")
                pricing[UsageType.SPANS] = {
                    'price_per_unit': Decimal("0.0001"),  # $0.0001 per 1000 spans
                    'unit_size': 1000,
                    'display_unit': 'thousand spans',
                }

            self._pricing_cache = pricing
            self._cache_timestamp = datetime.now()

        except stripe.error.StripeError as e:
            logger.error(f"Failed to fetch pricing from Stripe: {e}")
            return {
                UsageType.TOKENS: {
                    'price_per_unit': Decimal("0.0002"),  # $0.0002 per 1000 tokens
                    'unit_size': 1000,
                    'display_unit': 'thousand tokens',
                },
                UsageType.SPANS: {
                    'price_per_unit': Decimal("0.0001"),  # $0.0001 per 1000 spans
                    'unit_size': 1000,
                    'display_unit': 'thousand spans',
                },
            }
        except Exception as e:
            logger.error(f"Unexpected error in get_usage_pricing: {e}")
            return {
                UsageType.TOKENS: {
                    'price_per_unit': Decimal("0.0002"),  # $0.0002 per 1000 tokens
                    'unit_size': 1000,
                    'display_unit': 'thousand tokens',
                },
                UsageType.SPANS: {
                    'price_per_unit': Decimal("0.0001"),  # $0.0001 per 1000 spans
                    'unit_size': 1000,
                    'display_unit': 'thousand spans',
                },
            }

        return self._pricing_cache

    def get_seat_price(self) -> int:
        """Get per-seat price in cents from Stripe or environment"""
        try:
            main_price_id = STRIPE_SUBSCRIPTION_PRICE_ID
            if main_price_id:
                price = stripe.Price.retrieve(main_price_id, expand=['currency_options', 'tiers'])
                if price.recurring and price.recurring.usage_type == 'licensed':
                    price_amount = self._extract_price_amount(price, main_price_id)
                    if price_amount is not None:
                        # Convert float to int for seat pricing (seats should be whole cents)
                        return int(round(price_amount))
                    else:
                        logger.warning(
                            f"Seat price {main_price_id} has no valid pricing amount, falling back to default"
                        )
                else:
                    logger.warning(f"Seat price {main_price_id} is not configured for licensed usage")
        except stripe.error.StripeError as e:
            logger.error(f"Failed to fetch seat price from Stripe: {e}")
        except Exception as e:
            logger.error(f"Unexpected error fetching seat price: {e}")

        return int(os.getenv("STRIPE_SEAT_PRICE_CENTS", "4000"))

    async def get_usage_for_period(
        self,
        orm: Session,
        org_id: str,
        period_start: datetime,
        period_end: datetime,
        project_id: Optional[str] = None,
    ) -> Dict[str, int]:
        """Get usage quantities for a billing period by querying ClickHouse directly"""
        from ..models import ProjectModel

        # Ensure we have timezone-aware datetimes
        if period_start.tzinfo is None:
            period_start = period_start.replace(tzinfo=timezone.utc)
        if period_end.tzinfo is None:
            period_end = period_end.replace(tzinfo=timezone.utc)

        # Convert to UTC for consistent ClickHouse querying
        period_start_utc = period_start.astimezone(timezone.utc)
        period_end_utc = period_end.astimezone(timezone.utc)

        # Validate that the period is reasonable (not more than 32 days for billing overview)
        period_duration = period_end_utc - period_start_utc
        if period_duration.days > 32:
            logger.warning(
                f"Billing period duration is {period_duration.days} days for org {org_id}, this may indicate a date scoping issue"
            )

        cache_key = (
            f"{org_id}:{period_start_utc.isoformat()}:{period_end_utc.isoformat()}:{project_id or 'all'}"
        )
        if cache_key in self._usage_cache:
            cached_data, cached_time = self._usage_cache[cache_key]
            if (datetime.now() - cached_time).total_seconds() < self._usage_cache_ttl:
                logger.debug(f"Returning cached usage data for org {org_id}")
                return cached_data

        # If project_id is specified, only query for that project
        if project_id:
            # Verify the project belongs to the org
            project = (
                orm.query(ProjectModel.id)
                .filter(ProjectModel.org_id == org_id, ProjectModel.id == project_id)
                .first()
            )
            if not project:
                empty_result = {}
                self._usage_cache[cache_key] = (empty_result, datetime.now())
                return empty_result
            project_ids = [project_id]
        else:
            projects = orm.query(ProjectModel.id).filter(ProjectModel.org_id == org_id).all()
            project_ids = [str(p.id) for p in projects]

            if not project_ids:
                empty_result = {}
                self._usage_cache[cache_key] = (empty_result, datetime.now())
                return empty_result

        clickhouse_client = get_clickhouse()

        try:
            usage_query = """
                SELECT 
                    COUNT(*) as span_count,
                    SUM(
                        COALESCE(
                            toUInt64OrZero(ifNull(SpanAttributes['gen_ai.usage.total_tokens'], '0')),
                            toUInt64OrZero(ifNull(SpanAttributes['gen_ai.usage.prompt_tokens'], '0')) +
                            toUInt64OrZero(ifNull(SpanAttributes['gen_ai.usage.completion_tokens'], '0')) +
                            toUInt64OrZero(ifNull(SpanAttributes['gen_ai.usage.cache_read_input_tokens'], '0')) +
                            toUInt64OrZero(ifNull(SpanAttributes['gen_ai.usage.reasoning_tokens'], '0'))
                        )
                    ) as total_tokens
                FROM otel_2.otel_traces
                WHERE project_id IN %(project_ids)s
                    AND Timestamp >= %(period_start)s
                    AND Timestamp <= %(period_end)s
            """

            # Use timezone-aware formatting for ClickHouse (ClickHouse expects UTC)
            formatted_start = period_start_utc.strftime('%Y-%m-%d %H:%M:%S')
            formatted_end = period_end_utc.strftime('%Y-%m-%d %H:%M:%S')

            logger.info(
                f"Querying usage for org {org_id} from {formatted_start} to {formatted_end} (project_ids: {project_ids})"
            )

            result = clickhouse_client.query(
                usage_query,
                {
                    'project_ids': project_ids,
                    'period_start': formatted_start,
                    'period_end': formatted_end,
                },
            )

            if result.result_rows:
                span_count, total_tokens = result.result_rows[0]

                logger.info(f"Usage data for org {org_id}: {total_tokens} total tokens, {span_count} spans")
            else:
                span_count, total_tokens = 0, 0
                logger.info(
                    f"No usage data found for org {org_id} in period {formatted_start} to {formatted_end}"
                )

            usage_data = {
                'tokens': int(total_tokens) if total_tokens else 0,
                'spans': int(span_count) if span_count else 0,
            }

            logger.info(
                f"Final usage data for org {org_id}: {usage_data['tokens']} tokens and {usage_data['spans']} spans"
            )

            self._usage_cache[cache_key] = (usage_data, datetime.now())

            if len(self._usage_cache) > 100:
                current_time = datetime.now()
                expired_keys = [
                    k
                    for k, (_, cached_time) in self._usage_cache.items()
                    if (current_time - cached_time).total_seconds() > self._usage_cache_ttl
                ]
                for key in expired_keys:
                    del self._usage_cache[key]

            return usage_data

        except Exception as e:
            logger.error(f"Error querying usage data for org {org_id}: {e}")
            return {}

    async def get_usage_by_project_for_period(
        self, orm: Session, org_id: str, period_start: datetime, period_end: datetime
    ) -> Dict[str, Dict[str, int]]:
        """Get usage quantities for a billing period broken down by project"""
        from ..models import ProjectModel

        # Ensure we have timezone-aware datetimes
        if period_start.tzinfo is None:
            period_start = period_start.replace(tzinfo=timezone.utc)
        if period_end.tzinfo is None:
            period_end = period_end.replace(tzinfo=timezone.utc)

        # Convert to UTC for consistent ClickHouse querying
        period_start_utc = period_start.astimezone(timezone.utc)
        period_end_utc = period_end.astimezone(timezone.utc)

        projects = orm.query(ProjectModel.id, ProjectModel.name).filter(ProjectModel.org_id == org_id).all()
        project_ids = [str(p.id) for p in projects]
        project_names = {str(p.id): p.name for p in projects}

        if not project_ids:
            return {}

        clickhouse_client = get_clickhouse()

        try:
            # Same query as get_usage_for_period but grouped by project_id
            usage_query = """
                SELECT 
                    project_id,
                    COUNT(*) as span_count,
                    SUM(
                        COALESCE(
                            toUInt64OrZero(ifNull(SpanAttributes['gen_ai.usage.total_tokens'], '0')),
                            toUInt64OrZero(ifNull(SpanAttributes['gen_ai.usage.prompt_tokens'], '0')) +
                            toUInt64OrZero(ifNull(SpanAttributes['gen_ai.usage.completion_tokens'], '0')) +
                            toUInt64OrZero(ifNull(SpanAttributes['gen_ai.usage.cache_read_input_tokens'], '0')) +
                            toUInt64OrZero(ifNull(SpanAttributes['gen_ai.usage.reasoning_tokens'], '0'))
                        )
                    ) as total_tokens
                FROM otel_2.otel_traces
                WHERE project_id IN %(project_ids)s
                    AND Timestamp >= %(period_start)s
                    AND Timestamp <= %(period_end)s
                GROUP BY project_id
            """

            formatted_start = period_start_utc.strftime('%Y-%m-%d %H:%M:%S')
            formatted_end = period_end_utc.strftime('%Y-%m-%d %H:%M:%S')

            logger.info(
                f"Querying per-project usage for org {org_id} from {formatted_start} to {formatted_end}"
            )

            result = clickhouse_client.query(
                usage_query,
                {
                    'project_ids': project_ids,
                    'period_start': formatted_start,
                    'period_end': formatted_end,
                },
            )

            project_usage = {}

            for row in result.result_rows:
                project_id, span_count, total_tokens = row

                project_usage[str(project_id)] = {
                    'tokens': int(total_tokens) if total_tokens else 0,
                    'spans': int(span_count) if span_count else 0,
                    'project_name': project_names.get(str(project_id), 'Unknown Project'),
                }

            # Include projects with zero usage
            for project_id, project_name in project_names.items():
                if project_id not in project_usage:
                    project_usage[project_id] = {
                        'tokens': 0,
                        'spans': 0,
                        'project_name': project_name,
                    }

            logger.info(f"Found usage data for {len(project_usage)} projects in org {org_id}")
            return project_usage

        except Exception as e:
            logger.error(f"Error querying per-project usage data for org {org_id}: {e}")
            return {}

    async def calculate_usage_costs(self, usage_quantities: Dict[str, int]) -> Dict[str, int]:
        """Calculate costs from usage quantities

        For micro-pricing (like $0.0001, $0.0002), we enforce a minimum charge threshold
        to avoid charging customers $0.00. Costs are only included if they round to at least 1 cent.
        """
        costs = {}
        pricing = self.get_usage_pricing()

        for usage_type_str, quantity in usage_quantities.items():
            try:
                usage_type = UsageType(usage_type_str)
                if usage_type in pricing:
                    price_config = pricing[usage_type]

                    units = Decimal(str(quantity)) / Decimal(str(price_config['unit_size']))
                    cost_dollars = units * price_config['price_per_unit']
                    cost_cents = cost_dollars * 100
                    final_cost_cents = int(cost_cents.quantize(Decimal('1'), rounding='ROUND_HALF_UP'))

                    # Only include costs that are at least 1 cent to avoid $0.00 charges
                    if final_cost_cents >= 1:
                        costs[usage_type_str] = final_cost_cents
                        logger.info(
                            f"Usage cost for {usage_type_str}: {quantity} units -> {final_cost_cents} cents "
                            f"(${cost_dollars:.6f})"
                        )
                    else:
                        logger.info(
                            f"Usage cost for {usage_type_str}: {quantity} units -> {cost_cents:.6f} cents "
                            f"(below 1 cent threshold, not charged)"
                        )
            except (ValueError, TypeError, InvalidOperation) as e:
                logger.warning(
                    f"Error calculating cost for usage type {usage_type_str} with quantity {quantity}: {e}"
                )
                continue
            except Exception as e:
                logger.error(f"Unexpected error calculating cost for usage type {usage_type_str}: {e}")
                continue

        return costs

    async def create_billing_period_snapshot(
        self, orm: Session, org: OrgModel, period_start: datetime, period_end: datetime
    ) -> BillingPeriod:
        """Create a billing snapshot for the period"""

        seat_count = org.paid_member_count or 1
        seat_cost = seat_count * self.get_seat_price()

        usage_quantities = await self.get_usage_for_period(orm, str(org.id), period_start, period_end)

        usage_costs = await self.calculate_usage_costs(usage_quantities)

        total_cost = seat_cost + sum(usage_costs.values())

        billing_period = BillingPeriod(
            org_id=org.id,
            period_start=period_start,
            period_end=period_end,
            seat_cost=seat_cost,
            seat_count=seat_count,
            usage_costs=usage_costs,
            usage_quantities=usage_quantities,
            total_cost=total_cost,
            status='pending',
        )

        orm.add(billing_period)
        orm.commit()

        return billing_period


billing_service = BillingService()


# Log final validation summary when module is imported
def _log_billing_service_ready():
    """Log final status of billing service configuration"""
    logger.info("=== Billing Service Configuration Summary ===")

    # Check if all required variables are present
    required_vars = [
        STRIPE_SECRET_KEY,
        STRIPE_SUBSCRIPTION_PRICE_ID,
        STRIPE_TOKEN_PRICE_ID,
        STRIPE_SPAN_PRICE_ID,
    ]
    all_present = all(var for var in required_vars)

    if all_present:
        logger.info("✓ All Stripe variables configured - Billing service ready for production")
    else:
        missing = [
            name
            for name, var in [
                ("STRIPE_SECRET_KEY", STRIPE_SECRET_KEY),
                ("STRIPE_SUBSCRIPTION_PRICE_ID", STRIPE_SUBSCRIPTION_PRICE_ID),
                ("STRIPE_TOKEN_PRICE_ID", STRIPE_TOKEN_PRICE_ID),
                ("STRIPE_SPAN_PRICE_ID", STRIPE_SPAN_PRICE_ID),
            ]
            if not var
        ]
        logger.error(f"✗ Billing service NOT ready - missing: {', '.join(missing)}")
        logger.error("This will cause billing operations to fail or use fallback values")

    logger.info("============================================")


# Call validation when module is imported
_log_billing_service_ready()
