from typing import Optional, Dict
from fastapi import Request, Depends, HTTPException
import stripe
import pydantic
import logging
import time
from sqlalchemy import func
from enum import Enum
from pydantic import Field
import os

from agentops.common.orm import get_orm_session, Session
from agentops.api.environment import (
    STRIPE_SECRET_KEY,
    STRIPE_SUBSCRIPTION_PRICE_ID,
    STRIPE_TOKEN_PRICE_ID,
    STRIPE_SPAN_PRICE_ID,
)
from agentops.common.environment import APP_URL
from agentops.api.db.supabase_client import get_supabase
from ..models import (
    OrgModel,
    UserOrgModel,
    OrgInviteModel,
    OrgRoles,
    UserModel,
    PremStatus,
    AuthUserModel,
    BillingAuditLog,
)
from ..schemas import (
    OrgCreateSchema,
    OrgDetailResponse,
    OrgInviteDetailResponse,
    OrgInviteResponse,
    OrgInviteSchema,
    OrgMemberRemoveSchema,
    OrgMemberRoleSchema,
    OrgResponse,
    OrgUpdateSchema,
    StatusResponse,
    ValidateDiscountCodeBody,
    ValidateDiscountCodeResponse,
    CreateFreeSubscriptionResponse,
)

logger = logging.getLogger(__name__)


def _validate_and_set_stripe_key(function_name: str = "") -> bool:
    """Validate Stripe configuration and set API key with logging"""
    context = f" in {function_name}" if function_name else ""

    if not STRIPE_SECRET_KEY:
        logger.error(f"✗ STRIPE_SECRET_KEY not found{context} - Cannot initialize Stripe API")
        return False

    # Mask the key for logging
    masked_key = f"{STRIPE_SECRET_KEY[:8]}..." if len(STRIPE_SECRET_KEY) > 8 else STRIPE_SECRET_KEY
    logger.info(f"✓ Setting Stripe API key{context}: {masked_key}")

    try:
        stripe.api_key = STRIPE_SECRET_KEY
        return True
    except Exception as e:
        logger.error(f"✗ Failed to set Stripe API key{context}: {e}")
        return False


def _validate_stripe_price_ids(function_name: str = "") -> None:
    """Log status of all Stripe price IDs for debugging"""
    context = f" in {function_name}" if function_name else ""

    price_vars = {
        "STRIPE_SUBSCRIPTION_PRICE_ID": STRIPE_SUBSCRIPTION_PRICE_ID,
        "STRIPE_TOKEN_PRICE_ID": STRIPE_TOKEN_PRICE_ID,
        "STRIPE_SPAN_PRICE_ID": STRIPE_SPAN_PRICE_ID,
    }

    logger.info(f"=== Stripe Price ID Status{context} ===")
    found_count = 0
    for var_name, var_value in price_vars.items():
        if var_value:
            masked_value = f"{var_value[:12]}..." if len(var_value) > 12 else var_value
            logger.info(f"✓ {var_name}: {masked_value}")
            found_count += 1
        else:
            logger.warning(f"✗ {var_name}: NOT FOUND")

    logger.info(f"Price IDs configured: {found_count}/{len(price_vars)}")
    logger.info("=======================================")


def extract_subscription_period_dates(subscription: Dict) -> tuple[Optional[int], Optional[int]]:
    """
    Extract billing period dates from Stripe subscription object.
    Handles both standard subscriptions and 100% discounted subscriptions.

    Returns: (period_start_timestamp, period_end_timestamp)
    """
    # Try root level first
    period_start = subscription.get('current_period_start')
    period_end = subscription.get('current_period_end')

    # If not at root level, check subscription items (for 100% discount subscriptions)
    if not period_start or not period_end:
        items = subscription.get('items', {})
        if items and items.get('data') and len(items['data']) > 0:
            first_item = items['data'][0]
            period_start = first_item.get('current_period_start', period_start)
            period_end = first_item.get('current_period_end', period_end)

    return period_start, period_end


def update_org_subscription(
    orm: Session, org: OrgModel, subscription_id: str, mark_owner_paid: bool = True
) -> None:
    """Update organization with new subscription and mark all members as paid."""
    org.subscription_id = subscription_id
    org.prem_status = PremStatus.pro

    if mark_owner_paid:
        # Mark ALL members as paid since we're billing for the full organization
        updated_count = (
            orm.query(UserOrgModel)
            .filter(UserOrgModel.org_id == org.id)
            .update({UserOrgModel.is_paid: True}, synchronize_session=False)
        )

        logger.info(f"Marked {updated_count} members as paid for org {org.id} during subscription creation")


class BillingErrorCode(str, Enum):
    STRIPE_API_ERROR = "stripe_api_error"
    NO_SUBSCRIPTION = "no_subscription"
    OWNER_REQUIRED = "owner_license_required"
    PERMISSION_DENIED = "permission_denied"
    SUBSCRIPTION_CANCELLED = "subscription_cancelled"
    LEGACY_BILLING_PLAN = "legacy_billing_plan"


class CreateCheckoutSessionBody(pydantic.BaseModel):
    price_id: str
    discount_code: Optional[str] = None
    quantity: int = Field(default=1, ge=1, le=100)  # Add seat quantity with limits


class CreateCheckoutSessionResponse(pydantic.BaseModel):
    clientSecret: str


class CancelSubscriptionBody(pydantic.BaseModel):
    subscription_id: str


def get_user_orgs(
    *,
    request: Request,
    orm: Session = Depends(get_orm_session),
) -> list[OrgResponse]:
    """
    Get all organizations for the authenticated user.
    Returns a list of organizations with basic information, without member details.

    Optimized to avoid N+1 queries by using count subqueries instead of loading all relationships.
    """
    orgs: list[OrgModel] = OrgModel.get_all_for_user(orm, request.state.session.user_id)

    org_responses = []
    for org in orgs:
        org_response = OrgResponse.model_validate(org)

        if org.subscription_id and org.prem_status != PremStatus.free:
            try:
                if not _validate_and_set_stripe_key("get_user_orgs"):
                    logger.warning(
                        f"Skipping subscription retrieval for org {org.id} - Stripe not configured"
                    )
                    org_responses.append(org_response)
                    continue

                subscription = stripe.Subscription.retrieve(org.subscription_id)

                if subscription:
                    current_period_start, current_period_end = extract_subscription_period_dates(subscription)
                    cancel_at_period_end = subscription.get('cancel_at_period_end')

                    if current_period_start:
                        org_response.subscription_start_date = current_period_start
                    if current_period_end:
                        org_response.subscription_end_date = current_period_end
                    if cancel_at_period_end is not None:
                        org_response.subscription_cancel_at_period_end = cancel_at_period_end
            except Exception as e:
                logger.warning(
                    f"Could not fetch subscription details for org {org.id}: {type(e).__name__}: {e}"
                )

        org_responses.append(org_response)

    return org_responses


def get_org(
    *,
    request: Request,
    org_id: str,
    orm: Session = Depends(get_orm_session),
) -> OrgDetailResponse:
    """
    Get detailed information for a specific organization, including its members.

    Optimized to only load users (needed for response), not projects or invites.
    """
    org: Optional[OrgModel] = OrgModel.get_by_id_for_detail(orm, org_id)

    if not org or not org.is_user_member(request.state.session.user_id):
        raise HTTPException(status_code=404, detail="Organization not found")

    org.set_current_user(request.state.session.user_id)

    return OrgDetailResponse.model_validate(org)


def create_org(
    *,
    request: Request,
    orm: Session = Depends(get_orm_session),
    body: OrgCreateSchema,
) -> OrgResponse:
    """
    Create a new organization and add the authenticated user as owner.
    """
    if not (user := UserModel.get_by_id(orm, request.state.session.user_id)):
        raise HTTPException(status_code=500, detail="User not found")

    org: OrgModel = OrgModel(name=body.name)
    orm.add(org)
    orm.flush()  # generate the id

    # TODO user may not have an email address here
    # this displays in the UI for the user in the list of org members
    user_org: UserOrgModel = UserOrgModel(
        user_id=user.id,
        org_id=org.id,
        role=OrgRoles.owner,
        user_email=user.email,
        is_paid=True,  # Mark owner as paid from creation
    )
    orm.add(user_org)

    orm.commit()

    # Reload with relationships to ensure we have users loaded
    org = OrgModel.get_by_id(orm, org.id)

    org.set_current_user(request.state.session.user_id)
    return OrgResponse.model_validate(org)


def update_org(
    *,
    request: Request,
    org_id: str,
    orm: Session = Depends(get_orm_session),
    body: OrgUpdateSchema,
) -> OrgResponse:
    """
    Update an organization's name. User must be an owner or admin.
    Premium status and subscription management happens elsewhere.
    """
    org: Optional[OrgModel] = OrgModel.get_by_id_summary(orm, org_id, request.state.session.user_id)

    if not org or not org.is_user_admin_or_owner(request.state.session.user_id):
        raise HTTPException(status_code=404, detail="Organization not found")

    org.name = body.name  # this is the only field that can be updated

    orm.commit()

    # Return the updated org with summary data
    org = OrgModel.get_by_id_summary(orm, org_id, request.state.session.user_id)

    if not org:
        raise HTTPException(status_code=404, detail="Organization not found after update")

    return OrgResponse.model_validate(org)


