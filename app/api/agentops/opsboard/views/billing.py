from typing import List, Optional, Dict
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, field_validator
from fastapi import Depends, HTTPException, Query
from sqlalchemy.orm import Session
import stripe
import logging

from agentops.common.orm import get_orm_session
from agentops.common.route_config import BaseView
from agentops.common.views import add_cors_headers
from agentops.common.environment import APP_URL
from agentops.api.environment import STRIPE_SECRET_KEY, STRIPE_SUBSCRIPTION_PRICE_ID
from ..models import OrgModel, BillingPeriod
from ..services.billing_service import billing_service

logger = logging.getLogger(__name__)


class UsageCostBreakdown(BaseModel):
    usage_type: str
    quantity: int
    cost_cents: int


class BillingPeriodResponse(BaseModel):
    id: str
    period_start: str
    period_end: str
    seat_cost: int
    seat_count: int
    usage_costs: Dict[str, int]
    usage_quantities: Dict[str, int]
    usage_breakdown: List[UsageCostBreakdown]
    total_cost: int
    status: str

    @field_validator('period_start', 'period_end', mode='before')
    def format_datetime(cls, v) -> str:
        """Ensure datetime fields are formatted as ISO strings."""
        if isinstance(v, datetime):
            return v.isoformat()
        return v


# costs are in cents
class ProjectUsageBreakdown(BaseModel):
    project_id: str
    project_name: str
    tokens: int
    spans: int
    token_cost: int
    span_cost: int
    total_cost: int


class BillingDashboardResponse(BaseModel):
    current_period: Optional[BillingPeriodResponse]
    past_periods: List[BillingPeriodResponse]
    total_spent_all_time: int
    is_legacy_billing: bool = False
    legacy_cancellation_date: Optional[str] = None
    project_breakdown: Optional[List[ProjectUsageBreakdown]] = None

    @field_validator('legacy_cancellation_date', mode='before')
    def format_legacy_date(cls, v) -> Optional[str]:
        """Format datetime as ISO string if present."""
        if isinstance(v, datetime):
            return v.isoformat()
        return v


