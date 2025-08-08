import pytest
import uuid
import os
from unittest.mock import patch
from fastapi import HTTPException
from sqlalchemy import orm
import stripe

from agentops.opsboard.models import (
    OrgModel,
    UserOrgModel,
    UserModel,
    OrgInviteModel,
    OrgRoles,
    PremStatus,
)
from agentops.opsboard.views.orgs import (
    get_user_orgs,
    get_org,
    create_org,
    update_org,
    invite_to_org,
    get_org_invites,
    accept_org_invite,
    remove_from_org,
    change_member_role,
    create_checkout_session,
    CreateCheckoutSessionBody,
)
from agentops.opsboard.schemas import (
    OrgCreateSchema,
    OrgUpdateSchema,
    OrgInviteSchema,
    OrgMemberRemoveSchema,
    OrgMemberRoleSchema,
)


# Mock Stripe environment variables for testing to avoid warnings
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


@pytest.mark.asyncio
async def test_get_user_orgs(mock_request, orm_session, test_user_org_owner):
    """Test getting all organizations for a user."""
    # Call the endpoint function
    result = get_user_orgs(request=mock_request, orm=orm_session)

    # Verify that it returns a list and contains our test org
    assert isinstance(result, list)
    assert len(result) > 0

    # Check that our test org is in the results
    org_ids = [o.id for o in result]
    assert str(test_user_org_owner.id) in org_ids


@pytest.mark.asyncio
async def test_get_org(mock_request, orm_session, test_user_org_member):
    """Test getting a specific organization by ID."""
    # Call the endpoint function
    result = get_org(request=mock_request, org_id=str(test_user_org_member.id), orm=orm_session)

    # Verify the org data matches
    assert result.id == str(test_user_org_member.id)
    assert result.name == test_user_org_member.name
    assert len(result.users) == 1
    assert result.users[0].user_id == "00000000-0000-0000-0000-000000000000"
    assert result.users[0].role == OrgRoles.developer.value


@pytest.mark.asyncio
async def test_get_org_not_found(mock_request, orm_session):
    """Test getting an organization that doesn't exist."""
    non_existent_id = str(uuid.uuid4())

    # Expect an HTTP 404 exception
    with pytest.raises(HTTPException) as excinfo:
        get_org(request=mock_request, org_id=non_existent_id, orm=orm_session)

    assert excinfo.value.status_code == 404
    assert excinfo.value.detail == "Organization not found"


@pytest.mark.asyncio
async def test_create_org(mock_request, orm_session, test_user):
    """Test creating a new organization."""
    # Create the request body
    body = OrgCreateSchema(name="New Test Organization")

    # Call the endpoint function
    result = create_org(request=mock_request, orm=orm_session, body=body)

    # Verify the organization was created with the right data
    assert result.name == body.name
    assert result.id is not None

    # Verify we can find it in the database
    created_org = orm_session.query(OrgModel).filter_by(id=uuid.UUID(result.id)).one()
    assert created_org.name == body.name

    # Verify that the user is an owner
    user_org = orm_session.query(UserOrgModel).filter_by(user_id=test_user.id, org_id=created_org.id).one()
    assert user_org.role == OrgRoles.owner


@pytest.mark.asyncio
async def test_update_org(mock_request, orm_session, test_user):
    """Test updating an organization's name."""
    # Create a fresh organization for this test
    org = OrgModel(
        name="Original Org Name",
        prem_status=PremStatus.free,
    )
    orm_session.add(org)
    orm_session.flush()

    # Create a user-org relationship
    user_id = mock_request.state.session.user_id
    user_org = UserOrgModel(
        user_id=user_id, org_id=org.id, role=OrgRoles.owner, user_email="test@example.com"
    )
    orm_session.add(user_org)
    orm_session.commit()  # Commit to ensure it's persisted

    # Create the update body
    body = OrgUpdateSchema(name="Updated Organization Name")

    # Fetch org again with relationships to ensure we have the latest
    org = orm_session.query(OrgModel).options(orm.selectinload(OrgModel.users)).filter_by(id=org.id).one()

    # Verify the user is an owner of this org
    membership = org.get_user_membership(user_id)
    assert membership is not None, "User membership not found"
    assert membership.role == OrgRoles.owner, "User is not an owner"

    # Now call the update endpoint
    result = update_org(request=mock_request, org_id=str(org.id), orm=orm_session, body=body)

    # Verify the updates were applied
    assert result.name == body.name

    # Refresh the session to get the latest data
    orm_session.expire_all()  # Clear cached objects

    # Verify the database was updated
    updated_org = orm_session.query(OrgModel).filter_by(id=org.id).one()
    assert updated_org.name == body.name


@pytest.mark.asyncio
async def test_update_org_not_admin(mock_request, orm_session, test_user_org_member):
    """Test updating an organization without admin permissions."""
    # Change the role to developer (not admin or owner)
    user_org = test_user_org_member.get_user_membership(mock_request.state.session.user_id)
    user_org.role = OrgRoles.developer
    orm_session.flush()

    # Create the update body
    body = OrgUpdateSchema(name="Updated Organization Name")

    # Expect an HTTP 404 exception (since we use security by obscurity)
    with pytest.raises(HTTPException) as excinfo:
        update_org(request=mock_request, org_id=str(test_user_org_member.id), orm=orm_session, body=body)

    assert excinfo.value.status_code == 404
    assert excinfo.value.detail == "Organization not found"

    # Restore the role
    user_org.role = OrgRoles.owner
    orm_session.flush()


