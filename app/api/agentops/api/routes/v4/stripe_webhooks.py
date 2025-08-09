import stripe
from fastapi import APIRouter, Request, HTTPException, Depends, Header
from sqlalchemy.orm import Session
from sqlalchemy import case
from datetime import datetime, timedelta, timezone
import logging
from typing import Dict, Any

from agentops.api.environment import STRIPE_WEBHOOK_SECRET, STRIPE_SUBSCRIPTION_PRICE_ID
from agentops.common.orm import get_orm_session
from agentops.opsboard.models import (
    OrgModel,
    PremStatus,
    UserOrgModel,
    OrgRoles,
    WebhookEvent,
    BillingPeriod,
    BillingAuditLog,
)
from agentops.opsboard.services.billing_service import billing_service

router = APIRouter()
logger = logging.getLogger(__name__)


async def sync_org_licenses(
    org: OrgModel, seat_quantity: int, orm: Session, event_id: str = None
) -> Dict[str, list]:
    """
    Sync organization member licenses based on seat quantity.
    Returns dict with 'newly_licensed' and 'newly_unlicensed' lists.
    """
    # Get all org members ordered by role priority
    members = (
        orm.query(UserOrgModel)
        .filter(UserOrgModel.org_id == org.id)
        .order_by(
            # Order by role: owner=1, admin=2, developer=3
            case(
                (UserOrgModel.role == OrgRoles.owner, 1),
                (UserOrgModel.role == OrgRoles.admin, 2),
                else_=3,
            ),
            UserOrgModel.user_id,  # Secondary sort by user_id for consistency
        )
        .all()
    )

    # Track changes for logging
    newly_licensed = []
    newly_unlicensed = []

    # Update license status based on seat quantity
    for i, member in enumerate(members):
        should_be_paid = i < seat_quantity

        if member.is_paid != should_be_paid:
            if should_be_paid:
                newly_licensed.append(member.user_email or str(member.user_id))
            else:
                newly_unlicensed.append(member.user_email or str(member.user_id))

            member.is_paid = should_be_paid

    # Add audit log for the sync action
    if newly_licensed or newly_unlicensed:
        # Find the org owner to use as the user_id for this system action
        owner_membership = (
            orm.query(UserOrgModel)
            .filter(UserOrgModel.org_id == org.id, UserOrgModel.role == OrgRoles.owner)
            .first()
        )
        system_user_id = owner_membership.user_id if owner_membership else None

        if system_user_id:
            audit_log = BillingAuditLog(
                org_id=org.id,
                user_id=system_user_id,  # Use org owner's ID for system actions
                action='licenses_synced_by_webhook',
                details={
                    'event_id': event_id,
                    'seat_quantity': seat_quantity,
                    'newly_licensed': newly_licensed,
                    'newly_unlicensed': newly_unlicensed,
                    'system_action': True,  # Flag to indicate this was a system action
                },
            )
            orm.add(audit_log)

    return {
        'newly_licensed': newly_licensed,
        'newly_unlicensed': newly_unlicensed,
        'total_members': len(members),
    }


async def is_event_processed(event_id: str, orm: Session) -> bool:
    """Check if we've already processed this webhook event."""
    return orm.query(WebhookEvent).filter(WebhookEvent.event_id == event_id).count() > 0


async def mark_event_processed(event_id: str, orm: Session):
    """Mark an event as processed."""
    webhook_event = WebhookEvent(event_id=event_id)
    orm.add(webhook_event)
    orm.commit()


def log_webhook_metric(event_type: str, status: str, metadata: Dict[str, Any] = None):
    """Log structured metrics for webhook processing for anomaly detection"""
    log_data = {
        "metric_type": "WEBHOOK_METRIC",
        "webhook_provider": "stripe",
        "event_type": event_type,
        "status": status,
        "timestamp": datetime.utcnow().isoformat(),
        **(metadata or {}),
    }
    logger.info(f"WEBHOOK_METRIC: {log_data}")