class BillingDashboardView(BaseView):
    """Get billing dashboard data with cost breakdown"""

    @add_cors_headers(
        origins=[APP_URL],
        methods=["GET", "OPTIONS"],
    )
    async def __call__(
        self,
        org_id: str,
        start_date: Optional[str] = Query(None, alias="start_date"),
        end_date: Optional[str] = Query(None, alias="end_date"),
        project_id: Optional[str] = Query(None, alias="project_id"),
        period: Optional[str] = Query(None, alias="period"),  # For backward compatibility
        orm: Session = Depends(get_orm_session),
    ) -> BillingDashboardResponse:
        """Get billing dashboard data with cost breakdown"""

        # Handle FastAPI Query objects when called directly in tests

        # Check for various FastAPI Query object types
        if hasattr(start_date, 'default') or str(type(start_date)).find('Query') != -1:
            logger.debug(f"Converting start_date Query object to None: {type(start_date)}")
            start_date = None
        if hasattr(end_date, 'default') or str(type(end_date)).find('Query') != -1:
            logger.debug(f"Converting end_date Query object to None: {type(end_date)}")
            end_date = None
        if hasattr(project_id, 'default') or str(type(project_id)).find('Query') != -1:
            logger.debug(f"Converting project_id Query object to None: {type(project_id)}")
            project_id = None
        if hasattr(period, 'default') or str(type(period)).find('Query') != -1:
            logger.debug(f"Converting period Query object to None: {type(period)}")
            period = None

        logger.debug(
            f"Final parameter values: period={period}, start_date={start_date}, end_date={end_date}, project_id={project_id}"
        )

        org = OrgModel.get_by_id_summary(orm, org_id, self.request.state.session.user_id)
        if not org or not org.is_user_member(self.request.state.session.user_id):
            raise HTTPException(status_code=403, detail="Access denied")

        now = datetime.now(timezone.utc)

        # Handle specific billing period if provided (backward compatibility)
        if period:
            try:
                billing_period = (
                    orm.query(BillingPeriod)
                    .filter(BillingPeriod.id == period, BillingPeriod.org_id == org_id)
                    .first()
                )

                if not billing_period:
                    raise HTTPException(status_code=404, detail="Billing period not found")

                # Convert stored billing period to response format
                usage_breakdown = []
                for usage_type, quantity in billing_period.usage_quantities.items():
                    cost = billing_period.usage_costs.get(usage_type, 0)
                    usage_breakdown.append(
                        UsageCostBreakdown(
                            usage_type=usage_type,
                            quantity=quantity,
                            cost_cents=cost,
                        )
                    )

                stored_period = BillingPeriodResponse(
                    id=str(billing_period.id),
                    period_start=billing_period.period_start,
                    period_end=billing_period.period_end,
                    seat_cost=billing_period.seat_cost,
                    seat_count=billing_period.seat_count,
                    usage_costs=billing_period.usage_costs,
                    usage_quantities=billing_period.usage_quantities,
                    usage_breakdown=usage_breakdown,
                    total_cost=billing_period.total_cost,
                    status=billing_period.status,
                )

                return BillingDashboardResponse(
                    current_period=stored_period,
                    past_periods=[],
                    total_spent_all_time=stored_period.total_cost,
                    project_breakdown=[],  # Not supported for stored periods
                )

            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid period ID format")

        # Handle custom date range if provided
        if start_date and end_date and isinstance(start_date, str) and isinstance(end_date, str):
            try:
                s_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                e_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                if e_date.hour == 0 and e_date.minute == 0 and e_date.second == 0:
                    e_date = e_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use ISO 8601 format.")

            manual_usage = await billing_service.get_usage_for_period(orm, org_id, s_date, e_date, project_id)
            manual_usage_costs = await billing_service.calculate_usage_costs(manual_usage)
            project_usage = await billing_service.get_usage_by_project_for_period(orm, org_id, s_date, e_date)

            usage_breakdown = []
            for usage_type, quantity in manual_usage.items():
                cost = manual_usage_costs.get(usage_type, 0)
                usage_breakdown.append(
                    UsageCostBreakdown(
                        usage_type=usage_type,
                        quantity=quantity,
                        cost_cents=cost,
                    )
                )

            seat_price = billing_service.get_seat_price()
            manual_period = BillingPeriodResponse(
                id="custom",
                period_start=s_date.isoformat(),
                period_end=e_date.isoformat(),
                seat_cost=org.paid_member_count * seat_price,
                seat_count=org.paid_member_count,
                usage_costs=manual_usage_costs,
                usage_quantities=manual_usage,
                usage_breakdown=usage_breakdown,
                total_cost=(org.paid_member_count * seat_price) + sum(manual_usage_costs.values()),
                status="custom",
            )

            project_breakdown = []
            if project_usage:
                usage_costs_service = billing_service
                for proj_id, usage_data in project_usage.items():
                    # If project_id filter is specified, only include that project
                    if project_id and proj_id != project_id:
                        continue
                    project_usage_dict = {'tokens': usage_data['tokens'], 'spans': usage_data['spans']}
                    project_costs = await usage_costs_service.calculate_usage_costs(project_usage_dict)

                    project_breakdown.append(
                        ProjectUsageBreakdown(
                            project_id=proj_id,
                            project_name=usage_data['project_name'],
                            tokens=usage_data['tokens'],
                            spans=usage_data['spans'],
                            token_cost=project_costs.get('tokens', 0),
                            span_cost=project_costs.get('spans', 0),
                            total_cost=project_costs.get('tokens', 0) + project_costs.get('spans', 0),
                        )
                    )

            return BillingDashboardResponse(
                current_period=manual_period,
                past_periods=[],
                total_spent_all_time=manual_period.total_cost,
                project_breakdown=project_breakdown,
            )

        # Use Stripe billing period by default, or custom date range if provided

        current_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        current_end = now

        logger.info(f"Initial billing period for org {org_id}: {current_start} to {current_end}")

        if org.subscription_id and STRIPE_SECRET_KEY:
            try:
                stripe.api_key = STRIPE_SECRET_KEY
                subscription = stripe.Subscription.retrieve(org.subscription_id)

                if subscription:
                    subscription_status = subscription.get('status', 'unknown')

                    if subscription_status in ['trialing', 'active']:
                        from .orgs import extract_subscription_period_dates

                        period_start, period_end = extract_subscription_period_dates(subscription)

                        if period_start and period_end:
                            current_start = datetime.fromtimestamp(period_start, tz=timezone.utc)
                            current_end = datetime.fromtimestamp(period_end, tz=timezone.utc)
                            logger.info(
                                f"Using Stripe billing period for org {org_id}: "
                                f"{current_start} to {current_end}"
                            )
                        else:
                            logger.warning(
                                f"Could not extract dates from Stripe subscription {org.subscription_id}"
                            )
                            logger.warning(f"Falling back to monthly calendar period for org {org_id}")
                    else:
                        starts_at = subscription.get('start_date') or subscription.get('started_at')
                        if starts_at and subscription_status in ['scheduled', 'incomplete']:
                            scheduled_start = datetime.fromtimestamp(starts_at, tz=timezone.utc)
                            scheduled_end = scheduled_start + timedelta(days=30)

                            current_start = scheduled_start
                            current_end = scheduled_end

                        else:
                            logger.warning(
                                f"Subscription {org.subscription_id} has unsupported status "
                                f"'{subscription_status}' - falling back to monthly calendar period"
                            )

            except Exception as e:
                logger.error(f"Failed to retrieve Stripe subscription {org.subscription_id}: {e}")
                logger.warning(
                    f"Falling back to monthly calendar period for org {org_id} due to Stripe error"
                )

        logger.info(f"Final billing period for org {org_id}: {current_start} to {current_end}")
        current_usage = await billing_service.get_usage_for_period(
            orm, org_id, current_start, current_end, project_id
        )
        project_usage = await billing_service.get_usage_by_project_for_period(
            orm, org_id, current_start, current_end
        )

        current_period = None
        if current_usage or org.paid_member_count > 0:
            usage_costs = await billing_service.calculate_usage_costs(current_usage)

            seat_price = billing_service.get_seat_price()

            usage_breakdown = []
            for usage_type, quantity in current_usage.items():
                cost = usage_costs.get(usage_type, 0)
                usage_breakdown.append(
                    UsageCostBreakdown(
                        usage_type=usage_type,
                        quantity=quantity,
                        cost_cents=cost,
                    )
                )

            current_period = BillingPeriodResponse(
                id="current",
                period_start=current_start,
                period_end=current_end,
                seat_cost=org.paid_member_count * seat_price,
                seat_count=org.paid_member_count,
                usage_costs=usage_costs,
                usage_quantities=current_usage,
                usage_breakdown=usage_breakdown,
                total_cost=(org.paid_member_count * seat_price) + sum(usage_costs.values()),
                status="current",
            )

        # For now, we're not showing historical periods since we're moving away from stored periods
        # In the future, this could be calculated from Stripe's billing history if needed
        past_period_responses = []
        total_spent = current_period.total_cost if current_period else 0

        is_legacy = False
        legacy_cancellation_date = None

        if org.subscription_id and STRIPE_SECRET_KEY:
            try:
                subscription = stripe.Subscription.retrieve(org.subscription_id)
                has_current_pricing = False
                subscription_items = subscription.get('items', {}).get('data', [])
                logger.info(f"Subscription has {len(subscription_items)} items")

                for item in subscription_items:
                    price_id = item.get('price', {}).get('id')
                    logger.info(
                        f"Subscription item price ID: {price_id}, "
                        f"current price ID: {STRIPE_SUBSCRIPTION_PRICE_ID}"
                    )
                    if price_id == STRIPE_SUBSCRIPTION_PRICE_ID:
                        has_current_pricing = True
                        break

                # Legacy if no current pricing found OR subscription is canceled/canceling
                is_canceling = (
                    subscription.get('cancel_at_period_end', False)
                    or subscription.get('canceled_at') is not None
                    or subscription.get('cancel_at') is not None
                    or subscription.get('status') in ['canceled', 'unpaid', 'incomplete_expired']
                )
                is_legacy = not has_current_pricing or is_canceling
                logger.info(
                    f"Legacy determination: has_current_pricing={has_current_pricing}, "
                    f"is_canceling={is_canceling}, status={subscription.get('status')}, "
                    f"is_legacy={is_legacy}"
                )

                if is_legacy:
                    cancellation_timestamp = None
                    date_source = None

                    if subscription.get('cancel_at'):
                        cancellation_timestamp = subscription['cancel_at']
                        date_source = "cancel_at"
                    elif subscription.get('current_period_end'):
                        cancellation_timestamp = subscription['current_period_end']
                        date_source = "current_period_end"
                    elif subscription.get('canceled_at'):
                        cancellation_timestamp = subscription['canceled_at']
                        date_source = "canceled_at"

                    if cancellation_timestamp:
                        legacy_cancellation_date = datetime.fromtimestamp(
                            cancellation_timestamp, tz=timezone.utc
                        )
                        logger.info(
                            f"Set legacy cancellation date from Stripe {date_source}: "
                            f"{legacy_cancellation_date}"
                        )
                    else:
                        logger.warning(
                            f"Legacy subscription {org.subscription_id} has no cancellation date fields"
                        )

            except Exception as e:
                logger.error(f"Failed to check legacy subscription status: {e}")
                import traceback

                logger.error(traceback.format_exc())

        if is_legacy and not legacy_cancellation_date and current_period:
            legacy_cancellation_date = current_period.period_end
            logger.info(
                f"Using current period end as legacy cancellation date fallback: {legacy_cancellation_date}"
            )

        project_breakdown = []
        if project_usage:
            usage_costs_service = billing_service
            for proj_id, usage_data in project_usage.items():
                # If project_id filter is specified, only include that project
                if project_id and proj_id != project_id:
                    continue
                project_usage_dict = {'tokens': usage_data['tokens'], 'spans': usage_data['spans']}
                project_costs = await usage_costs_service.calculate_usage_costs(project_usage_dict)

                project_breakdown.append(
                    ProjectUsageBreakdown(
                        project_id=proj_id,
                        project_name=usage_data['project_name'],
                        tokens=usage_data['tokens'],
                        spans=usage_data['spans'],
                        token_cost=project_costs.get('tokens', 0),
                        span_cost=project_costs.get('spans', 0),
                        total_cost=project_costs.get('tokens', 0) + project_costs.get('spans', 0),
                    )
                )

        return BillingDashboardResponse(
            current_period=current_period,
            past_periods=past_period_responses,
            total_spent_all_time=total_spent,
            is_legacy_billing=is_legacy,
            legacy_cancellation_date=legacy_cancellation_date,
            project_breakdown=project_breakdown,
        )