@pytest.mark.asyncio
@patch('agentops.opsboard.views.orgs._send_invitation_email')
async def test_invite_to_org(mock_send_email, mock_request, orm_session, test_user):
    """Test inviting a user to an organization."""
    # Mock the email function to not raise any exceptions
    mock_send_email.return_value = None

    # Create a fresh organization for this test
    org = OrgModel(
        name="Test Org for Invites",
        prem_status=PremStatus.enterprise,  # Use enterprise to avoid the member limit
    )
    orm_session.add(org)
    orm_session.flush()

    # Create a user-org relationship
    user_id = mock_request.state.session.user_id
    user_org = UserOrgModel(
        user_id=user_id, org_id=org.id, role=OrgRoles.owner, user_email="test@example.com"
    )
    orm_session.add(user_org)
    orm_session.commit()  # Commit to ensure it's persisted

    # Create the invite body
    body = OrgInviteSchema(email="newuser@example.com", role=OrgRoles.developer.value)

    # Fetch org again with relationships to ensure we have the latest
    org = (
        orm_session.query(OrgModel)
        .options(orm.selectinload(OrgModel.users), orm.selectinload(OrgModel.invites))
        .filter_by(id=org.id)
        .one()
    )

    # Verify the user is an owner of this org
    membership = org.get_user_membership(user_id)
    assert membership is not None, "User membership not found"
    assert membership.role == OrgRoles.owner, "User is not an owner"

    # Now call the invite endpoint
    result = invite_to_org(request=mock_request, org_id=str(org.id), orm=orm_session, body=body)

    # Verify the status response
    assert result.success is True
    assert result.message == "Invitation sent successfully"

    # Verify the invite exists in the database
    invite = orm_session.query(OrgInviteModel).filter_by(org_id=org.id, invitee_email=body.email).one()
    assert invite.role == OrgRoles.developer
    assert invite.org_name == org.name


@pytest.mark.asyncio
async def test_invite_to_org_already_member(mock_request, orm_session, test_user_org_owner):
    """Test inviting a user who is already a member."""
    # Create the invite body with the same email as the existing member
    body = OrgInviteSchema(email="test@example.com", role=OrgRoles.developer.value)

    # Expect an HTTP 400 exception
    with pytest.raises(HTTPException) as excinfo:
        invite_to_org(request=mock_request, org_id=str(test_user_org_owner.id), orm=orm_session, body=body)

    assert excinfo.value.status_code == 400
    assert excinfo.value.detail == "User is already a member of this organization"


@pytest.mark.asyncio
async def test_invite_to_org_not_admin(mock_request, orm_session, test_user_org_member):
    """Test inviting a user without admin permissions."""
    # Change the role to developer (not admin or owner)
    user_org = test_user_org_member.get_user_membership(mock_request.state.session.user_id)
    user_org.role = OrgRoles.developer
    orm_session.flush()

    # Create the invite body
    body = OrgInviteSchema(email="newuser@example.com", role=OrgRoles.developer.value)

    # Expect an HTTP 404 exception (since we use security by obscurity)
    with pytest.raises(HTTPException) as excinfo:
        invite_to_org(request=mock_request, org_id=str(test_user_org_member.id), orm=orm_session, body=body)

    assert excinfo.value.status_code == 404
    assert excinfo.value.detail == "Organization not found"

    # Restore the role
    user_org.role = OrgRoles.owner
    orm_session.flush()


@pytest.mark.asyncio
@patch('agentops.opsboard.views.orgs._send_invitation_email')
async def test_invite_to_org_case_insensitive(mock_send_email, mock_request, orm_session, test_user):
    """Test that email invitations are case-insensitive."""
    mock_send_email.return_value = None

    org = OrgModel(
        name="Test Org for Case Sensitivity",
        prem_status=PremStatus.enterprise,
    )
    orm_session.add(org)
    orm_session.flush()

    user_id = mock_request.state.session.user_id
    user_org = UserOrgModel(
        user_id=user_id, org_id=org.id, role=OrgRoles.owner, user_email="test@example.com"
    )
    orm_session.add(user_org)
    orm_session.commit()

    body = OrgInviteSchema(email="newuser@example.com", role=OrgRoles.developer.value)
    result = invite_to_org(request=mock_request, org_id=str(org.id), orm=orm_session, body=body)
    assert result.success is True

    body_upper = OrgInviteSchema(email="NEWUSER@example.com", role=OrgRoles.developer.value)
    with pytest.raises(HTTPException) as excinfo:
        invite_to_org(request=mock_request, org_id=str(org.id), orm=orm_session, body=body_upper)
    assert excinfo.value.status_code == 400
    assert excinfo.value.detail == "User already has a pending invitation"

    body_mixed = OrgInviteSchema(email="NewUser@Example.COM", role=OrgRoles.developer.value)
    with pytest.raises(HTTPException) as excinfo:
        invite_to_org(request=mock_request, org_id=str(org.id), orm=orm_session, body=body_mixed)
    assert excinfo.value.status_code == 400
    assert excinfo.value.detail == "User already has a pending invitation"

    invite = orm_session.query(OrgInviteModel).filter_by(org_id=org.id).one()
    assert invite.invitee_email == "newuser@example.com"  # Should be lowercase