def invite_to_org(
    *,
    request: Request,
    org_id: str,
    orm: Session = Depends(get_orm_session),
    body: OrgInviteSchema,
) -> StatusResponse:
    """Invite a user to an organization. User must be an owner or admin."""
    org: Optional[OrgModel] = OrgModel.get_by_id(orm, org_id)

    if not org or not org.is_user_admin_or_owner(request.state.session.user_id):
        raise HTTPException(status_code=404, detail="Organization not found")

    # Normalize email to lowercase for case-insensitive comparison
    normalized_email = body.email.lower()

    is_already_member = any(
        user_org.user_email.lower() == normalized_email for user_org in org.users if user_org.user_email
    )
    if is_already_member:
        raise HTTPException(status_code=400, detail="User is already a member of this organization")

    # Check member limit
    if org.max_member_count and not org.current_member_count < org.max_member_count:
        raise HTTPException(status_code=400, detail="Organization has reached its member limit")

    # Get the inviter's email (current user)
    inviter_user = UserModel.get_by_id(orm, request.state.session.user_id)
    if not inviter_user or not inviter_user.billing_email:
        raise HTTPException(status_code=500, detail="Unable to determine inviter email")

    existing_invite = (
        orm.query(OrgInviteModel)
        .filter(func.lower(OrgInviteModel.invitee_email) == normalized_email, OrgInviteModel.org_id == org_id)
        .first()
    )
    if existing_invite:
        raise HTTPException(status_code=400, detail="User already has a pending invitation")

    invite = OrgInviteModel(
        inviter_id=request.state.session.user_id,
        invitee_email=normalized_email,
        org_id=org_id,
        role=body.role,
        org_name=org.name,
    )
    orm.add(invite)
    orm.commit()

    logger.debug("Created org_invites record for %s", body.email)

    # Send email notification (handles both existing and new users)
    email_sent = False
    email_error = None
    try:
        _send_invitation_email(
            invitee_email=body.email,
            inviter_email=inviter_user.billing_email,
            org_name=org.name,
            role=body.role,
            org_id=org_id,
            orm=orm,
        )
        email_sent = True
    except Exception as e:
        # Don't fail the whole invitation if email fails, but log it
        email_error = str(e)
        logger.error("Failed to send invitation email to %s: %s", body.email, e)

    # Return appropriate message based on what happened
    if email_sent:
        return StatusResponse(message="Invitation sent successfully")
    elif "already been registered" in str(email_error):
        return StatusResponse(
            message=(
                "Invitation created. The user already has an account - "
                "they can accept the invitation from their pending invites."
            )
        )
    else:
        return StatusResponse(
            message=(
                "Invitation created but email could not be sent. "
                "The user can still accept from their pending invites."
            )
        )


def _send_invitation_email(
    invitee_email: str, inviter_email: str, org_name: str, role: str, org_id: str, orm: Session
) -> None:
    """Send invitation email using standard OTP flow."""
    try:
        logger.debug("Sending invitation email to %s", invitee_email)

        supabase = get_supabase()

        # Use the dashboard URL for the redirect, not the API URL
        # This ensures users land on the frontend auth callback page
        # Note: Supabase strips query parameters from redirect URLs, so we rely on the 'data' field
        redirect_url = f"{APP_URL}/auth/callback"
        logger.debug("Magic link redirect URL: %s", redirect_url)
        logger.debug("Invite data will be passed in JWT: org_id=%s", org_id)

        auth_response = supabase.auth.sign_in_with_otp(
            {
                'email': invitee_email,
                'options': {
                    'should_create_user': True,
                    'email_redirect_to': redirect_url,
                    'data': {
                        'invited_to_org': org_id,
                        'invited_by': inviter_email,
                        'org_name': org_name,
                        'role': role,
                    },
                },
            }
        )

        if hasattr(auth_response, 'error') or auth_response is None:
            logger.error("Failed to send OTP: %s", getattr(auth_response, 'error', 'Unknown error'))
            return

        logger.debug("Magic link sent successfully to %s", invitee_email)

    except Exception as e:
        logger.error("Error sending invitation email: %s: %s", type(e).__name__, e)


def get_org_invites(
    *,
    request: Request,
    orm: Session = Depends(get_orm_session),
) -> list[OrgInviteResponse]:
    """Get all pending invitations for the authenticated user."""
    user = UserModel.get_by_id(orm, request.state.session.user_id)
    if not user:
        return []

    invites = []

    # Try both billing_email and regular email
    for email_field in [user.billing_email, user.email]:
        if email_field:
            found_invites = (
                orm.query(OrgInviteModel)
                .filter(func.lower(OrgInviteModel.invitee_email) == email_field.lower())
                .all()
            )
            invites.extend(found_invites)

    # Remove duplicates (in case both emails found the same invite)
    seen_invite_ids = set()
    unique_invites = []
    for invite in invites:
        invite_key = (invite.org_id, invite.invitee_email.lower())
        if invite_key not in seen_invite_ids:
            seen_invite_ids.add(invite_key)
            unique_invites.append(invite)

    return [OrgInviteResponse.model_validate(invite) for invite in unique_invites]


