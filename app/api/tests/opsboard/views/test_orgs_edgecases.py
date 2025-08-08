import pytest
import uuid
from fastapi import HTTPException
from sqlalchemy import orm

from agentops.opsboard.models import (
    OrgModel,
    UserOrgModel,
    OrgInviteModel,
    OrgRoles,
    PremStatus,
    UserModel,
)
from agentops.opsboard.views.orgs import (
    create_org,
    invite_to_org,
    remove_from_org,
    change_member_role,
)
from agentops.opsboard.schemas import (
    OrgCreateSchema,
    OrgInviteSchema,
    OrgMemberRemoveSchema,
    OrgMemberRoleSchema,
)


@pytest.mark.asyncio
async def test_create_org_user_not_found(mock_request, orm_session, monkeypatch):
    """Test creating an organization when the user doesn't exist."""
    # Mock orm.get to return None for UserModel (user not found)
    original_get_by_id = UserModel.get_by_id

    def mock_get_by_id(session, id):
        return None

    # Apply the monkeypatch
    monkeypatch.setattr(UserModel, "get_by_id", mock_get_by_id)

    # Create the request body
    body = OrgCreateSchema(name="New Test Organization")

    # Expect an HTTP 500 exception
    with pytest.raises(HTTPException) as excinfo:
        create_org(request=mock_request, orm=orm_session, body=body)

    assert excinfo.value.status_code == 500
    assert excinfo.value.detail == "User not found"

    # Restore the original method
    monkeypatch.setattr(UserModel, "get_by_id", original_get_by_id)


@pytest.mark.asyncio
async def test_invite_to_org_existing_invite(mock_request, orm_session, test_user):
    """Test inviting a user when there's an existing invite for the same email."""
    # Create a fresh organization for this test
    org = OrgModel(
        name="Test Org for Existing Invite",
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

    # First create an invitation
    invite_email = "newuser@example.com"
    invite = OrgInviteModel(
        inviter_id=user_id,
        invitee_email=invite_email,
        org_id=org.id,
        role=OrgRoles.developer,
        org_name=org.name,
    )
    orm_session.add(invite)
    orm_session.commit()

    # Fetch org again with relationships to ensure we have the latest
    org = (
        orm_session.query(OrgModel)
        .options(orm.selectinload(OrgModel.users), orm.selectinload(OrgModel.invites))
        .filter_by(id=org.id)
        .one()
    )

    # Try to create another invite with the same email
    body = OrgInviteSchema(email=invite_email, role=OrgRoles.admin.value)

    # Expect an HTTP 400 exception
    with pytest.raises(HTTPException) as excinfo:
        invite_to_org(request=mock_request, org_id=str(org.id), orm=orm_session, body=body)

    assert excinfo.value.status_code == 400
    assert excinfo.value.detail == "User already has a pending invitation"


@pytest.mark.asyncio
async def test_remove_from_org_user_not_found(mock_request, orm_session, test_user):
    """Test removing a user who isn't part of the organization."""
    # Create a fresh organization for this test
    org = OrgModel(
        name="Test Org for Remove Non-Member",
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
    orm_session.commit()  # Commit to ensure both relationships are persisted

    # Create the remove body using a non-existent user ID
    non_member_id = str(uuid.uuid4())
    body = OrgMemberRemoveSchema(user_id=non_member_id)

    # Expect an HTTP 400 exception
    with pytest.raises(HTTPException) as excinfo:
        remove_from_org(request=mock_request, org_id=str(org.id), orm=orm_session, body=body)

    assert excinfo.value.status_code == 400
    assert excinfo.value.detail == "User cannot be removed"


@pytest.mark.asyncio
async def test_change_member_role_non_owner_promotes_to_owner(
    mock_request, orm_session, test_user, test_user2, test_user3
):
    """Test when a non-owner tries to promote someone to owner."""
    # Create a fresh organization for this test
    org = OrgModel(
        name="Test Org for Non-Owner Promotion",
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

    # Attempt to promote the developer to owner by the admin (not owner)
    body = OrgMemberRoleSchema(user_id=str(test_user3.id), role=OrgRoles.owner.value)

    # Expect an HTTP 400 exception
    with pytest.raises(HTTPException) as excinfo:
        change_member_role(request=mock_request, org_id=str(org.id), orm=orm_session, body=body)

    assert excinfo.value.status_code == 400
    assert excinfo.value.detail == "Only owners can assign the owner role"

    # Verify the role wasn't changed
    orm_session.expire_all()  # Clear cached objects
    user_org = orm_session.query(UserOrgModel).filter_by(user_id=test_user3.id, org_id=org.id).one()
    assert user_org.role == OrgRoles.developer, "The user role should not have been changed"