@pytest.mark.asyncio
async def test_invite_to_org_member_limit(mock_request, orm_session, test_user):
    """Test inviting a user when the organization has reached its member limit."""
    # Create a fresh organization with free plan (which has a member limit of 1)
    org = OrgModel(
        name="Test Org with Member Limit",
        prem_status=PremStatus.free,  # Free plan has a member limit of 1
    )
    orm_session.add(org)
    orm_session.flush()

    # Create a user-org relationship (this is the first and only allowed member)
    user_id = mock_request.state.session.user_id
    user_org = UserOrgModel(
        user_id=user_id, org_id=org.id, role=OrgRoles.owner, user_email="test@example.com"
    )
    orm_session.add(user_org)
    orm_session.commit()  # Commit to ensure it's persisted

    # Create the invite body for a second user (which should exceed the limit)
    body = OrgInviteSchema(email="newuser@example.com", role=OrgRoles.developer.value)

    # Expect an HTTP 400 exception due to member limit
    with pytest.raises(HTTPException) as excinfo:
        invite_to_org(request=mock_request, org_id=str(org.id), orm=orm_session, body=body)

    assert excinfo.value.status_code == 400
    assert excinfo.value.detail == "Organization has reached its member limit"

    # Verify no invite was created
    invites = orm_session.query(OrgInviteModel).filter_by(org_id=org.id).all()
    assert len(invites) == 0


@pytest.mark.asyncio
@patch('agentops.opsboard.views.orgs._send_invitation_email')
async def test_invite_to_org_after_upgrade(mock_send_email, mock_request, orm_session, test_user):
    """Test inviting users after upgrading from free to enterprise plan."""
    # Mock the email function to not raise any exceptions
    mock_send_email.return_value = None

    # Create a fresh organization with free plan (which has a member limit of 1)
    org = OrgModel(
        name="Test Org for Plan Upgrade",
        prem_status=PremStatus.free,  # Free plan has a member limit of 1
    )
    orm_session.add(org)
    orm_session.flush()

    # Create a user-org relationship (this is the first and only allowed member)
    user_id = mock_request.state.session.user_id
    user_org = UserOrgModel(
        user_id=user_id, org_id=org.id, role=OrgRoles.owner, user_email="test@example.com"
    )
    orm_session.add(user_org)
    orm_session.commit()  # Commit to ensure it's persisted

    # Upgrade the organization plan to enterprise (which has no member limit)
    org.prem_status = PremStatus.enterprise
    orm_session.commit()

    # Reload the org with all relationships
    org = OrgModel.get_by_id(orm_session, org.id)

    # Create the invite body for a second user (which should now work)
    body = OrgInviteSchema(email="newuser@example.com", role=OrgRoles.developer.value)

    # This should now succeed with the enterprise plan
    result = invite_to_org(request=mock_request, org_id=str(org.id), orm=orm_session, body=body)

    # Verify the invite success response
    assert result.success is True
    assert result.message == "Invitation sent successfully"

    # Verify the invite was created in the database
    invites = orm_session.query(OrgInviteModel).filter_by(org_id=org.id).all()
    assert len(invites) == 1
    assert invites[0].invitee_email == "newuser@example.com"
    assert invites[0].role == OrgRoles.developer


@pytest.mark.asyncio
async def test_get_org_invites(mock_request, orm_session, test_user):
    """Test getting all invitations for the authenticated user (as invitee)."""
    # Create a fresh org for this test
    org = OrgModel(name="Test Org for Invites")
    orm_session.add(org)
    orm_session.flush()

    invite = OrgInviteModel(
        inviter_id=test_user.id,
        invitee_email="test@example.com",
        org_id=org.id,
        role=OrgRoles.developer,
        org_name=org.name,
    )
    orm_session.add(invite)
    orm_session.commit()  # Commit to ensure it's persisted

    # Call the endpoint function
    result = get_org_invites(request=mock_request, orm=orm_session)

    # Verify the result contains our invite
    assert isinstance(result, list)
    assert len(result) > 0

    # Find our invite in the results (might be other test artifacts)
    our_invite = None
    for invite_response in result:
        if invite_response.org_id == str(org.id) and invite_response.invitee_email == "test@example.com":
            our_invite = invite_response
            break

    assert our_invite is not None
    assert our_invite.inviter_id == str(test_user.id)
    assert our_invite.org_id == str(org.id)
    assert our_invite.role == OrgRoles.developer.value
    assert our_invite.invitee_email == "test@example.com"


@pytest.mark.asyncio
async def test_accept_org_invite(mock_request, orm_session, test_user):
    """Test accepting an invitation to join an organization."""
    # Create a fresh organization for this test
    org = OrgModel(
        name="Test Org for Invite",
        prem_status=PremStatus.free,
    )
    orm_session.add(org)
    orm_session.flush()

    # The current user ID from the mock request
    user_id = mock_request.state.session.user_id

    invite = OrgInviteModel(
        inviter_id=test_user.id,
        invitee_email="test@example.com",
        org_id=org.id,
        role=OrgRoles.developer,
        org_name=org.name,
    )
    orm_session.add(invite)
    orm_session.commit()  # Ensure it's persisted

    # Now we should be able to find the invitation when accept_org_invite runs
    invitation = (
        orm_session.query(OrgInviteModel).filter_by(invitee_email="test@example.com", org_id=org.id).first()
    )
    assert invitation is not None, "Invitation not found in database"

    # Call the endpoint function
    result = accept_org_invite(request=mock_request, org_id=str(org.id), orm=orm_session)

    # Verify the status response
    assert result.success is True
    assert result.message == "Organization invitation accepted"

    # Verify the invite was removed and user-org relationship was created
    invites = (
        orm_session.query(OrgInviteModel).filter_by(invitee_email="test@example.com", org_id=org.id).all()
    )
    assert len(invites) == 0

    # Verify the user-org relationship was created
    user_orgs = orm_session.query(UserOrgModel).filter_by(user_id=user_id, org_id=org.id).all()
    assert len(user_orgs) > 0