def accept_org_invite(
    *,
    request: Request,
    org_id: str,
    orm: Session = Depends(get_orm_session),
) -> StatusResponse:
    """Accept an invitation to join an organization."""
    logger.info(f"accept_org_invite: Started for user_id={request.state.session.user_id}, org_id={org_id}")

    user = UserModel.get_by_id(orm, request.state.session.user_id)

    # For new users, the trigger might not have created the public.users record yet
    # In this case, we need to get the email directly from auth.users
    email_to_check = None

    if not user:
        logger.warning(
            f"accept_org_invite: User not found in public.users for ID: {request.state.session.user_id}"
        )
        print(f"accept_org_invite: User not found in public.users for ID: {request.state.session.user_id}")
        # Try to get email from auth.users directly
        auth_user = orm.query(AuthUserModel).filter(AuthUserModel.id == request.state.session.user_id).first()
        if auth_user and auth_user.email:
            logger.info(f"accept_org_invite: Found user in auth.users with email: {auth_user.email}")
            print(f"accept_org_invite: Found user in auth.users with email: {auth_user.email}")
            email_to_check = auth_user.email
        else:
            logger.error(
                f"accept_org_invite: User not found in auth.users either for ID: {request.state.session.user_id}"
            )
            print(
                f"accept_org_invite: ERROR - User not found in auth.users either for ID: {request.state.session.user_id}"
            )
            raise HTTPException(status_code=404, detail="User not found")
    else:
        logger.info(
            f"accept_org_invite: Found user {user.id} with email={user.email}, billing_email={user.billing_email}"
        )
        print(f"accept_org_invite: Accepting invite for user {user.id}, org {org_id}")
        print(f"accept_org_invite: User email: {user.email}, billing_email: {user.billing_email}")

        # Also check if auth_user is loaded
        if user.auth_user:
            logger.debug(
                f"accept_org_invite: Auth user loaded, email from auth.users: {user.auth_user.email}"
            )
            print(f"accept_org_invite: Auth user loaded, email from auth.users: {user.auth_user.email}")
        else:
            logger.warning("accept_org_invite: Auth user NOT loaded - this might be the issue!")
            print("accept_org_invite: Auth user NOT loaded - this might be the issue!")

    # Log all invites for debugging
    all_invites = orm.query(OrgInviteModel).filter(OrgInviteModel.org_id == org_id).all()
    logger.debug(f"accept_org_invite: Found {len(all_invites)} invites for org {org_id}")
    print(
        f"accept_org_invite: All invites for org {org_id}: {[(inv.invitee_email, inv.inviter_id) for inv in all_invites]}"
    )

    invite = None

    # If we have a direct email from auth.users (new user case), use that
    if email_to_check:
        print(f"accept_org_invite: Looking for invite with email from auth.users: {email_to_check}")
        invite = (
            orm.query(OrgInviteModel)
            .filter(
                func.lower(OrgInviteModel.invitee_email) == email_to_check.lower(),
                OrgInviteModel.org_id == org_id,
            )
            .first()
        )
        if invite:
            print(f"accept_org_invite: Found invite for email: {email_to_check}")
    else:
        # Normal case - user exists in public.users
        # Try both billing_email and regular email
        for email_field in [user.billing_email, user.email]:
            if email_field:
                print(f"accept_org_invite: Looking for invite with email: {email_field}")
                invite = (
                    orm.query(OrgInviteModel)
                    .filter(
                        func.lower(OrgInviteModel.invitee_email) == email_field.lower(),
                        OrgInviteModel.org_id == org_id,
                    )
                    .first()
                )
                if invite:
                    print(f"accept_org_invite: Found invite for email: {email_field}")
                    break
                else:
                    print(f"accept_org_invite: No invite found with email: {email_field}")

    if not invite:
        if user:
            print(f"accept_org_invite: ERROR - No invitation found for user {user.id} in org {org_id}")
            print(
                f"accept_org_invite: ERROR - Checked emails: billing_email={user.billing_email}, email={user.email}"
            )
        else:
            print(
                f"accept_org_invite: ERROR - No invitation found for auth email {email_to_check} in org {org_id}"
            )
        raise HTTPException(status_code=404, detail="Invitation not found")

    # For new users, we need to wait for the trigger to create the user record
    # before we can add them to the org
    if not user:
        # Wait a moment for the trigger to complete
        import time

        max_retries = 5
        for i in range(max_retries):
            time.sleep(0.5)  # Wait 500ms
            user = UserModel.get_by_id(orm, request.state.session.user_id)
            if user:
                print(f"accept_org_invite: User record found after {i + 1} retries")
                break

        if not user:
            print("accept_org_invite: ERROR - User record still not created after waiting")
            raise HTTPException(
                status_code=500, detail="User record not yet created. Please try again in a moment."
            )

    # Check if already a member (safety check)
    existing_member = (
        orm.query(UserOrgModel).filter(UserOrgModel.user_id == user.id, UserOrgModel.org_id == org_id).first()
    )

    new_member_added = False
    user_org = None
    if not existing_member:
        # Create user-org relationship
        user_org = UserOrgModel(
            user_id=user.id,
            org_id=org_id,
            role=invite.role,
            user_email=user.billing_email or user.email or email_to_check,
            is_paid=True,  # Mark all new members as paid by default
        )
        orm.add(user_org)
        new_member_added = True

    # Always delete the invite
    print(
        f"accept_org_invite: Deleting invite record: inviter_id={invite.inviter_id}, invitee_email={invite.invitee_email}, org_id={invite.org_id}"
    )
    orm.delete(invite)

    # If a new member was added and the org has a subscription, update the seat count
    if new_member_added:
        org = orm.query(OrgModel).filter(OrgModel.id == org_id).first()
        if org and org.subscription_id and org.prem_status == PremStatus.pro:
            try:
                # Get the current user count (actual members, not invites) for billing
                new_seat_count = orm.query(UserOrgModel).filter(UserOrgModel.org_id == org_id).count()

                # Update Stripe subscription
                import stripe
                from agentops.api.environment import STRIPE_SECRET_KEY

                stripe.api_key = STRIPE_SECRET_KEY

                subscription = stripe.Subscription.retrieve(
                    org.subscription_id, expand=["items.data.price.product"]
                )

                # Find the seat item
                seat_item = None
                for item in subscription.get('items', {}).get('data', []):
                    price = item.get('price', {})
                    if price.get('id') == STRIPE_SUBSCRIPTION_PRICE_ID:
                        seat_item = item
                        break

                if seat_item and new_seat_count > 0:
                    stripe.Subscription.modify(
                        org.subscription_id,
                        items=[
                            {
                                'id': seat_item.get('id'),
                                'quantity': new_seat_count,
                            }
                        ],
                        proration_behavior='create_prorations',
                    )
                    print(
                        f"accept_org_invite: Updated subscription to {new_seat_count} seats for org {org_id}"
                    )

                    # Add audit log
                    from agentops.opsboard.models import BillingAuditLog

                    audit_log = BillingAuditLog(
                        org_id=org_id,
                        user_id=user.id,
                        action='member_auto_licensed_on_invite_accept',
                        details={
                            'member_id': str(user.id),
                            'member_email': user.billing_email or user.email or email_to_check,
                            'new_seat_count': new_seat_count,
                            'invite_role': invite.role.value,
                        },
                    )
                    orm.add(audit_log)

            except Exception as e:
                print(f"accept_org_invite: Warning - failed to update subscription: {e}")
                # Don't fail the invite acceptance if subscription update fails
                logger.warning(
                    f"Failed to auto-update subscription for org {org_id} when user {user.id} joined: {e}"
                )

    orm.commit()
    print("accept_org_invite: Invite deleted and committed")

    return StatusResponse(message="Organization invitation accepted")


def remove_from_org(
    *,
    request: Request,
    org_id: str,
    orm: Session = Depends(get_orm_session),
    body: OrgMemberRemoveSchema,
) -> StatusResponse:
    """
    Remove a user from an organization. User must be an owner or admin.
    Automatically updates Stripe subscription if a paid member is removed.
    """
    # admins can only remove non-owners
    # owners can remove anyone except the last owner
    org: Optional[OrgModel] = OrgModel.get_by_id(orm, org_id)

    if not org or not org.is_user_admin_or_owner(request.state.session.user_id):
        raise HTTPException(status_code=404, detail="Organization not found")

    user_to_remove = (
        orm.query(UserOrgModel)
        .filter(
            UserOrgModel.user_id == body.user_id,
            UserOrgModel.org_id == org_id,
            UserOrgModel.role != OrgRoles.owner,
            UserOrgModel.user_id != request.state.session.user_id,  # can't remove yourself
        )
        .first()
    )

    if not user_to_remove:
        raise HTTPException(status_code=400, detail="User cannot be removed")

    # Remove the user from the organization
    orm.delete(user_to_remove)

    # If the org has a subscription, update Stripe (since we bill for all members)
    if org.subscription_id and org.prem_status == PremStatus.pro:
        try:
            # Get the new user count after removal (actual members, not invites) for billing
            new_seat_count = orm.query(UserOrgModel).filter(UserOrgModel.org_id == org_id).count()

            # Update Stripe subscription
            import stripe
            from agentops.api.environment import STRIPE_SECRET_KEY

            stripe.api_key = STRIPE_SECRET_KEY

            subscription = stripe.Subscription.retrieve(
                org.subscription_id, expand=["items.data.price.product"]
            )

            # Find the seat item
            seat_item = None
            for item in subscription.get('items', {}).get('data', []):
                price = item.get('price', {})
                if price.get('id') == STRIPE_SUBSCRIPTION_PRICE_ID:
                    seat_item = item
                    break

            if seat_item:
                stripe.Subscription.modify(
                    org.subscription_id,
                    items=[
                        {
                            'id': seat_item.get('id'),
                            'quantity': max(1, new_seat_count),  # Ensure at least 1 seat
                        }
                    ],
                    proration_behavior='create_prorations',
                )
                logger.info(
                    f"remove_from_org: Updated subscription to {max(1, new_seat_count)} seats for org {org_id}"
                )

                # Add audit log
                from agentops.opsboard.models import BillingAuditLog

                audit_log = BillingAuditLog(
                    org_id=org_id,
                    user_id=request.state.session.user_id,
                    action='member_unlicensed_on_removal',
                    details={
                        'removed_member_id': str(user_to_remove.user_id),
                        'removed_member_email': user_to_remove.user_email or 'Unknown',
                        'new_seat_count': max(1, new_seat_count),
                        'removed_by': str(request.state.session.user_id),
                    },
                )
                orm.add(audit_log)

        except Exception as e:
            logger.warning(f"remove_from_org: Failed to update subscription for org {org_id}: {e}")
            # Don't fail the member removal if subscription update fails

    orm.commit()

    return StatusResponse(message="User removed from organization")


def change_member_role(
    *,
    request: Request,
    org_id: str,
    orm: Session = Depends(get_orm_session),
    body: OrgMemberRoleSchema,
) -> StatusResponse:
    """
    Change a user's role within an organization. Authenticate user must be an owner or admin.
    """
    org: Optional[OrgModel] = OrgModel.get_by_id(orm, org_id)

    if not org or not org.is_user_admin_or_owner(request.state.session.user_id):
        raise HTTPException(status_code=404, detail="Organization not found")

    # Get the role we're changing
    update_record: Optional[UserOrgModel] = (
        orm.query(UserOrgModel)
        .filter(UserOrgModel.user_id == body.user_id)
        .filter(UserOrgModel.org_id == org_id)
        .first()
    )

    if not update_record:
        raise HTTPException(status_code=404, detail="User not found in organization")

    # if we're changing to owner, make sure we are an owner
    if body.role == OrgRoles.owner.value and not org.is_user_owner(request.state.session.user_id):
        raise HTTPException(status_code=400, detail="Only owners can assign the owner role")

    # If we're changing from owner to another role, check if it's the last owner
    # TODO this can be simplified
    if update_record.role == OrgRoles.owner and body.role != OrgRoles.owner.value:
        owner_count = (
            orm.query(UserOrgModel)
            .filter(UserOrgModel.org_id == org_id)
            .filter(UserOrgModel.role == OrgRoles.owner)
            .count()
        )

        if owner_count <= 1:
            raise HTTPException(status_code=400, detail="Cannot remove the last owner")

    update_record.role = OrgRoles(body.role)
    orm.commit()

    return StatusResponse(message="User role updated")