@router.post("/stripe-webhook", include_in_schema=False)
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None),
    orm: Session = Depends(get_orm_session),
):
    """
    Handle incoming Stripe webhooks.
    Find our webhooks here:
    https://dashboard.stripe.com/test/webhooks
    https://dashboard.stripe.com/webhooks
    """
    if not STRIPE_WEBHOOK_SECRET:
        logger.error(
            "✗ CRITICAL: STRIPE_WEBHOOK_SECRET is not configured - Cannot verify webhook signatures!"
        )
        logger.error("This means webhook events from Stripe cannot be validated and will be rejected.")
        logger.error("Set the STRIPE_WEBHOOK_SECRET environment variable to fix this issue.")
        log_webhook_metric("unknown", "config_error", {"error": "missing_webhook_secret"})
        raise HTTPException(status_code=500, detail="Webhook secret not configured")

    # Log webhook secret status (masked) for debugging
    masked_secret = (
        f"{STRIPE_WEBHOOK_SECRET[:8]}..." if len(STRIPE_WEBHOOK_SECRET) > 8 else STRIPE_WEBHOOK_SECRET
    )
    logger.debug(f"✓ Using webhook secret: {masked_secret}")

    # Also log if STRIPE_SUBSCRIPTION_PRICE_ID is missing (needed for subscription validation)
    if not STRIPE_SUBSCRIPTION_PRICE_ID:
        logger.warning("✗ STRIPE_SUBSCRIPTION_PRICE_ID not configured - Subscription validation may fail")

    if not stripe_signature:
        logger.error("Missing Stripe-Signature header.")
        log_webhook_metric("unknown", "missing_signature")
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")

    try:
        payload = await request.body()
        event = stripe.Webhook.construct_event(payload, stripe_signature, STRIPE_WEBHOOK_SECRET)
    except ValueError as e:  # Invalid payload
        logger.error(f"Invalid webhook payload: {e}")
        log_webhook_metric("unknown", "invalid_payload", {"error": str(e)})
        raise HTTPException(status_code=400, detail=f"Invalid payload: {e}")
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid webhook signature: {e}")
        log_webhook_metric("unknown", "invalid_signature", {"error": str(e)})
        raise HTTPException(status_code=400, detail=f"Invalid signature: {e}")
    except Exception as e:
        logger.error(f"Could not construct webhook event: {e}")
        log_webhook_metric("unknown", "construction_error", {"error": str(e), "error_type": type(e).__name__})
        raise HTTPException(status_code=500, detail=f"Could not construct event: {e}")

    log_webhook_metric(event.type, "received", {"event_id": event.id})

    try:
        if event.type == "checkout.session.completed":
            await handle_checkout_completed(event, orm)
        elif event.type == "customer.subscription.updated":
            await handle_subscription_updated(event, orm)
        elif event.type == "customer.subscription.deleted":
            await handle_subscription_deleted(event, orm)
        elif event.type == "invoice.payment_failed":
            await handle_payment_failed(event, orm)
        elif event.type == "charge.refunded":
            await handle_charge_refunded(event, orm)
        elif event.type == "invoice.created":
            await handle_invoice_created(event, orm)
        elif event.type == "invoice.payment_succeeded":
            await handle_invoice_payment_succeeded(event, orm)
        else:
            logger.debug(f"Received unhandled event type: {event.type}")
            log_webhook_metric(event.type, "unhandled")

        log_webhook_metric(event.type, "processed", {"event_id": event.id})

    except Exception as e:
        logger.error(f"Error processing webhook {event.type}: {e}")
        log_webhook_metric(
            event.type,
            "processing_error",
            {"error": str(e), "error_type": type(e).__name__, "event_id": event.id},
        )

    return {"status": "success"}