@pytest.mark.asyncio
async def test_accept_org_invite_case_insensitive(mock_request, orm_session, test_user):
    """Test accepting an invitation with different email casing."""
    org = OrgModel(
        name="Test Org for Case Sensitive Accept",
        prem_status=PremStatus.free,
    )
    orm_session.add(org)
    orm_session.flush()

    invite = OrgInviteModel(
        inviter_id=test_user.id,
        invitee_email="test@example.com",
        org_id=org.id,
        role=OrgRoles.developer,
        org_name=org.name,
    )
    orm_session.add(invite)
    orm_session.commit()

    # Get the test user from the session to ensure auth_user relationship is loaded
    user_from_session = orm_session.get(UserModel, test_user.id)
    if not user_from_session:
        pytest.skip("Test user not found in session")

    # Check if auth_user exists, if not skip this test
    if not user_from_session.auth_user:
        pytest.skip("Test user does not have auth_user relationship set up")

    # Save the original email
    original_email = user_from_session.auth_user.email

    # Temporarily modify the auth user's email in memory only (not persisted)
    # This simulates a user whose auth email has different casing
    object.__setattr__(user_from_session.auth_user, 'email', 'TEST@EXAMPLE.COM')

    try:
        # Accept with the uppercase email (should still find the lowercase invite)
        result = accept_org_invite(request=mock_request, org_id=str(org.id), orm=orm_session)

        # Verify the result
        assert result.success is True
        assert result.message == "Organization invitation accepted"

        # Verify invite was removed
        invites = orm_session.query(OrgInviteModel).filter_by(org_id=org.id).all()
        assert len(invites) == 0

        # Verify user was added to org
        user_id = mock_request.state.session.user_id
        user_orgs = orm_session.query(UserOrgModel).filter_by(user_id=user_id, org_id=org.id).all()
        assert len(user_orgs) > 0

    finally:
        # Restore the original email
        object.__setattr__(user_from_session.auth_user, 'email', original_email)


@pytest.mark.asyncio
async def test_accept_org_invite_not_found(mock_request, orm_session):
    """Test accepting an invitation that doesn't exist."""
    non_existent_id = str(uuid.uuid4())

    # Expect an HTTP 404 exception
    with pytest.raises(HTTPException) as excinfo:
        accept_org_invite(request=mock_request, org_id=non_existent_id, orm=orm_session)

    assert excinfo.value.status_code == 404
    assert excinfo.value.detail == "Invitation not found"


@pytest.mark.asyncio
async def test_remove_from_org(mock_request, orm_session, test_user2):
    """Test removing a user from an organization."""
    # Create a fresh organization for this test
    org = OrgModel(
        name="Test Org for Remove",
        prem_status=PremStatus.free,
    )
    orm_session.add(org)
    orm_session.flush()

    # Add the primary test user as an owner
    user_id = mock_request.state.session.user_id
    user_org = UserOrgModel(
        user_id=user_id, org_id=org.id, role=OrgRoles.owner, user_email="test@example.com"
    )
    orm_session.add(user_org)

    # Add the second test user as a developer
    user2_org = UserOrgModel(
        user_id=test_user2.id,
        org_id=org.id,
        role=OrgRoles.developer,
        user_email=test_user2.email,
    )
    orm_session.add(user2_org)
    orm_session.commit()  # Commit to ensure both relationships are persisted

    # Create the remove body using the second user's ID
    body = OrgMemberRemoveSchema(user_id=str(test_user2.id))

    # Fetch org again with relationships
    org = orm_session.query(OrgModel).options(orm.selectinload(OrgModel.users)).filter_by(id=org.id).one()

    # Verify both users are in the org
    assert len(org.users) == 2, "Expected both users to be in the org"

    # Call the endpoint function
    result = remove_from_org(request=mock_request, org_id=str(org.id), orm=orm_session, body=body)

    # Verify the status response
    assert result.success is True
    assert result.message == "User removed from organization"

    # Verify the user was removed
    user_orgs = orm_session.query(UserOrgModel).filter_by(user_id=test_user2.id, org_id=org.id).all()
    assert len(user_orgs) == 0, "Expected the second user to be removed from the org"


@pytest.mark.asyncio
async def test_remove_from_org_owner(mock_request, orm_session, test_user, test_user2):
    """Test removing an owner from an organization (which should fail)."""
    # First create a fresh org
    org = OrgModel(name="Test Org for Remove Owner")
    orm_session.add(org)
    orm_session.flush()

    # Add the primary test user as owner
    user_id = mock_request.state.session.user_id
    user_org = UserOrgModel(
        user_id=user_id, org_id=org.id, role=OrgRoles.owner, user_email="test@example.com"
    )
    orm_session.add(user_org)
    orm_session.flush()

    # Add test_user2 as an owner
    # We're using the existing test_user2 fixture which already exists in auth.users
    second_user_org = UserOrgModel(
        user_id=test_user2.id,
        org_id=org.id,
        role=OrgRoles.owner,
        user_email=test_user2.email,
    )
    orm_session.add(second_user_org)
    orm_session.commit()  # Need to commit to ensure relationships are persisted

    # Create the remove body - try to remove the second owner
    body = OrgMemberRemoveSchema(user_id=str(test_user2.id))

    # Expect an HTTP 400 exception
    with pytest.raises(HTTPException) as excinfo:
        remove_from_org(request=mock_request, org_id=str(org.id), orm=orm_session, body=body)

    assert excinfo.value.status_code == 400
    assert excinfo.value.detail == "User cannot be removed"