def delete_org(
    *,
    request: Request,
    org_id: str,
    orm: Session = Depends(get_orm_session),
) -> StatusResponse:
    """
    Delete an organization. User must be the owner.
    Organization cannot be deleted if it still contains projects.
    """
    org: Optional[OrgModel] = OrgModel.get_by_id(orm, org_id)

    if not org or not org.is_user_owner(request.state.session.user_id):
        raise HTTPException(status_code=403, detail="Organization cannot be deleted")

    if org.projects:
        raise HTTPException(
            status_code=400,
            detail="Organization cannot be deleted while it still contains projects",
        )

    orm.delete(org)
    orm.commit()

    return StatusResponse(message="Organization deleted")


class UpdateMemberLicensesBody(pydantic.BaseModel):
    add: list[str] = Field(default_factory=list)
    remove: list[str] = Field(default_factory=list)


class UpdateMemberLicensesResponse(pydantic.BaseModel):
    message: str
    paid_members_count: int


async def update_member_licenses(
    *,
    request: Request,
    org_id: str,
    body: UpdateMemberLicensesBody,
    orm: Session = Depends(get_orm_session),
) -> UpdateMemberLicensesResponse:
    """Update which members are included in paid seats. Automatically updates Stripe subscription."""
    stripe.api_key = STRIPE_SECRET_KEY
    user: Optional[UserModel] = UserModel.get_by_id(orm, request.state.session.user_id)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not authenticated.",
            headers={"X-Error-Code": BillingErrorCode.PERMISSION_DENIED},
        )

    org: Optional[OrgModel] = OrgModel.get_by_id(orm, org_id)
    if not org or not org.is_user_admin_or_owner(request.state.session.user_id):
        raise HTTPException(
            status_code=403,
            detail="Permission denied. Only owners and admins can manage licenses.",
            headers={"X-Error-Code": BillingErrorCode.PERMISSION_DENIED},
        )

    if not org.subscription_id:
        raise HTTPException(
            status_code=400,
            detail="Organization does not have an active subscription.",
            headers={"X-Error-Code": BillingErrorCode.NO_SUBSCRIPTION},
        )

    # Check if this is a legacy subscription
    try:
        subscription = stripe.Subscription.retrieve(org.subscription_id)

        # Check if subscription is scheduled to cancel
        if subscription.get('cancel_at_period_end'):
            raise HTTPException(
                status_code=400,
                detail="Your subscription is scheduled to cancel. Seat management is not available for cancelled subscriptions.",
                headers={"X-Error-Code": BillingErrorCode.SUBSCRIPTION_CANCELLED},
            )

        # Check if using current price ID
        is_current_pricing = False
        for item in subscription.get('items', {}).get('data', []):
            if item.get('price', {}).get('id') == STRIPE_SUBSCRIPTION_PRICE_ID:
                is_current_pricing = True
                break

        if not is_current_pricing:
            raise HTTPException(
                status_code=400,
                detail="Your organization is on a legacy billing plan. Seat management is not available for legacy plans. Your subscription will automatically cancel at the end of the current billing period.",
                headers={"X-Error-Code": BillingErrorCode.LEGACY_BILLING_PLAN},
            )
    except stripe.error.StripeError as e:
        logger.error(f"Failed to retrieve subscription for legacy check: {e}")
        # Continue anyway - don't block the operation if we can't check

    if body.remove:
        owner_ids = (
            orm.query(UserOrgModel.user_id)
            .filter(
                UserOrgModel.user_id.in_(body.remove),
                UserOrgModel.org_id == org_id,
                UserOrgModel.role == OrgRoles.owner,
            )
            .all()
        )

        if owner_ids:
            raise HTTPException(
                status_code=400,
                detail="Cannot remove license from organization owner",
                headers={"X-Error-Code": BillingErrorCode.OWNER_REQUIRED},
            )

    # The main transaction is handled by the lifespan manager, so we don't need a nested transaction.
    # We lock the organization row to prevent race conditions.
    org = orm.query(OrgModel).filter(OrgModel.id == org_id).with_for_update().first()

    # Calculate final_paid based on the effective state after changes, BEFORE updating the db.
    all_member_ids = {
        str(uid) for (uid,) in orm.query(UserOrgModel.user_id).filter(UserOrgModel.org_id == org_id)
    }
    paid_member_ids = {
        str(uid)
        for (uid,) in orm.query(UserOrgModel.user_id).filter(
            UserOrgModel.org_id == org_id, UserOrgModel.is_paid
        )
    }

    # Apply changes to our in-memory set to calculate the final state
    paid_member_ids.update(body.add)
    paid_member_ids.difference_update(body.remove)

    # Ensure all licensed members are actual members of the org
    final_paid_ids = paid_member_ids.intersection(all_member_ids)
    final_paid = len(final_paid_ids)

    members_to_add = []
    members_to_remove = []

    if body.add:
        members_to_add = (
            orm.query(UserOrgModel)
            .filter(UserOrgModel.user_id.in_(body.add), UserOrgModel.org_id == org_id)
            .all()
        )

        orm.query(UserOrgModel).filter(
            UserOrgModel.user_id.in_(body.add), UserOrgModel.org_id == org_id
        ).update({UserOrgModel.is_paid: True}, synchronize_session=False)

    if body.remove:
        members_to_remove = (
            orm.query(UserOrgModel)
            .filter(UserOrgModel.user_id.in_(body.remove), UserOrgModel.org_id == org_id)
            .all()
        )

        orm.query(UserOrgModel).filter(
            UserOrgModel.user_id.in_(body.remove), UserOrgModel.org_id == org_id
        ).update({UserOrgModel.is_paid: False}, synchronize_session=False)

    try:
        subscription = stripe.Subscription.retrieve(org.subscription_id, expand=["items.data.price.product"])

        # Find the specific subscription item for licensed seats
        seat_item = None
        for item in subscription.get('items', {}).get('data', []):
            price = item.get('price', {})
            if price.get('id') == os.getenv("STRIPE_SUBSCRIPTION_PRICE_ID"):
                seat_item = item
                break

        if not seat_item:
            raise HTTPException(
                status_code=500,
                detail="Could not find subscription item for seat pricing. Please contact support.",
                headers={"X-Error-Code": BillingErrorCode.STRIPE_API_ERROR},
            )

        stripe.Subscription.modify(
            org.subscription_id,
            items=[
                {
                    'id': seat_item.get('id'),
                    'quantity': final_paid,
                }
            ],
            proration_behavior='create_prorations',
        )

    except stripe.error.StripeError as e:
        # Since we are in a transaction, raising an exception will trigger a rollback.
        logger.error(f"Stripe error updating subscription for org {org_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to update subscription. Please try again.",
            headers={"X-Error-Code": BillingErrorCode.STRIPE_API_ERROR},
        )

    # Create audit logs
    for member in members_to_add:
        audit_log = BillingAuditLog(
            org_id=org_id,
            user_id=user.id,
            action='member_licensed',
            details={
                'member_id': str(member.user_id),
                'member_email': member.user_email if member.user_email else 'Unknown',
                'updated_by': user.email,
            },
        )
        orm.add(audit_log)

    for member in members_to_remove:
        audit_log = BillingAuditLog(
            org_id=org_id,
            user_id=user.id,
            action='member_unlicensed',
            details={
                'member_id': str(member.user_id),
                'member_email': member.user_email if member.user_email else 'Unknown',
                'updated_by': user.email,
            },
        )
        orm.add(audit_log)

    orm.flush()  # We can flush to ensure audit logs are written before the transaction commits.
    orm.commit()  # Commit the transaction to persist all changes

    logger.info(
        f"Member licenses updated for org {org_id} by user {user.email}: "
        f"added {len(members_to_add)}, removed {len(members_to_remove)}"
    )

    return UpdateMemberLicensesResponse(
        message="Successfully updated member licenses", paid_members_count=final_paid
    )


async def _resolve_discount_code(discount_code: str) -> tuple[Optional[object], Optional[str]]:
    """
    Helper function to resolve a discount code string to either a promotion code or coupon.
    Returns (coupon, promotion_code_id) where one will be None.
    """
    # Try as promotion code first (most common)
    try:
        promotion_codes = stripe.PromotionCode.list(code=discount_code, active=True, limit=1)
        if promotion_codes.data:
            promo_code = promotion_codes.data[0]
            return promo_code.coupon, promo_code.id
    except Exception:
        pass

    # Try as coupon ID
    try:
        coupon = stripe.Coupon.retrieve(discount_code)
        if coupon and coupon.valid:
            return coupon, None
    except Exception:
        pass

    return None, None