async def handle_checkout_completed(event, orm: Session):
    """Handle successful checkout completion."""
    if await is_event_processed(event.id, orm):
        logger.info(f"Event {event.id} already processed, skipping")
        return {"status": "already_processed"}

    checkout_session = event.data.object
    subscription_id = checkout_session.get("subscription")
    client_reference_id = checkout_session.get("client_reference_id")
    session_id = checkout_session.get("id")
    metadata = checkout_session.get("metadata", {})

    # Try to get org_id from metadata as fallback
    if not client_reference_id and metadata.get("org_id"):
        client_reference_id = metadata.get("org_id")
        logger.warning(
            f"client_reference_id missing from checkout.session.completed event. "
            f"Using org_id from metadata: {client_reference_id}. Session ID: {session_id}"
        )

    if not client_reference_id:
        error_msg = f"checkout.session.completed event missing client_reference_id. Session ID: {session_id}"
        logger.error(error_msg)
        log_webhook_metric(
            "checkout.session.completed",
            "missing_reference_id",
            {"session_id": session_id, "subscription_id": subscription_id},
        )
        return

    if not subscription_id:
        error_msg = f"checkout.session.completed event missing subscription_id. Session ID: {session_id}"
        logger.error(error_msg)
        log_webhook_metric(
            "checkout.session.completed",
            "missing_subscription_id",
            {"session_id": session_id, "client_reference_id": client_reference_id},
        )
        return

    try:
        subscription = stripe.Subscription.retrieve(subscription_id, expand=['items'])
        if not subscription or not subscription.get('items') or not subscription.get('items').get('data'):
            logger.error(f"Subscription {subscription_id} has no items or items data.")
            return

        items_data = subscription.get('items', {}).get('data', [])
        if not items_data:
            logger.error(f"Subscription {subscription_id} has no items data array or it is empty.")
            return

        purchased_price_id = items_data[0].get('price', {}).get('id')
        if not purchased_price_id:
            logger.error(f"Could not extract price ID from subscription {subscription_id}")
            return

        if purchased_price_id != STRIPE_SUBSCRIPTION_PRICE_ID:
            logger.error(
                f"Purchased price ID {purchased_price_id} does not match "
                f"expected STRIPE_SUBSCRIPTION_PRICE_ID {STRIPE_SUBSCRIPTION_PRICE_ID} for org {client_reference_id}."
            )
            log_webhook_metric(
                "checkout.session.completed",
                "price_mismatch",
                {
                    "purchased_price_id": purchased_price_id,
                    "expected_price_id": STRIPE_SUBSCRIPTION_PRICE_ID,
                    "org_id": client_reference_id,
                    "subscription_id": subscription_id,
                    "session_id": session_id,
                },
            )
            return

        subscription_status = subscription.get('status')
        if subscription_status not in ['active', 'trialing', 'scheduled']:
            logger.warning(
                f"Subscription {subscription_id} has status '{subscription_status}', "
                f"not 'active', 'trialing', or 'scheduled'"
            )

    except stripe.error.StripeError as e:
        logger.error(
            "BILLING_WEBHOOK_ERROR",
            extra={
                "event_type": event.type,
                "event_id": event.id,
                "org_id": client_reference_id,
                "subscription_id": subscription_id,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "requires_manual_intervention": True,
            },
        )
        raise HTTPException(status_code=500, detail=f"Stripe API error: {e}")

    org: OrgModel = orm.query(OrgModel).filter(OrgModel.id == client_reference_id).with_for_update().first()

    if org:
        if org.subscription_id == subscription_id:
            logger.info(f"Subscription {subscription_id} already processed for org {org.id}")
            log_webhook_metric(
                "checkout.session.completed",
                "duplicate_processing",
                {"org_id": str(org.id), "subscription_id": subscription_id},
            )
            return

        old_status = org.prem_status
        org.subscription_id = subscription_id
        org.prem_status = PremStatus.pro

        owner_member = (
            orm.query(UserOrgModel)
            .filter(UserOrgModel.org_id == org.id, UserOrgModel.role == OrgRoles.owner)
            .first()
        )

        if owner_member:
            owner_member.is_paid = True
            logger.info(f"Marked owner as paid for org {org.id}")
            # NOTE: We intentionally only license the owner at checkout
            # The subscription.updated webhook will handle syncing all purchased seats
            # This allows flexibility for manual license assignment in the future
        else:
            logger.warning(f"No owner found for org {org.id} - cannot mark as paid")

        try:
            orm.commit()
            await mark_event_processed(event.id, orm)

            # Log successful upgrade
            log_webhook_metric(
                "checkout.session.completed",
                "org_upgraded",
                {
                    "org_id": str(org.id),
                    "subscription_id": subscription_id,
                    "old_status": old_status.value if old_status else "none",
                    "new_status": "pro",
                },
            )
        except Exception as e:
            orm.rollback()
            logger.error(
                "BILLING_WEBHOOK_ERROR",
                extra={
                    "event_type": event.type,
                    "event_id": event.id,
                    "org_id": str(org.id) if org else client_reference_id,
                    "subscription_id": subscription_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "requires_manual_intervention": True,
                },
            )
            log_webhook_metric(
                "checkout.session.completed",
                "database_error",
                {
                    "org_id": str(org.id),
                    "subscription_id": subscription_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise HTTPException(status_code=500, detail="Database update failed")
    else:
        logger.error(f"Org not found with client_reference_id: {client_reference_id}")
        logger.error(
            "BILLING_WEBHOOK_ERROR",
            extra={
                "event_type": event.type,
                "event_id": event.id,
                "org_id": client_reference_id,
                "subscription_id": subscription_id,
                "error_type": "OrgNotFound",
                "error_message": f"Organization with ID {client_reference_id} not found after checkout.",
                "requires_manual_intervention": True,
            },
        )
        log_webhook_metric(
            "checkout.session.completed",
            "org_not_found",
            {
                "client_reference_id": client_reference_id,
                "subscription_id": subscription_id,
                "session_id": session_id,
            },
        )


async def handle_subscription_updated(event, orm: Session):
    """Handle subscription updates (status changes, plan changes, etc.)."""
    if await is_event_processed(event.id, orm):
        logger.info(f"Event {event.id} already processed, skipping")
        return {"status": "already_processed"}

    subscription = event.data.object
    subscription_id = subscription.get("id")
    status = subscription.get("status")
    current_period_end = subscription.get("current_period_end")

    org: OrgModel = (
        orm.query(OrgModel).filter(OrgModel.subscription_id == subscription_id).with_for_update().first()
    )

    if not org:
        logger.warning(f"No org found with subscription_id: {subscription_id}")
        return

    # Check if there was a recent manual license update to avoid race conditions
    recent_cutoff = datetime.now(timezone.utc) - timedelta(seconds=5)
    recent_manual_update = (
        orm.query(BillingAuditLog)
        .filter(
            BillingAuditLog.org_id == org.id,
            BillingAuditLog.action.in_(['member_licensed', 'member_unlicensed']),
            BillingAuditLog.created_at >= recent_cutoff,
        )
        .first()
    )

    if recent_manual_update:
        logger.info(
            f"Skipping license sync for org {org.id} due to recent manual update "
            f"(action: {recent_manual_update.action} at {recent_manual_update.created_at})"
        )
        skip_license_sync = True
    else:
        skip_license_sync = False

    # Extract seat quantity from subscription items and detect legacy subscriptions
    seat_quantity = 0
    is_legacy_subscription = True
    legacy_price_id = None
    items = subscription.get('items', {}).get('data', [])

    if items:
        for item in items:
            price = item.get('price', {})
            price_id = price.get('id')

            if price_id == STRIPE_SUBSCRIPTION_PRICE_ID:
                is_legacy_subscription = False
                seat_quantity = item.get('quantity', 0)
                break
            elif 'seat' in str(price.get('product', {}).get('name', '')).lower():
                legacy_price_id = price_id
                seat_quantity = item.get('quantity', 0)

    logger.info(
        f"Subscription updated for org {org.id}: status={status}, seat_quantity={seat_quantity}, is_legacy={is_legacy_subscription}"
    )
    # Handle legacy subscriptions - set them to cancel at period end
    # should be auto handled by the manual run of scripts/sunset_legacy_subscriptions.py
    # TODO: Remove this entire legacy subscription handling block (31 days after migration)
    if is_legacy_subscription and status == "active":
        # Check if we need to set cancellation
        if not subscription.get('cancel_at_period_end'):
            try:
                logger.info(f"Detected legacy subscription {subscription_id} for org {org.id}")

                # Log the action - use org owner's user_id since user_id cannot be NULL
                from agentops.opsboard.models import UserOrgModel, OrgRoles

                owner_membership = (
                    orm.query(UserOrgModel)
                    .filter(UserOrgModel.org_id == org.id, UserOrgModel.role == OrgRoles.owner)
                    .first()
                )
                system_user_id = owner_membership.user_id if owner_membership else None

                if not system_user_id:
                    logger.warning(f"No owner found for org {org.id}, cannot create audit log")
                else:
                    audit_log = BillingAuditLog(
                        org_id=org.id,
                        user_id=system_user_id,  # Use org owner's ID for system actions
                        action='legacy_subscription_sunset',
                        details={
                            'subscription_id': subscription_id,
                            'old_price_id': legacy_price_id or 'unknown',
                            'cancel_at': current_period_end,
                            'event_id': event.id,
                            'system_action': True,  # Flag to indicate this was a system action
                        },
                    )
                    orm.add(audit_log)

                # Send notification email
                await send_legacy_billing_notification(org, subscription, orm)

                # Cancel at period end and mark email as sent in single call
                stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True,
                    metadata={
                        'cancellation_reason': 'billing_model_change',
                        'notification_email_sent': 'sent',
                        'original_price_id': legacy_price_id or 'unknown',
                    },
                )

            except stripe.error.StripeError as e:
                logger.error(f"Failed to update legacy subscription: {e}")

        # Skip seat sync for legacy subscriptions
        skip_license_sync = True

    # Check if this is a legacy subscription being notified
    elif (
        subscription.get('cancel_at_period_end')
        and subscription.get('metadata', {}).get('cancellation_reason') == 'billing_model_change'
        and subscription.get('metadata', {}).get('notification_email_sent') == 'pending'
    ):
        # Send notification email if not already sent
        await send_legacy_billing_notification(org, subscription, orm)

        # Update metadata to mark email as sent
        try:
            stripe.Subscription.modify(
                subscription_id,
                metadata={
                    'cancellation_reason': 'billing_model_change',
                    'notification_email_sent': 'sent',
                    'original_price_id': subscription.get('metadata', {}).get('original_price_id', 'unknown'),
                },
            )
        except stripe.error.StripeError as e:
            logger.error(f"Failed to update subscription metadata: {e}")

    # Update org status based on subscription status
    if status == "active":
        org.prem_status = PremStatus.pro

        # Sync member licenses based on seat quantity (unless we just did a manual update or it's legacy)
        if seat_quantity > 0 and not skip_license_sync and not is_legacy_subscription:
            # If we want granular control over who gets licensed, we can add a flag to the org model
            # and only license the owner at checkout
            # Some orgs may prefer manual control over who gets licensed

            # Sync licenses
            sync_result = await sync_org_licenses(org, seat_quantity, orm, event.id)

            # Log the changes
            if sync_result['newly_licensed']:
                logger.info(
                    f"Licensed {len(sync_result['newly_licensed'])} members for org {org.id}: {sync_result['newly_licensed']}"
                )
            if sync_result['newly_unlicensed']:
                logger.info(
                    f"Unlicensed {len(sync_result['newly_unlicensed'])} members for org {org.id}: {sync_result['newly_unlicensed']}"
                )

            # Log metrics for monitoring
            log_webhook_metric(
                "subscription.updated",
                "licenses_synced",
                {
                    "org_id": str(org.id),
                    "seat_quantity": seat_quantity,
                    "total_members": sync_result['total_members'],
                    "newly_licensed": len(sync_result['newly_licensed']),
                    "newly_unlicensed": len(sync_result['newly_unlicensed']),
                },
            )

    elif status in ["past_due", "unpaid"]:
        # Check if we're past the 3-day grace period
        if current_period_end:
            period_end_date = datetime.fromtimestamp(current_period_end)
            grace_period_end = period_end_date + timedelta(days=3)

            if datetime.now() > grace_period_end:
                logger.warning(
                    f"Org {org.id} subscription is {status} and past 3-day grace period. Demoting to free."
                )
                org.prem_status = PremStatus.free
                org.subscription_id = None

                # Remove all licenses when demoting to free
                orm.query(UserOrgModel).filter(UserOrgModel.org_id == org.id).update(
                    {UserOrgModel.is_paid: False}
                )

            else:
                days_remaining = (grace_period_end - datetime.now()).days
                logger.warning(
                    f"Org {org.id} subscription is {status}. {days_remaining} days left in grace period."
                )
    elif status in ["canceled", "incomplete_expired"]:
        org.prem_status = PremStatus.free
        org.subscription_id = None

        # Remove all licenses when subscription is canceled
        orm.query(UserOrgModel).filter(UserOrgModel.org_id == org.id).update({UserOrgModel.is_paid: False})

        logger.info(f"Removed all licenses for org {org.id} due to subscription cancellation")

    try:
        orm.commit()
        await mark_event_processed(event.id, orm)
    except Exception as e:
        orm.rollback()
        logger.error(
            "BILLING_WEBHOOK_ERROR",
            extra={
                "event_type": event.type,
                "event_id": event.id,
                "org_id": str(org.id),
                "subscription_id": subscription_id,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "requires_manual_intervention": True,
            },
        )


async def handle_subscription_deleted(event, orm: Session):
    """Handle subscription cancellation/deletion."""
    subscription = event.data.object
    subscription_id = subscription.get("id")

    org: OrgModel = (
        orm.query(OrgModel).filter(OrgModel.subscription_id == subscription_id).with_for_update().first()
    )

    if not org:
        logger.warning(f"No org found with subscription_id: {subscription_id}")
        return

    # Check if this was a legacy subscription being sunset
    cancellation_reason = subscription.get('metadata', {}).get('cancellation_reason')

    if cancellation_reason == 'billing_model_change':
        # Log the legacy subscription cancellation - use org owner's user_id since user_id cannot be NULL
        from agentops.opsboard.models import UserOrgModel, OrgRoles

        owner_membership = (
            orm.query(UserOrgModel)
            .filter(UserOrgModel.org_id == org.id, UserOrgModel.role == OrgRoles.owner)
            .first()
        )
        system_user_id = owner_membership.user_id if owner_membership else None

        if system_user_id:
            audit_log = BillingAuditLog(
                org_id=org.id,
                user_id=system_user_id,  # Use org owner's ID for system actions
                action='legacy_subscription_cancelled',
                details={
                    'subscription_id': subscription_id,
                    'cancelled_at': datetime.now(timezone.utc).isoformat(),
                    'original_price_id': subscription.get('metadata', {}).get('original_price_id', 'unknown'),
                    'system_action': True,  # Flag to indicate this was a system action
                },
            )
            orm.add(audit_log)

        logger.info(f"Legacy subscription {subscription_id} cancelled for org {org.id}")

    org.prem_status = PremStatus.free
    org.subscription_id = None

    # Remove all licenses when subscription is deleted
    orm.query(UserOrgModel).filter(UserOrgModel.org_id == org.id).update({UserOrgModel.is_paid: False})
    logger.info(f"Removed all licenses for org {org.id} due to subscription deletion")

    try:
        orm.commit()
    except Exception as e:
        orm.rollback()
        logger.error(
            "BILLING_WEBHOOK_ERROR",
            extra={
                "event_type": event.type,
                "event_id": event.id,
                "org_id": str(org.id),
                "subscription_id": subscription_id,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "requires_manual_intervention": True,
            },
        )


async def handle_payment_failed(event, orm: Session):
    """Handle failed payment attempts."""
    invoice = event.data.object
    subscription_id = invoice.get("subscription")
    attempt_count = invoice.get("attempt_count", 0)

    org: OrgModel = orm.query(OrgModel).filter(OrgModel.subscription_id == subscription_id).first()

    if not org:
        logger.warning(f"No org found with subscription_id: {subscription_id}")
        log_webhook_metric(
            "invoice.payment_failed",
            "org_not_found",
            {"subscription_id": subscription_id, "attempt_count": attempt_count},
        )
        return

    logger.warning(f"Org {org.id} has failed payment, attempt #{attempt_count}")

    log_webhook_metric(
        "invoice.payment_failed",
        "payment_failure",
        {"org_id": str(org.id), "subscription_id": subscription_id, "attempt_count": attempt_count},
    )

    if attempt_count >= 3:
        logger.error(f"CRITICAL: Org {org.id} has {attempt_count} failed payment attempts")
        # Critical: multiple payment failures
        log_webhook_metric(
            "invoice.payment_failed",
            "critical_payment_failure",
            {
                "org_id": str(org.id),
                "subscription_id": subscription_id,
                "attempt_count": attempt_count,
                "severity": "critical",
            },
        )


async def handle_charge_refunded(event, orm: Session):
    """Handle refunded charges - immediately revoke access."""
    charge = event.data.object
    refunded = charge.get("refunded")
    amount_refunded = charge.get("amount_refunded", 0)

    if not refunded:
        return

    # Get the invoice associated with this charge
    invoice_id = charge.get("invoice")
    if not invoice_id:
        logger.warning(f"Refunded charge {charge.get('id')} has no associated invoice")
        return

    try:
        # Retrieve the invoice to get the subscription
        invoice = stripe.Invoice.retrieve(invoice_id)
        subscription_id = invoice.get("subscription")

        if not subscription_id:
            logger.warning(f"Invoice {invoice_id} has no associated subscription")
            return

        # Find the org with this subscription
        # Use SELECT FOR UPDATE to lock the row and prevent race conditions
        org: OrgModel = (
            orm.query(OrgModel).filter(OrgModel.subscription_id == subscription_id).with_for_update().first()
        )

        if not org:
            logger.warning(f"No org found with subscription_id: {subscription_id}")
            return

        # Check if it's a full refund
        if amount_refunded >= charge.get("amount"):
            logger.info(f"Full refund detected for org {org.id}. Revoking pro access.")
            org.prem_status = PremStatus.free
            org.subscription_id = None

            try:
                orm.commit()
            except Exception as e:
                orm.rollback()
                logger.error(
                    "BILLING_WEBHOOK_ERROR",
                    extra={
                        "event_type": event.type,
                        "event_id": event.id,
                        "org_id": str(org.id),
                        "subscription_id": subscription_id,
                        "charge_id": charge.get('id'),
                        "amount_refunded": amount_refunded,
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "requires_manual_intervention": True,
                    },
                )
        else:
            logger.info(f"Partial refund of {amount_refunded} cents for org {org.id}. No action taken.")

    except stripe.error.StripeError as e:
        logger.error(f"Stripe API error handling refund: {e}")
    except Exception as e:
        logger.error(f"Unexpected error handling refund: {e}")


async def handle_invoice_created(event, orm: Session):
    """Handle invoice creation - add usage-based charges."""
    if await is_event_processed(event.id, orm):
        logger.info(f"Event {event.id} already processed, skipping")
        return {"status": "already_processed"}

    invoice = event.data.object
    subscription_id = invoice.get("subscription")
    customer_id = invoice.get("customer")

    if not subscription_id:
        logger.debug(f"Invoice {invoice.get('id')} is not for a subscription, skipping usage charges")
        return

    org: OrgModel = orm.query(OrgModel).filter(OrgModel.subscription_id == subscription_id).first()

    if not org:
        logger.warning(f"No org found with subscription_id: {subscription_id}")
        return

    # Check if this is a legacy subscription being sunset
    # TODO: Remove after <31 days after migration was run goes here>
    try:
        subscription = stripe.Subscription.retrieve(subscription_id)
        if (
            subscription.get('cancel_at_period_end')
            and subscription.get('metadata', {}).get('cancellation_reason') == 'billing_model_change'
        ):
            logger.info(f"Skipping usage charges for sunset legacy subscription {subscription_id}")
            await mark_event_processed(event.id, orm)
            return
    except stripe.error.StripeError as e:
        logger.error(f"Error retrieving subscription {subscription_id}: {e}")

    period_start_timestamp = invoice.get("period_start")
    period_end_timestamp = invoice.get("period_end")

    if not period_start_timestamp or not period_end_timestamp:
        logger.error(f"Invoice {invoice.get('id')} missing period information")
        return

    period_start = datetime.fromtimestamp(period_start_timestamp)
    period_end = datetime.fromtimestamp(period_end_timestamp)

    # Skip creating billing periods for zero-duration periods (setup/proration invoices)
    if period_start == period_end:
        logger.info(f"Skipping billing period creation for zero-duration invoice {invoice.get('id')}")
        await mark_event_processed(event.id, orm)
        return

    try:
        usage_quantities = await billing_service.get_usage_for_period(
            orm, str(org.id), period_start, period_end
        )

        if not usage_quantities:
            logger.info(f"No usage found for org {org.id} in period {period_start} to {period_end}")
            await mark_event_processed(event.id, orm)
            return

        usage_costs = await billing_service.calculate_usage_costs(usage_quantities)

        for usage_type, cost_cents in usage_costs.items():
            if cost_cents > 0:
                quantity = usage_quantities.get(usage_type, 0)
                if usage_type == 'tokens':
                    description = f"API Tokens: {quantity:,} tokens"
                elif usage_type == 'spans':
                    description = f"Span Uploads: {quantity:,} spans"
                else:
                    description = f"{usage_type.title()}: {quantity:,}"

                try:
                    stripe.InvoiceItem.create(
                        customer=customer_id,
                        invoice=invoice.get("id"),
                        amount=cost_cents,
                        currency='usd',
                        description=description,
                    )

                    logger.info(
                        f"Added {usage_type} charge of {cost_cents} cents to invoice {invoice.get('id')}"
                    )

                except stripe.error.StripeError as e:
                    logger.error(f"Failed to add {usage_type} charge to invoice: {e}")
                    log_webhook_metric(
                        "invoice.created",
                        "add_item_error",
                        {
                            "org_id": str(org.id),
                            "invoice_id": invoice.get("id"),
                            "usage_type": usage_type,
                            "error": str(e),
                        },
                    )

        await billing_service.create_billing_period_snapshot(orm, org, period_start, period_end)

        await mark_event_processed(event.id, orm)

        log_webhook_metric(
            "invoice.created",
            "usage_charges_added",
            {
                "org_id": str(org.id),
                "invoice_id": invoice.get("id"),
                "usage_costs": usage_costs,
                "usage_quantities": usage_quantities,
            },
        )

    except Exception as e:
        logger.error(f"Error processing usage charges for invoice: {e}")
        log_webhook_metric(
            "invoice.created",
            "processing_error",
            {
                "org_id": str(org.id),
                "invoice_id": invoice.get("id"),
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )


async def handle_invoice_payment_succeeded(event, orm: Session):
    """Handle successful invoice payment - update billing period status."""
    if await is_event_processed(event.id, orm):
        logger.info(f"Event {event.id} already processed, skipping")
        return {"status": "already_processed"}

    invoice = event.data.object
    invoice_id = invoice.get("id")
    subscription_id = invoice.get("subscription")

    if not subscription_id:
        return

    org: OrgModel = orm.query(OrgModel).filter(OrgModel.subscription_id == subscription_id).first()

    if not org:
        logger.warning(f"No org found with subscription_id: {subscription_id}")
        return

    period_start_timestamp = invoice.get("period_start")
    if period_start_timestamp:
        period_start = datetime.fromtimestamp(period_start_timestamp)

        billing_period = (
            orm.query(BillingPeriod)
            .filter(BillingPeriod.org_id == org.id, BillingPeriod.period_start == period_start)
            .first()
        )

        if billing_period:
            billing_period.status = 'paid'
            billing_period.stripe_invoice_id = invoice_id
            billing_period.invoiced_at = datetime.now(timezone.utc)
            orm.commit()

            logger.info(f"Marked billing period as paid for org {org.id}, invoice {invoice_id}")
        else:
            logger.warning(f"No billing period found for org {org.id} with period_start {period_start}")

    await mark_event_processed(event.id, orm)

    log_webhook_metric(
        "invoice.payment_succeeded",
        "billing_period_paid",
        {"org_id": str(org.id), "invoice_id": invoice_id, "subscription_id": subscription_id},
    )


async def send_legacy_billing_notification(org: OrgModel, subscription: dict, orm: Session):
    """Send email notification about legacy billing sunset"""
    try:
        owner_member = (
            orm.query(UserOrgModel)
            .filter(UserOrgModel.org_id == org.id, UserOrgModel.role == OrgRoles.owner)
            .first()
        )

        if not owner_member or not owner_member.user_id:
            logger.warning(f"No owner found for org {org.id} - cannot send legacy billing notification")
            return

        from agentops.opsboard.models import UserModel

        owner = orm.query(UserModel).filter(UserModel.id == owner_member.user_id).first()

        if not owner or not owner.billing_email:
            logger.warning(f"No billing email found for owner of org {org.id}")
            return

        period_end = None
        if subscription.get('current_period_end'):
            period_end = datetime.fromtimestamp(subscription['current_period_end'], tz=timezone.utc)

        # TODO: Integrate with your email service
        # For now, just log that we would send an email
        # audit_log = BillingAuditLog(
        #     org_id=org.id,
        #     user_id=owner.id,
        #     action='legacy_billing_notification_sent',
        #     details={
        #         'email': owner.billing_email,
        #         'subscription_id': subscription.get('id'),
        #         'cancel_at_period_end': subscription.get('current_period_end'),
        #         'notification_type': 'billing_model_change',
        #     },
        # )
        # orm.add(audit_log)
        logger.info(
            f"LEGACY_BILLING_NOTIFICATION: Would send email to {owner.billing_email} "
            f"for org {org.name} (ID: {org.id}) "
            f"with cancellation date: {period_end.strftime('%B %d, %Y') if period_end else 'Unknown'}"
        )

        # Don't commit here - let the calling function handle the commit
        # to ensure all operations are atomic

    except Exception as e:
        logger.error(f"Failed to send legacy billing notification for org {org.id}: {e}")