@pytest.mark.asyncio
async def test_remove_from_org_self(mock_request, orm_session, test_user_org_owner):
    """Test removing yourself from an organization (which should fail)."""
    # Create the remove body with the authenticated user's ID
    body = OrgMemberRemoveSchema(user_id=str(mock_request.state.session.user_id))

    # Expect an HTTP 400 exception
    with pytest.raises(HTTPException) as excinfo:
        remove_from_org(request=mock_request, org_id=str(test_user_org_owner.id), orm=orm_session, body=body)

    assert excinfo.value.status_code == 400
    assert excinfo.value.detail == "User cannot be removed"


@pytest.mark.asyncio
async def test_change_member_role(mock_request, orm_session, test_user2):
    """Test changing a user's role in an organization."""
    # Create a fresh organization for this test
    org = OrgModel(
        name="Test Org for Role Change",
        prem_status=PremStatus.free,
    )
    orm_session.add(org)
    orm_session.flush()

    # Add the primary test user as an owner
    user_id = mock_request.state.session.user_id
    user_org = UserOrgModel(
        user_id=user_id, org_id=org.id, role=OrgRoles.owner, user_email="test@example.com"
    )
    orm_session.add(user_org)

    # Add the second test user as a developer
    user2_org = UserOrgModel(
        user_id=test_user2.id,
        org_id=org.id,
        role=OrgRoles.developer,
        user_email=test_user2.email,
    )
    orm_session.add(user2_org)
    orm_session.commit()  # Commit to ensure both relationships are persisted

    # Create the role change body using the second user's ID
    body = OrgMemberRoleSchema(user_id=str(test_user2.id), role=OrgRoles.admin.value)

    # Call the endpoint function
    result = change_member_role(request=mock_request, org_id=str(org.id), orm=orm_session, body=body)

    # Verify the status response
    assert result.success is True
    assert result.message == "User role updated"

    # Refresh the session to get the latest data from the database
    orm_session.expire_all()  # Clear cached objects

    # Verify the role was updated
    user_org = orm_session.query(UserOrgModel).filter_by(user_id=test_user2.id, org_id=org.id).one()
    assert user_org.role == OrgRoles.admin, "Expected the user role to be updated to admin"


@pytest.mark.asyncio
async def test_change_member_role_to_owner(mock_request, orm_session, test_user2):
    """Test changing a user's role to owner."""
    # Create a fresh organization for this test to avoid session issues
    org = OrgModel(
        name="Test Org for Owner Role Change",
        prem_status=PremStatus.free,
    )
    orm_session.add(org)
    orm_session.flush()

    # Add the primary test user as an owner
    user_id = mock_request.state.session.user_id
    user_org = UserOrgModel(
        user_id=user_id, org_id=org.id, role=OrgRoles.owner, user_email="test@example.com"
    )
    orm_session.add(user_org)

    # Add test_user2 as a developer
    user2_org = UserOrgModel(
        user_id=test_user2.id,
        org_id=org.id,
        role=OrgRoles.developer,
        user_email=test_user2.email,
    )
    orm_session.add(user2_org)
    orm_session.commit()  # Commit to ensure both relationships are persisted

    # Create the role change body
    body = OrgMemberRoleSchema(user_id=str(test_user2.id), role=OrgRoles.owner.value)

    # Call the endpoint function
    result = change_member_role(request=mock_request, org_id=str(org.id), orm=orm_session, body=body)

    # Verify the status response
    assert result.success is True
    assert result.message == "User role updated"

    # Refresh the session to get the latest data from the database
    orm_session.expire_all()  # Clear cached objects

    # Verify the role was updated
    user_org = orm_session.query(UserOrgModel).filter_by(user_id=test_user2.id, org_id=org.id).one()
    assert user_org.role == OrgRoles.owner


@pytest.mark.asyncio
async def test_change_member_role_from_owner_to_developer(
    mock_request, orm_session, test_user_org_owner, test_user2
):
    """Test changing a user's role from owner to developer (when there are multiple owners)."""
    # Create a fresh organization for this test to avoid session issues
    org = OrgModel(
        name="Test Org for Role Change",
        prem_status=PremStatus.free,
    )
    orm_session.add(org)
    orm_session.flush()

    # Add the primary test user as an owner
    user_id = mock_request.state.session.user_id
    user_org = UserOrgModel(
        user_id=user_id, org_id=org.id, role=OrgRoles.owner, user_email="test@example.com"
    )
    orm_session.add(user_org)

    # Add test_user2 as another owner
    user2_org = UserOrgModel(
        user_id=test_user2.id,
        org_id=org.id,
        role=OrgRoles.owner,
        user_email=test_user2.email,
    )
    orm_session.add(user2_org)
    orm_session.commit()  # Commit to ensure both relationships are persisted

    # Create the role change body
    body = OrgMemberRoleSchema(user_id=str(test_user2.id), role=OrgRoles.developer.value)

    # Call the endpoint function
    result = change_member_role(request=mock_request, org_id=str(org.id), orm=orm_session, body=body)

    # Verify the status response
    assert result.success is True
    assert result.message == "User role updated"

    # Refresh the session to get the latest data from the database
    orm_session.expire_all()  # Clear cached objects

    # Verify the role was updated
    user_org = orm_session.query(UserOrgModel).filter_by(user_id=test_user2.id, org_id=org.id).one()
    assert user_org.role == OrgRoles.developer