async def validate_discount_code(
    *,
    request: Request,
    org_id: str,
    body: ValidateDiscountCodeBody,
    orm: Session = Depends(get_orm_session),
) -> ValidateDiscountCodeResponse:
    """
    Validate a discount code (promotion code or coupon ID) before checkout.
    Returns discount details if valid.
    """
    stripe.api_key = STRIPE_SECRET_KEY

    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe secret key not configured.")

    # Verify user has permission
    org: Optional[OrgModel] = OrgModel.get_by_id(orm, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    if not org.is_user_admin_or_owner(request.state.session.user_id):
        raise HTTPException(
            status_code=403, detail="User does not have permission to manage this organization."
        )

    # Try as promotion code first (most common)
    try:
        promotion_codes = stripe.PromotionCode.list(code=body.discount_code, active=True, limit=1)
        if promotion_codes.data:
            promo_code = promotion_codes.data[0]
            coupon = promo_code.coupon

            # Build discount description
            if coupon.percent_off:
                discount_description = f"{coupon.percent_off}% off"
                discount_type = "percent_off"
                discount_value = coupon.percent_off
                currency = None
            else:
                # For amount_off, we need to handle currency
                amount_in_dollars = coupon.amount_off / 100  # Convert cents to dollars
                currency_symbol = "$" if coupon.currency.upper() == "USD" else coupon.currency.upper()
                discount_description = f"{currency_symbol}{amount_in_dollars:.2f} off"
                discount_type = "amount_off"
                discount_value = coupon.amount_off
                currency = coupon.currency.upper()

            # Add duration info to description
            if coupon.duration == "once":
                discount_description += " for the first month"
            elif coupon.duration == "repeating":
                discount_description += f" for {coupon.duration_in_months} months"
            elif coupon.duration == "forever":
                discount_description += " forever"

            return ValidateDiscountCodeResponse(
                valid=True,
                discount_type=discount_type,
                discount_value=discount_value,
                discount_description=discount_description,
                currency=currency,
                is_100_percent_off=(coupon.percent_off == 100),
            )
    except Exception as e:
        logger.debug(f"Not a valid promotion code: {str(e)}")

    # Try as coupon ID
    try:
        coupon = stripe.Coupon.retrieve(body.discount_code)
        if coupon and coupon.valid:
            # Build discount description
            if coupon.percent_off:
                discount_description = f"{coupon.percent_off}% off"
                discount_type = "percent_off"
                discount_value = coupon.percent_off
                currency = None
            else:
                # For amount_off, we need to handle currency
                amount_in_dollars = coupon.amount_off / 100  # Convert cents to dollars
                currency_symbol = "$" if coupon.currency.upper() == "USD" else coupon.currency.upper()
                discount_description = f"{currency_symbol}{amount_in_dollars:.2f} off"
                discount_type = "amount_off"
                discount_value = coupon.amount_off
                currency = coupon.currency.upper()

            # Add duration info to description
            if coupon.duration == "once":
                discount_description += " for the first month"
            elif coupon.duration == "repeating":
                discount_description += f" for {coupon.duration_in_months} months"
            elif coupon.duration == "forever":
                discount_description += " forever"

            return ValidateDiscountCodeResponse(
                valid=True,
                discount_type=discount_type,
                discount_value=discount_value,
                discount_description=discount_description,
                currency=currency,
                is_100_percent_off=(coupon.percent_off == 100),
            )
    except Exception as e:
        logger.debug(f"Not a valid coupon ID: {str(e)}")

    # Neither worked, return invalid
    return ValidateDiscountCodeResponse(valid=False)


async def create_checkout_session(
    *,
    request: Request,
    org_id: str,
    body: CreateCheckoutSessionBody,
    orm: Session = Depends(get_orm_session),
) -> CreateCheckoutSessionResponse:
    """
    Create a Stripe Checkout Session for an organization to upgrade their plan.
    Optionally supports promotion codes or coupon IDs for discounts.
    """
    stripe.api_key = STRIPE_SECRET_KEY

    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe secret key not configured.")

    user: Optional[UserModel] = UserModel.get_by_id(orm, request.state.session.user_id)
    if not user or not user.billing_email:
        raise HTTPException(status_code=400, detail="User email is required to create a checkout session.")

    org: Optional[OrgModel] = OrgModel.get_by_id(orm, org_id)

    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    if not org.is_user_admin_or_owner(request.state.session.user_id):
        raise HTTPException(
            status_code=403, detail="User does not have permission to upgrade this organization."
        )

    # Validate org.id is not None or empty
    if not org.id:
        logger.error(f"Organization {org_id} has no id attribute")
        raise HTTPException(status_code=500, detail="Organization data is invalid")

    legacy_subscription_end = None  # Track when legacy subscription ends

    if org.subscription_id and org.prem_status != PremStatus.free:
        try:
            subscription = stripe.Subscription.retrieve(org.subscription_id)
            if subscription.status in ['active', 'trialing']:
                # Check if it's a legacy subscription scheduled to cancel
                if subscription.get('cancel_at_period_end'):
                    # Check if it's a legacy subscription by price ID
                    is_legacy = True
                    for item in subscription.get('items', {}).get('data', []):
                        if item.get('price', {}).get('id') == STRIPE_SUBSCRIPTION_PRICE_ID:
                            is_legacy = False
                            break

                    if not is_legacy:
                        # Non-legacy subscription cancelling - don't allow new subscription
                        raise HTTPException(
                            status_code=400,
                            detail="Your current subscription is scheduled to end. Please wait until it expires to resubscribe.",
                        )
                    # For legacy subscriptions, we'll schedule the new one to start when old ends
                    legacy_subscription_end = subscription.get('current_period_end')
                else:
                    # Active subscription not scheduled to cancel
                    raise HTTPException(
                        status_code=400, detail="Organization already has an active subscription"
                    )
        except stripe.error.StripeError:
            # If we can't retrieve the subscription, continue with checkout
            # This handles cases where the subscription_id is invalid/deleted
            logger.warning(f"Could not retrieve subscription {org.subscription_id} for org {org.id}")
            pass

    try:
        price = stripe.Price.retrieve(body.price_id)
        if (
            hasattr(price, 'recurring')
            and hasattr(price.recurring, 'usage_type')
            and price.recurring.usage_type != 'licensed'
        ):
            logger.error(f"Price {body.price_id} is not configured for licensed usage")
            raise HTTPException(status_code=400, detail="Invalid price configuration")
    except stripe.error.StripeError as e:
        logger.error(f"Failed to retrieve price: {e}")
        raise HTTPException(status_code=500, detail="Failed to validate pricing")

    try:
        session_params = {
            'ui_mode': 'custom',
            'customer_email': user.billing_email,
            'payment_method_types': ['card'],
            'mode': 'subscription',
            'line_items': [
                {
                    'price': body.price_id,
                    'quantity': body.quantity,
                }
            ],
            'client_reference_id': str(org.id),
            'return_url': (
                f"{APP_URL}/settings/organization?org_id={org_id}&checkout_status={{CHECKOUT_SESSION_STATUS}}"
            ),
            'metadata': {'initial_seats': str(body.quantity), 'org_id': str(org.id)},
        }

        if body.discount_code:
            # First try as promotion code
            try:
                promotion_codes = stripe.PromotionCode.list(code=body.discount_code, active=True, limit=1)
                if promotion_codes.data:
                    # It's a valid promotion code, use the ID
                    session_params['discounts'] = [{'promotion_code': promotion_codes.data[0].id}]
                else:
                    # Not a promotion code, try as coupon ID
                    coupon = stripe.Coupon.retrieve(body.discount_code)
                    if coupon and coupon.valid:
                        session_params['discounts'] = [{'coupon': body.discount_code}]
                    else:
                        raise HTTPException(status_code=400, detail="Invalid discount code")
            except stripe.error.StripeError:
                # Not a promotion code, try as coupon ID
                try:
                    coupon = stripe.Coupon.retrieve(body.discount_code)
                    if coupon and coupon.valid:
                        session_params['discounts'] = [{'coupon': body.discount_code}]
                    else:
                        raise HTTPException(status_code=400, detail="Invalid discount code")
                except Exception:
                    raise HTTPException(status_code=400, detail="Invalid discount code")

        # If this is a legacy subscription transition, schedule the new subscription to start when old ends
        if legacy_subscription_end:
            session_params['subscription_data'] = {
                'starts_at': legacy_subscription_end,
                'description': 'Subscription scheduled to start after legacy plan ends',
            }

        # Add idempotency key to prevent duplicate checkout sessions
        # Include user_id and price_id to make it more deterministic for the same request
        idempotency_key = (
            f"checkout_{org.id}_{user.id}_{body.price_id}_{body.quantity}_{int(time.time() // 10)}"
        )

        checkout_session = stripe.checkout.Session.create(**session_params, idempotency_key=idempotency_key)

        return CreateCheckoutSessionResponse(clientSecret=checkout_session.client_secret)
    except HTTPException:
        # Re-raise HTTPException without wrapping it
        raise
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


async def create_free_subscription(
    *,
    request: Request,
    org_id: str,
    body: CreateCheckoutSessionBody,
    orm: Session = Depends(get_orm_session),
) -> CreateFreeSubscriptionResponse:
    """
    Create a subscription directly for cases where a 100% off discount is applied.
    This bypasses the checkout session since no payment is required.
    """
    stripe.api_key = STRIPE_SECRET_KEY

    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe secret key not configured.")

    user: Optional[UserModel] = UserModel.get_by_id(orm, request.state.session.user_id)
    if not user or not user.billing_email:
        raise HTTPException(status_code=400, detail="User email is required to create a subscription.")

    org: Optional[OrgModel] = OrgModel.get_by_id(orm, org_id)

    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    if not org.is_user_admin_or_owner(request.state.session.user_id):
        raise HTTPException(
            status_code=403, detail="User does not have permission to upgrade this organization."
        )

    if org.subscription_id and org.prem_status != PremStatus.free:
        try:
            subscription = stripe.Subscription.retrieve(org.subscription_id)
            if subscription.status in ['active', 'trialing']:
                raise HTTPException(status_code=400, detail="Organization already has an active subscription")
        except stripe.error.StripeError:
            logger.warning(f"Could not retrieve subscription {org.subscription_id} for org {org.id}")
            pass

    if not body.discount_code:
        raise HTTPException(status_code=400, detail="Discount code is required for free subscription")

    try:
        # Resolve the discount code
        coupon, promotion_code_id = await _resolve_discount_code(body.discount_code)

        if not coupon:
            raise HTTPException(status_code=400, detail="Invalid discount code")

        if coupon.percent_off != 100:
            raise HTTPException(status_code=400, detail="This endpoint only supports 100% off discounts")

        # Create a customer for this subscription
        customer = stripe.Customer.create(
            email=user.billing_email, metadata={'org_id': str(org.id), 'user_id': str(user.id)}
        )

        # Create the subscription with the 100% off discount
        subscription_params = {
            'customer': customer.id,
            'items': [{'price': body.price_id}],
            'metadata': {'org_id': str(org.id)},
        }

        # Apply the discount
        if promotion_code_id:
            subscription_params['discounts'] = [{'promotion_code': promotion_code_id}]
        else:
            subscription_params['discounts'] = [{'coupon': body.discount_code}]

        subscription = stripe.Subscription.create(**subscription_params)

        # Update organization with subscription details
        update_org_subscription(orm, org, subscription.id)

        orm.commit()

        logger.info(f"Created free subscription {subscription.id} for org {org_id} with 100% off discount")

        return CreateFreeSubscriptionResponse(
            message="Subscription created successfully with 100% off discount. No payment required.",
            subscription_id=subscription.id,
            org_id=str(org.id),
        )

    except HTTPException:
        raise
    except stripe.error.StripeError as e:
        orm.rollback()
        logger.error(f"Stripe error creating free subscription for org {org_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")
    except Exception as e:
        orm.rollback()
        logger.error(f"Unexpected error creating free subscription for org {org_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


async def cancel_subscription(
    *,
    request: Request,
    org_id: str,
    body: CancelSubscriptionBody,
    orm: Session = Depends(get_orm_session),
) -> StatusResponse:
    """
    Cancel a Stripe subscription for an organization immediately.
    """
    stripe.api_key = STRIPE_SECRET_KEY

    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe secret key not configured.")

    user: Optional[UserModel] = UserModel.get_by_id(orm, request.state.session.user_id)
    if not user:  # Minimal check, primary auth is via endpoint protection
        raise HTTPException(status_code=401, detail="User not authenticated.")

    org: Optional[OrgModel] = OrgModel.get_by_id(orm, org_id)

    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    if not org.is_user_admin_or_owner(request.state.session.user_id):
        raise HTTPException(
            status_code=403,
            detail="User does not have permission to manage this organization's subscription.",
        )

    if not org.subscription_id:
        raise HTTPException(status_code=400, detail="Organization does not have an active subscription.")

    if org.subscription_id != body.subscription_id:
        raise HTTPException(status_code=400, detail="Subscription ID mismatch.")

    try:
        # Add idempotency key to prevent duplicate cancellation requests
        idempotency_key = f"cancel_{org.id}_{body.subscription_id}_{int(time.time())}"
        stripe.Subscription.modify(
            body.subscription_id, cancel_at_period_end=True, idempotency_key=idempotency_key
        )

        logger.info(f"Subscription {body.subscription_id} set to cancel at period end for org {org_id}")

        return StatusResponse(
            message="Subscription will be cancelled at the end of the current billing period."
        )

    except stripe.error.StripeError as e:
        orm.rollback()
        logger.error(
            "Stripe error cancelling subscription %s for org %s: %s", body.subscription_id, org_id, str(e)
        )
        raise HTTPException(
            status_code=500,
            detail=(
                "Stripe error: Could not cancel subscription. "
                "Please try again later or contact support if the issue persists."
            ),
        )
    except Exception as e:
        orm.rollback()
        logger.error(
            "Unexpected error cancelling subscription %s for org %s: %s", body.subscription_id, org_id, str(e)
        )
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


async def reactivate_subscription(
    *,
    request: Request,
    org_id: str,
    orm: Session = Depends(get_orm_session),
) -> StatusResponse:
    """
    Reactivate a subscription that was set to cancel at period end.
    """
    stripe.api_key = STRIPE_SECRET_KEY

    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe secret key not configured.")

    user: Optional[UserModel] = UserModel.get_by_id(orm, request.state.session.user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not authenticated.")

    org: Optional[OrgModel] = OrgModel.get_by_id(orm, org_id)

    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    if not org.is_user_admin_or_owner(request.state.session.user_id):
        raise HTTPException(
            status_code=403,
            detail="User does not have permission to manage this organization's subscription.",
        )

    if not org.subscription_id:
        raise HTTPException(status_code=400, detail="Organization does not have an active subscription.")

    try:
        subscription = stripe.Subscription.retrieve(org.subscription_id)

        if not subscription.cancel_at_period_end:
            raise HTTPException(status_code=400, detail="Subscription is not set to cancel.")

        # Add idempotency key to prevent duplicate reactivation requests
        idempotency_key = f"reactivate_{org.id}_{org.subscription_id}_{int(time.time())}"
        stripe.Subscription.modify(
            org.subscription_id, cancel_at_period_end=False, idempotency_key=idempotency_key
        )

        logger.info(f"Subscription {org.subscription_id} reactivated for org {org_id}")

        return StatusResponse(
            message=(
                "Subscription reactivated successfully. "
                "You will continue to be billed at the next billing cycle."
            )
        )

    except stripe.error.StripeError as e:
        logger.error(
            f"Stripe error reactivating subscription {org.subscription_id} for org {org_id}: {str(e)}"
        )
        raise HTTPException(
            status_code=500,
            detail=(
                "Stripe error: Could not reactivate subscription. Please try again later or contact support."
            ),
        )
    except Exception as e:
        logger.error(
            f"Unexpected error reactivating subscription {org.subscription_id} for org {org_id}: {str(e)}"
        )
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


class UpdateSubscriptionBody(pydantic.BaseModel):
    price_id: Optional[str] = None
    proration_behavior: Optional[str] = "create_prorations"  # create_prorations, always_invoice, none
    payment_behavior: Optional[str] = "allow_incomplete"  # allow_incomplete, error_if_incomplete


class CustomerPortalResponse(pydantic.BaseModel):
    url: str


class PreviewMemberAddResponse(pydantic.BaseModel):
    immediate_charge: float  # Amount in dollars
    next_period_charge: float  # Amount in dollars per billing period
    billing_interval: str
    period_end: Optional[str] = None
    currency: str = "usd"


async def preview_member_add_cost(
    *,
    request: Request,
    org_id: str,
    orm: Session = Depends(get_orm_session),
) -> PreviewMemberAddResponse:
    """
    Preview the cost of adding a new member to the subscription.
    Uses Stripe's upcoming invoice API to get exact proration amounts.
    """
    stripe.api_key = STRIPE_SECRET_KEY

    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe secret key not configured.")

    user: Optional[UserModel] = UserModel.get_by_id(orm, request.state.session.user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not authenticated.")

    org: Optional[OrgModel] = OrgModel.get_by_id(orm, org_id)

    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    if not org.is_user_member(request.state.session.user_id):
        raise HTTPException(
            status_code=403,
            detail="User does not have permission to view this organization's billing.",
        )

    if not org.subscription_id:
        raise HTTPException(status_code=400, detail="Organization does not have an active subscription.")

    try:
        # Get the current subscription
        subscription = stripe.Subscription.retrieve(org.subscription_id, expand=["items.data.price.product"])

        # Find the seat item
        seat_item = None
        for item in subscription.get('items', {}).get('data', []):
            price = item.get('price', {})
            if price.get('id') == STRIPE_SUBSCRIPTION_PRICE_ID:
                seat_item = item
                break

        if not seat_item:
            raise HTTPException(status_code=500, detail="Could not find seat pricing in subscription")

        current_quantity = seat_item.get('quantity', 1)
        price_data = seat_item.get('price', {})

        # Get the upcoming invoice to see current period charges
        upcoming_invoice = stripe.Invoice.create_preview(
            customer=subscription.customer,
            subscription=subscription.id,
            subscription_details={
                'items': [
                    {
                        'id': seat_item.get('id'),
                        'quantity': current_quantity + 1,  # Preview with one additional seat
                    }
                ],
                'proration_behavior': 'create_prorations',
            },
        )

        # Calculate the immediate charge by finding proration line items
        # The recommended way to get only the prorations is to look for line items
        # where parent.subscription_item_details.proration is true
        immediate_charge_cents = 0

        # Get the line items from the preview invoice
        for line_item in upcoming_invoice.lines.data:
            parent = line_item.get('parent', {})
            if parent and parent.get('type') == 'subscription_item_details':
                subscription_item_details = parent.get('subscription_item_details', {})
                # Check if this is a proration line item
                if subscription_item_details.get('proration', False):
                    # Add the proration amount (could be positive for upgrade or negative for downgrade)
                    immediate_charge_cents += line_item.get('amount', 0)

        immediate_charge = max(0, immediate_charge_cents / 100)  # Convert to dollars

        # Get the regular price per billing period
        unit_amount = price_data.get('unit_amount', 0)
        next_period_charge = unit_amount / 100  # Convert to dollars

        # Get billing interval
        recurring = price_data.get('recurring', {})
        interval = recurring.get('interval', 'month')
        interval_count = recurring.get('interval_count', 1)

        if interval_count > 1:
            billing_interval = f"{interval_count} {interval}s"
        else:
            billing_interval = interval

        # Get period end date
        period_end = subscription.get('current_period_end')
        period_end_str = None
        if period_end:
            from datetime import datetime

            period_end_str = datetime.fromtimestamp(period_end).isoformat()

        return PreviewMemberAddResponse(
            immediate_charge=immediate_charge,
            next_period_charge=next_period_charge,
            billing_interval=billing_interval,
            period_end=period_end_str,
            currency=price_data.get('currency', 'usd'),
        )

    except stripe.error.StripeError as e:
        logger.error(f"Stripe error previewing member add cost for org {org_id}: {str(e)}")
        # Return a fallback calculation if Stripe API fails
        return PreviewMemberAddResponse(
            immediate_charge=0,
            next_period_charge=40,  # Default price
            billing_interval="month",
            period_end=None,
            currency="usd",
        )
    except Exception as e:
        logger.error(f"Unexpected error previewing member add cost for org {org_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to preview billing changes.")


class SubscriptionDetailResponse(pydantic.BaseModel):
    subscription_id: str
    status: str
    current_period_start: int
    current_period_end: int
    price_id: Optional[str] = None
    product_name: Optional[str] = None
    quantity: Optional[int] = None


async def get_subscription_detail(
    *,
    request: Request,
    org_id: str,
    orm: Session = Depends(get_orm_session),
) -> SubscriptionDetailResponse:
    """
    Fetch current subscription details from Stripe for refreshing billing data.
    """
    stripe.api_key = STRIPE_SECRET_KEY

    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe secret key not configured.")

    user: Optional[UserModel] = UserModel.get_by_id(orm, request.state.session.user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not authenticated.")

    org: Optional[OrgModel] = OrgModel.get_by_id(orm, org_id)

    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    if not org.is_user_admin_or_owner(request.state.session.user_id):
        raise HTTPException(
            status_code=403,
            detail="User does not have permission to view this organization's subscription.",
        )

    if not org.subscription_id:
        raise HTTPException(status_code=400, detail="Organization does not have an active subscription.")

    try:
        # Get current subscription details from Stripe (same pattern as BillingDashboardView)
        subscription = stripe.Subscription.retrieve(org.subscription_id, expand=["items.data.price.product"])

        # Get product info if available
        product_name = None
        price_id = None
        quantity = None

        # Use the utility function to get period dates
        period_start, period_end = extract_subscription_period_dates(subscription)

        # Get product and quantity info from items
        items = subscription.get('items', {})
        if items and items.get('data') and len(items['data']) > 0:
            first_item = items['data'][0]
            if first_item.get('price'):
                price_id = first_item['price']['id']
                quantity = first_item.get('quantity')

                if first_item['price'].get('product'):
                    # The product object is already expanded
                    product_data = first_item['price'].get('product', {})
                    product_name = product_data.get('name')

        if period_start and period_end:
            logger.info(f"Successfully retrieved period info for subscription {org.subscription_id}")
        else:
            logger.warning(
                f"Could not find billing period dates in Stripe subscription {org.subscription_id}"
            )
            raise HTTPException(status_code=500, detail="Subscription period information not available")

        return SubscriptionDetailResponse(
            subscription_id=subscription.id,
            status=subscription.status,
            current_period_start=period_start,
            current_period_end=period_end,
            price_id=price_id,
            product_name=product_name,
            quantity=quantity,
        )

    except stripe.error.StripeError as e:
        logger.error(f"Stripe error fetching subscription {org.subscription_id} for org {org_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Stripe error: Could not fetch subscription details. {str(e)}"
        )
    except Exception as e:
        logger.error(
            f"Unexpected error fetching subscription {org.subscription_id} for org {org_id}: {str(e)}"
        )
        raise HTTPException(status_code=500, detail="Failed to fetch subscription details. Please try again.")


async def update_subscription(
    *,
    request: Request,
    org_id: str,
    body: UpdateSubscriptionBody,
    orm: Session = Depends(get_orm_session),
) -> StatusResponse:
    """
    Update an existing subscription (change plan, billing, etc.) using Stripe's API.
    This provides in-app subscription management without redirecting to Stripe's portal.
    """
    stripe.api_key = STRIPE_SECRET_KEY

    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe secret key not configured.")

    user: Optional[UserModel] = UserModel.get_by_id(orm, request.state.session.user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not authenticated.")

    org: Optional[OrgModel] = OrgModel.get_by_id(orm, org_id)

    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    if not org.is_user_admin_or_owner(request.state.session.user_id):
        raise HTTPException(
            status_code=403,
            detail="User does not have permission to manage this organization's subscription.",
        )

    if not org.subscription_id:
        raise HTTPException(status_code=400, detail="Organization does not have an active subscription.")

    try:
        # Get current subscription details
        current_subscription = stripe.Subscription.retrieve(org.subscription_id)

        if current_subscription.status not in ['active', 'trialing']:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot update subscription with status: {current_subscription.status}",
            )

        # Check if subscription is scheduled to cancel
        if current_subscription.get('cancel_at_period_end'):
            raise HTTPException(
                status_code=400,
                detail="Your subscription is scheduled to cancel. Updates are not allowed for cancelled subscriptions.",
            )

        update_params = {
            'proration_behavior': body.proration_behavior,
            'payment_behavior': body.payment_behavior,
        }

        # Add idempotency key to prevent duplicate updates
        idempotency_key = f"update_{org.id}_{org.subscription_id}_{int(time.time())}"

        # If changing the plan/price
        if body.price_id:
            # Get the current subscription item
            subscription_items = current_subscription.items.data
            if not subscription_items:
                raise HTTPException(status_code=400, detail="No subscription items found")

            current_item = subscription_items[0]  # Assuming single item subscription

            # Update the subscription item with new price
            update_params['items'] = [
                {
                    'id': current_item.id,
                    'price': body.price_id,
                }
            ]

        # Update the subscription
        stripe.Subscription.modify(
            org.subscription_id,
            idempotency_key=idempotency_key,
            **update_params,
        )

        logger.info(f"Subscription {org.subscription_id} updated for org {org_id}")

        # Determine the response message based on what was updated
        if body.price_id:
            message = "Subscription plan updated successfully."
            if body.proration_behavior == "always_invoice":
                message += " You will be charged/credited for the prorated amount immediately."
            elif body.proration_behavior == "create_prorations":
                message += " Prorated charges will be applied to your next invoice."
        else:
            message = "Subscription updated successfully."

        return StatusResponse(message=message)

    except stripe.error.StripeError as e:
        logger.error(f"Stripe error updating subscription {org.subscription_id} for org {org_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Stripe error: Could not update subscription. {str(e)}")
    except Exception as e:
        logger.error(
            f"Unexpected error updating subscription {org.subscription_id} for org {org_id}: {str(e)}"
        )
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


async def create_customer_portal_session(
    *,
    request: Request,
    org_id: str,
    orm: Session = Depends(get_orm_session),
) -> CustomerPortalResponse:
    """
    Create a Stripe Customer Portal session for advanced subscription management.
    This is a fallback option for complex billing scenarios.
    """
    stripe.api_key = STRIPE_SECRET_KEY

    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe secret key not configured.")

    user: Optional[UserModel] = UserModel.get_by_id(orm, request.state.session.user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not authenticated.")

    org: Optional[OrgModel] = OrgModel.get_by_id(orm, org_id)

    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    if not org.is_user_admin_or_owner(request.state.session.user_id):
        raise HTTPException(
            status_code=403,
            detail="User does not have permission to manage this organization's subscription.",
        )

    if not org.subscription_id:
        raise HTTPException(status_code=400, detail="Organization does not have an active subscription.")

    try:
        # Get the customer ID from the subscription
        subscription = stripe.Subscription.retrieve(org.subscription_id)
        customer_id = subscription.customer

        # Create customer portal session
        portal_session = stripe.billing_portal.Session.create(
            customer=customer_id, return_url=f"{APP_URL}/settings/organization"
        )

        return CustomerPortalResponse(url=portal_session.url)

    except stripe.error.StripeError as e:
        logger.error(f"Stripe error creating customer portal for org {org_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Stripe error: Could not create customer portal session. {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error creating customer portal for org {org_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


async def get_stripe_pricing(
    *,
    request: Request,
    org_id: str,
    orm: Session = Depends(get_orm_session),
) -> dict:
    """Get current Stripe pricing information including seat and usage pricing."""
    if not _validate_and_set_stripe_key("get_stripe_pricing"):
        raise HTTPException(status_code=500, detail="Stripe configuration error")

    # Log all price ID status for debugging
    _validate_stripe_price_ids("get_stripe_pricing")

    user: Optional[UserModel] = UserModel.get_by_id(orm, request.state.session.user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not authenticated.")

    org: Optional[OrgModel] = OrgModel.get_by_id(orm, org_id)
    if not org or not org.is_user_member(request.state.session.user_id):
        raise HTTPException(status_code=403, detail="Access denied.")

    try:
        # Get seat pricing
        seat_price_id = os.getenv("STRIPE_SUBSCRIPTION_PRICE_ID")
        if not seat_price_id:
            raise HTTPException(status_code=500, detail="Stripe seat price ID not configured")

        seat_price = stripe.Price.retrieve(seat_price_id)

        # Extract seat price using robust method
        from ..services.billing_service import billing_service

        seat_price_amount = billing_service._extract_price_amount(seat_price, seat_price_id)
        if seat_price_amount is None:
            logger.warning(f"Seat price {seat_price_id} has no valid pricing amount, using fallback")
            raise HTTPException(status_code=500, detail="Seat price amount not available")

        pricing_data = {
            "seat": {
                "priceId": seat_price_id,
                "amount": int(round(seat_price_amount)),  # Amount in cents (rounded to whole cents)
                "currency": seat_price.currency,
                "interval": seat_price.recurring.interval if seat_price.recurring else "one_time",
                "interval_count": seat_price.recurring.interval_count if seat_price.recurring else None,
            }
        }

        # Get usage pricing
        token_price_id = STRIPE_TOKEN_PRICE_ID
        span_price_id = STRIPE_SPAN_PRICE_ID

        if token_price_id:
            try:
                token_price = stripe.Price.retrieve(token_price_id, expand=['currency_options', 'tiers'])
                token_price_amount = billing_service._extract_price_amount(token_price, token_price_id)
                if token_price_amount is not None:
                    pricing_data["tokens"] = {
                        "priceId": token_price_id,
                        "amount": token_price_amount,  # Amount in cents
                        "currency": token_price.currency,
                        "unit_size": token_price.transform_quantity.divide_by
                        if token_price.transform_quantity
                        else 1000,
                        "display_unit": "thousand tokens",
                    }
                else:
                    logger.warning(
                        f"Token price {token_price_id} has no valid pricing amount, using fallback"
                    )
                    # Use fallback values when Stripe price has no amount
                    pricing_data["tokens"] = {
                        "priceId": None,  # Set to None since price is not usable
                        "amount": 0.02,  # $0.0002 = 0.02 cents (fractional cents)
                        "currency": "usd",
                        "unit_size": 1000,
                        "display_unit": "thousand tokens",
                    }
            except (stripe.error.StripeError, ValueError) as e:
                logger.warning(f"Failed to fetch token price from Stripe: {e}")
                # Use fallback
                pricing_data["tokens"] = {
                    "priceId": None,
                    "amount": 0.02,  # $0.0002 = 0.02 cents (fractional cents)
                    "currency": "usd",
                    "unit_size": 1000,
                    "display_unit": "thousand tokens",
                }

        if span_price_id:
            try:
                span_price = stripe.Price.retrieve(span_price_id, expand=['currency_options', 'tiers'])
                span_price_amount = billing_service._extract_price_amount(span_price, span_price_id)
                if span_price_amount is not None:
                    pricing_data["spans"] = {
                        "priceId": span_price_id,
                        "amount": span_price_amount,  # Amount in cents
                        "currency": span_price.currency,
                        "unit_size": span_price.transform_quantity.divide_by
                        if span_price.transform_quantity
                        else 1000,
                        "display_unit": "thousand spans",
                    }
                else:
                    logger.warning(f"Span price {span_price_id} has no valid pricing amount, using fallback")
                    # Use fallback values when Stripe price has no amount
                    pricing_data["spans"] = {
                        "priceId": None,  # Set to None since price is not usable
                        "amount": 0.01,  # $0.0001 = 0.01 cents (fractional cents)
                        "currency": "usd",
                        "unit_size": 1000,
                        "display_unit": "thousand spans",
                    }
            except (stripe.error.StripeError, ValueError) as e:
                logger.warning(f"Failed to fetch span price from Stripe: {e}")
                # Use fallback
                pricing_data["spans"] = {
                    "priceId": None,
                    "amount": 0.01,  # $0.0001 = 0.01 cents (fractional cents)
                    "currency": "usd",
                    "unit_size": 1000,
                    "display_unit": "thousand spans",
                }

        return pricing_data

    except stripe.error.StripeError as e:
        logger.error(f"Failed to fetch pricing from Stripe: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch pricing information")


def get_org_invites_for_org(
    *,
    request: Request,
    org_id: str,
    orm: Session = Depends(get_orm_session),
) -> list[OrgInviteDetailResponse]:
    """Get all pending invites for an organization (admin/owner only)."""
    org = OrgModel.get_by_id(orm, org_id)
    if not org or not org.is_user_admin_or_owner(request.state.session.user_id):
        raise HTTPException(status_code=404, detail="Organization not found")

    # Query all invites for this org
    invites = orm.query(OrgInviteModel).filter(OrgInviteModel.org_id == org_id).all()

    logger.debug("get_org_invites_for_org: Found %d total invites for org %s", len(invites), org_id)

    result = []
    for invite in invites:
        logger.debug(
            "Processing invite: inviter_id=%s, invitee_email=%s, role=%s",
            invite.inviter_id,
            invite.invitee_email,
            invite.role,
        )
        invitee_email = invite.invitee_email

        # Check if this user is already a member of the org
        already_member = (
            orm.query(UserOrgModel)
            .filter(
                func.lower(UserOrgModel.user_email) == invitee_email.lower(), UserOrgModel.org_id == org_id
            )
            .first()
        )

        # Skip this invite if user is already a member
        if already_member:
            logger.debug("Skipping invite for %s - already a member of org", invitee_email)
            continue

        # Get inviter's actual email from inviter_id
        inviter_user = UserModel.get_by_id(orm, invite.inviter_id)

        # Check if the invitee exists in our system using ORM
        user_exists = False
        existing_user = (
            orm.query(UserModel)
            .join(AuthUserModel, UserModel.id == AuthUserModel.id)
            .filter(func.lower(AuthUserModel.email) == invitee_email.lower())
            .first()
        )

        if not existing_user:
            # Also check regular email field
            existing_user = (
                orm.query(UserModel).filter(func.lower(UserModel.email) == invitee_email.lower()).first()
            )

        user_exists = existing_user is not None

        result.append(
            OrgInviteDetailResponse(
                invitee_email=invitee_email,
                inviter_email=inviter_user.billing_email if inviter_user else "Unknown",
                role=invite.role.value if hasattr(invite.role, 'value') else invite.role,
                org_id=str(invite.org_id),
                org_name=invite.org_name,
                created_at=getattr(invite, 'created_at', None),
                user_exists=user_exists,
            )
        )

    orm.commit()
    return result


def revoke_org_invite(
    *,
    request: Request,
    org_id: str,
    email: str,
    orm: Session = Depends(get_orm_session),
) -> StatusResponse:
    """Revoke an invitation."""
    org = OrgModel.get_by_id(orm, org_id)
    if not org or not org.is_user_admin_or_owner(request.state.session.user_id):
        raise HTTPException(status_code=404, detail="Organization not found")

    invite = (
        orm.query(OrgInviteModel)
        .filter(func.lower(OrgInviteModel.invitee_email) == email.lower(), OrgInviteModel.org_id == org_id)
        .first()
    )

    if not invite:
        raise HTTPException(status_code=404, detail="Invitation not found")

    orm.delete(invite)
    orm.commit()
    logger.debug("Invitation revoked for %s in org %s", email, org_id)

    return StatusResponse(message="Invitation revoked successfully")