@pytest.mark.asyncio
async def test_change_last_owner_role(mock_request, orm_session):
    """Test changing the role of the last owner (which should fail)."""
    # Create a fresh organization for this test to avoid session issues
    org = OrgModel(
        name="Test Org for Last Owner Role",
        prem_status=PremStatus.free,
    )
    orm_session.add(org)
    orm_session.flush()

    # Add the primary test user as the only owner
    user_id = mock_request.state.session.user_id
    user_org = UserOrgModel(
        user_id=user_id, org_id=org.id, role=OrgRoles.owner, user_email="test@example.com"
    )
    orm_session.add(user_org)
    orm_session.commit()  # Commit to ensure the relationship is persisted

    # Create the role change body to change the only owner to a developer
    body = OrgMemberRoleSchema(user_id=str(mock_request.state.session.user_id), role=OrgRoles.developer.value)

    # Expect an HTTP 400 exception when trying to change the only owner's role
    with pytest.raises(HTTPException) as excinfo:
        change_member_role(request=mock_request, org_id=str(org.id), orm=orm_session, body=body)

    # Verify the error message
    assert excinfo.value.status_code == 400
    assert excinfo.value.detail == "Cannot remove the last owner"

    # Verify the role wasn't changed
    orm_session.expire_all()  # Clear cached objects
    user_org = orm_session.query(UserOrgModel).filter_by(user_id=user_id, org_id=org.id).one()
    assert user_org.role == OrgRoles.owner, "The user role should not have been changed"


@pytest.mark.asyncio
async def test_change_member_role_as_admin(mock_request, orm_session, test_user, test_user2, test_user3):
    """Test changing a user's role as an admin (not owner)."""
    # Create a fresh organization for this test
    org = OrgModel(
        name="Test Org for Admin Role Change",
        prem_status=PremStatus.free,
    )
    orm_session.add(org)
    orm_session.flush()

    # Add test_user2 as the owner
    owner_org = UserOrgModel(
        user_id=test_user2.id,
        org_id=org.id,
        role=OrgRoles.owner,
        user_email=test_user2.email,
    )
    orm_session.add(owner_org)

    # Add the primary test user as an admin (not owner)
    user_id = mock_request.state.session.user_id
    user_org = UserOrgModel(
        user_id=user_id, org_id=org.id, role=OrgRoles.admin, user_email="test@example.com"
    )
    orm_session.add(user_org)

    # Add test_user3 as a developer
    dev_org = UserOrgModel(
        user_id=test_user3.id, org_id=org.id, role=OrgRoles.developer, user_email=test_user3.email
    )
    orm_session.add(dev_org)
    orm_session.commit()  # Commit to ensure all relationships are persisted

    # Create the role change body to promote developer to admin
    body = OrgMemberRoleSchema(user_id=str(test_user3.id), role=OrgRoles.admin.value)

    # Call the endpoint function with the admin user (mock_request contains test_user's ID)
    result = change_member_role(request=mock_request, org_id=str(org.id), orm=orm_session, body=body)

    # Verify the status response
    assert result.success is True
    assert result.message == "User role updated"

    # Refresh the session to get the latest data from the database
    orm_session.expire_all()  # Clear cached objects

    # Verify the role was updated
    user_org = orm_session.query(UserOrgModel).filter_by(user_id=test_user3.id, org_id=org.id).one()
    assert user_org.role == OrgRoles.admin

    # Verify admin cannot promote someone to owner
    body = OrgMemberRoleSchema(user_id=str(test_user3.id), role=OrgRoles.owner.value)

    # Expect an HTTP 400 exception
    with pytest.raises(HTTPException) as excinfo:
        change_member_role(request=mock_request, org_id=str(org.id), orm=orm_session, body=body)

    assert excinfo.value.status_code == 400
    assert excinfo.value.detail == "Only owners can assign the owner role"


@pytest.mark.asyncio
@patch('stripe.checkout.Session.create')
@patch('stripe.Price.retrieve')
@patch('stripe.PromotionCode.list')
@patch('agentops.opsboard.views.orgs.STRIPE_SECRET_KEY', 'test_stripe_key')
async def test_create_checkout_session_with_valid_promotion_code(
    mock_promo_list, mock_price_retrieve, mock_stripe_session, mock_request, orm_session, test_user
):
    """Test successful checkout with a promotion code."""
    # Create a fresh organization for this test
    org = OrgModel(
        name="Test Org for Promotion Code",
        prem_status=PremStatus.free,
    )
    orm_session.add(org)
    orm_session.flush()

    # Create a user-org relationship
    user_id = mock_request.state.session.user_id
    user_org = UserOrgModel(
        user_id=user_id, org_id=org.id, role=OrgRoles.owner, user_email="test@example.com"
    )
    orm_session.add(user_org)
    orm_session.commit()

    # Ensure the auth_user relationship is loaded (the test user should already have billing_email)
    user_from_session = orm_session.get(UserModel, test_user.id)
    if not user_from_session:
        pytest.skip("Test user not found in session")

    # Verify the user has billing_email from auth.users
    if not user_from_session.billing_email:
        pytest.skip("Test user does not have billing_email set up properly")

    # Mock the promotion code lookup
    mock_promo_code = type('obj', (object,), {'id': 'promo_123'})
    mock_promo_list.return_value.data = [mock_promo_code]

    # Mock the price retrieve call
    mock_price = type('obj', (object,), {'recurring': type('obj', (object,), {'usage_type': 'licensed'})})
    mock_price_retrieve.return_value = mock_price

    # Mock the Stripe session creation
    mock_stripe_session.return_value.client_secret = "test_client_secret_123"

    # Create the request body with promotion code
    body = CreateCheckoutSessionBody(price_id="price_test123", discount_code="SAVE20")

    # Call the endpoint with the new signature
    result = await create_checkout_session(
        request=mock_request, org_id=str(org.id), body=body, orm=orm_session
    )

    # Verify the response
    assert result.clientSecret == "test_client_secret_123"

    # Verify promotion code lookup was called
    mock_promo_list.assert_called_once_with(code="SAVE20", active=True, limit=1)

    # Verify Stripe was called with the promotion code ID
    mock_stripe_session.assert_called_once()
    call_args = mock_stripe_session.call_args[1]
    assert call_args['discounts'] == [{'promotion_code': 'promo_123'}]
    assert call_args['customer_email'] == user_from_session.billing_email
    assert call_args['line_items'][0]['price'] == "price_test123"


@pytest.mark.asyncio
@patch('stripe.checkout.Session.create')
@patch('stripe.Price.retrieve')
@patch('stripe.Coupon.retrieve')
@patch('stripe.PromotionCode.list')
@patch('agentops.opsboard.views.orgs.STRIPE_SECRET_KEY', 'test_stripe_key')
async def test_create_checkout_session_with_valid_coupon_id(
    mock_promo_list,
    mock_coupon_retrieve,
    mock_price_retrieve,
    mock_stripe_session,
    mock_request,
    orm_session,
    test_user,
):
    """Test successful checkout with a direct coupon ID."""
    # Create a fresh organization for this test
    org = OrgModel(
        name="Test Org for Coupon",
        prem_status=PremStatus.free,
    )
    orm_session.add(org)
    orm_session.flush()

    # Create a user-org relationship
    user_id = mock_request.state.session.user_id
    user_org = UserOrgModel(
        user_id=user_id, org_id=org.id, role=OrgRoles.owner, user_email="test@example.com"
    )
    orm_session.add(user_org)
    orm_session.commit()

    # Ensure the auth_user relationship is loaded (the test user should already have billing_email)
    user_from_session = orm_session.get(UserModel, test_user.id)
    if not user_from_session:
        pytest.skip("Test user not found in session")

    # Verify the user has billing_email from auth.users
    if not user_from_session.billing_email:
        pytest.skip("Test user does not have billing_email set up properly")

    # Mock promotion code lookup to return empty (not a promotion code)
    mock_promo_list.return_value.data = []

    # Mock coupon retrieval to return a valid coupon
    mock_coupon = type('obj', (object,), {'valid': True})
    mock_coupon_retrieve.return_value = mock_coupon

    # Mock the price retrieve call
    mock_price = type('obj', (object,), {'recurring': type('obj', (object,), {'usage_type': 'licensed'})})
    mock_price_retrieve.return_value = mock_price

    # Mock the Stripe session creation
    mock_stripe_session.return_value.client_secret = "test_client_secret_456"

    # Create the request body with coupon ID
    body = CreateCheckoutSessionBody(price_id="price_test456", discount_code="SUMMER_SALE")

    # Call the endpoint with the new signature
    result = await create_checkout_session(
        request=mock_request, org_id=str(org.id), body=body, orm=orm_session
    )

    # Verify the response
    assert result.clientSecret == "test_client_secret_456"

    # Verify promotion code lookup was called first
    mock_promo_list.assert_called_once_with(code="SUMMER_SALE", active=True, limit=1)

    # Verify coupon retrieval was called as fallback
    mock_coupon_retrieve.assert_called_once_with("SUMMER_SALE")

    # Verify Stripe was called with the coupon
    mock_stripe_session.assert_called_once()
    call_args = mock_stripe_session.call_args[1]
    assert call_args['discounts'] == [{'coupon': "SUMMER_SALE"}]
    assert call_args['customer_email'] == user_from_session.billing_email
    assert call_args['line_items'][0]['price'] == "price_test456"


@pytest.mark.asyncio
@patch('stripe.checkout.Session.create')
@patch('stripe.Price.retrieve')
@patch('stripe.Coupon.retrieve')
@patch('stripe.PromotionCode.list')
@patch('agentops.opsboard.views.orgs.STRIPE_SECRET_KEY', 'test_stripe_key')
async def test_create_checkout_session_with_invalid_discount_code(
    mock_promo_list,
    mock_coupon_retrieve,
    mock_price_retrieve,
    mock_stripe_session,
    mock_request,
    orm_session,
    test_user,
):
    """Test error handling for invalid discount codes."""
    # Create a fresh organization for this test
    org = OrgModel(
        name="Test Org for Invalid Code",
        prem_status=PremStatus.free,
    )
    orm_session.add(org)
    orm_session.flush()

    # Create a user-org relationship
    user_id = mock_request.state.session.user_id
    user_org = UserOrgModel(
        user_id=user_id, org_id=org.id, role=OrgRoles.owner, user_email="test@example.com"
    )
    orm_session.add(user_org)
    orm_session.commit()

    # Ensure the auth_user relationship is loaded (the test user should already have billing_email)
    user_from_session = orm_session.get(UserModel, test_user.id)
    if not user_from_session:
        pytest.skip("Test user not found in session")

    # Verify the user has billing_email from auth.users
    if not user_from_session.billing_email:
        pytest.skip("Test user does not have billing_email set up properly")

    # Mock promotion code lookup to return empty (not a promotion code)
    mock_promo_list.return_value.data = []

    # Mock coupon retrieval to raise an error (invalid coupon)
    mock_coupon_retrieve.side_effect = stripe.error.InvalidRequestError(
        message="No such coupon: 'INVALID'", param="coupon"
    )

    # Mock the price retrieve call
    mock_price = type('obj', (object,), {'recurring': type('obj', (object,), {'usage_type': 'licensed'})})
    mock_price_retrieve.return_value = mock_price

    # Create the request body with invalid discount code
    body = CreateCheckoutSessionBody(price_id="price_test789", discount_code="INVALID")

    from agentops.opsboard.views.orgs import create_checkout_session

    # Expect an HTTP 400 exception for invalid discount code
    with pytest.raises(HTTPException) as excinfo:
        await create_checkout_session(
            request=mock_request,
            org_id=str(org.id),
            body=body,
            orm=orm_session,
        )

    assert excinfo.value.status_code == 400
    assert excinfo.value.detail == "Invalid discount code"


@pytest.mark.asyncio
@patch('stripe.checkout.Session.create')
@patch('stripe.Price.retrieve')
@patch('agentops.opsboard.views.orgs.STRIPE_SECRET_KEY', 'test_stripe_key')
async def test_create_checkout_session_without_discount_code(
    mock_price_retrieve, mock_stripe_session, mock_request, orm_session, test_user
):
    """Test that checkout works without a discount code."""
    # Create a fresh organization for this test
    org = OrgModel(
        name="Test Org No Discount",
        prem_status=PremStatus.free,
    )
    orm_session.add(org)
    orm_session.flush()

    # Create a user-org relationship
    user_id = mock_request.state.session.user_id
    user_org = UserOrgModel(
        user_id=user_id, org_id=org.id, role=OrgRoles.owner, user_email="test@example.com"
    )
    orm_session.add(user_org)
    orm_session.commit()

    # Ensure the auth_user relationship is loaded (the test user should already have billing_email)
    user_from_session = orm_session.get(UserModel, test_user.id)
    if not user_from_session:
        pytest.skip("Test user not found in session")

    # Verify the user has billing_email from auth.users
    if not user_from_session.billing_email:
        pytest.skip("Test user does not have billing_email set up properly")

    # Mock the price retrieve call
    mock_price = type('obj', (object,), {'recurring': type('obj', (object,), {'usage_type': 'licensed'})})
    mock_price_retrieve.return_value = mock_price

    # Mock the Stripe session creation
    mock_stripe_session.return_value.client_secret = "test_client_secret_no_discount"

    # Create the request body without any discount
    body = CreateCheckoutSessionBody(price_id="price_test999")

    from agentops.opsboard.views.orgs import create_checkout_session

    # Call the endpoint without discount parameters
    result = await create_checkout_session(
        request=mock_request, org_id=str(org.id), body=body, orm=orm_session
    )

    # Verify the response
    assert result.clientSecret == "test_client_secret_no_discount"

    # Verify Stripe was called without discounts
    mock_stripe_session.assert_called_once()
    call_args = mock_stripe_session.call_args[1]
    assert 'discounts' not in call_args  # No discounts field when not using discount codes
    assert call_args['customer_email'] == user_from_session.billing_email
    assert call_args['line_items'][0]['price'] == "price_test999"


@pytest.mark.asyncio
@patch('agentops.opsboard.views.orgs.STRIPE_SECRET_KEY', 'test_stripe_key')
@patch('stripe.Subscription.retrieve')
async def test_get_user_orgs_with_discount(mock_stripe_subscription, mock_request, orm_session, test_user):
    """Test that discount info is properly returned in organization list."""
    # Create a fresh organization with pro status and subscription
    org = OrgModel(
        name="Test Org with Discount", prem_status=PremStatus.pro, subscription_id="sub_test_with_discount"
    )
    orm_session.add(org)
    orm_session.flush()

    # Create a user-org relationship
    user_id = mock_request.state.session.user_id
    user_org = UserOrgModel(
        user_id=user_id, org_id=org.id, role=OrgRoles.owner, user_email="test@example.com"
    )
    orm_session.add(user_org)
    orm_session.commit()

    # Mock Stripe subscription with discount
    mock_subscription = {
        'id': 'sub_test_with_discount',
        'status': 'active',
        'current_period_start': 1734000000,  # Some start timestamp
        'current_period_end': 1735689600,  # Some future timestamp
        'cancel_at_period_end': False,
        'discount': {
            'coupon': {'id': 'SUMMER_SALE', 'percent_off': 20, 'valid': True},
            'promotion_code': 'SAVE20',
        },
    }
    mock_stripe_subscription.return_value = mock_subscription

    from agentops.opsboard.views.orgs import get_user_orgs

    # Call the endpoint
    result = get_user_orgs(request=mock_request, orm=orm_session)

    # Find our test org in the results
    test_org_response = None
    for org_response in result:
        if org_response.id == str(org.id):
            test_org_response = org_response
            break

    assert test_org_response is not None
    assert test_org_response.subscription_end_date == 1735689600
    assert test_org_response.subscription_cancel_at_period_end is False

    # Note: The current implementation doesn't return discount info in the response
    # This test verifies the subscription details are fetched correctly
    # If discount info needs to be added to the response, the schema and view would need updates
