import pytest
from fastapi import HTTPException

from agentops.opsboard.models import (
    OrgModel,
    UserOrgModel,
    OrgInviteModel,
    ProjectModel,
    OrgRoles,
    Environment,
    PremStatus,
)
from agentops.opsboard.views.orgs import (
    delete_org,
    accept_org_invite,
)


@pytest.mark.asyncio
async def test_delete_org(mock_request, orm_session, test_user):
    """Test deleting an organization."""
    # Create a fresh organization for this test
    org = OrgModel(
        name="Test Org for Deletion",
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

    # Call the endpoint function
    result = delete_org(request=mock_request, org_id=str(org.id), orm=orm_session)

    # Verify the status response
    assert result.success is True
    assert result.message == "Organization deleted"

    # Verify the organization was deleted
    deleted_org = orm_session.query(OrgModel).filter_by(id=org.id).first()
    assert deleted_org is None


@pytest.mark.asyncio
async def test_delete_org_not_owner(mock_request, orm_session, test_user):
    """Test deleting an organization without owner permissions."""
    # Create a fresh organization for this test
    org = OrgModel(
        name="Test Org for Non-Owner Deletion",
        prem_status=PremStatus.free,
    )
    orm_session.add(org)
    orm_session.flush()

    # Create a user-org relationship with admin role (not owner)
    user_id = mock_request.state.session.user_id
    user_org = UserOrgModel(
        user_id=user_id, org_id=org.id, role=OrgRoles.admin, user_email="test@example.com"
    )
    orm_session.add(user_org)
    orm_session.commit()  # Commit to ensure it's persisted

    # Expect a 403 exception
    with pytest.raises(HTTPException) as excinfo:
        delete_org(request=mock_request, org_id=str(org.id), orm=orm_session)

    assert excinfo.value.status_code == 403
    assert excinfo.value.detail == "Organization cannot be deleted"

    # Verify the organization still exists
    org_still_exists = orm_session.query(OrgModel).filter_by(id=org.id).first()
    assert org_still_exists is not None


@pytest.mark.asyncio
async def test_delete_org_with_projects(mock_request, orm_session, test_user):
    """Test deleting an organization that still has projects (should fail)."""
    # Create a fresh organization for this test
    org = OrgModel(
        name="Test Org with Projects",
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
    orm_session.flush()

    # Create a project in the organization
    project = ProjectModel(name="Test Project", org_id=org.id, environment=Environment.development)
    orm_session.add(project)
    orm_session.commit()  # Commit to ensure it's persisted

    # Reload the org with all relationships
    org = OrgModel.get_by_id(orm_session, org.id)

    # Expect a 400 exception
    with pytest.raises(HTTPException) as excinfo:
        delete_org(request=mock_request, org_id=str(org.id), orm=orm_session)

    assert excinfo.value.status_code == 400
    assert excinfo.value.detail == "Organization cannot be deleted while it still contains projects"

    # Verify the organization still exists
    org_still_exists = orm_session.query(OrgModel).filter_by(id=org.id).first()
    assert org_still_exists is not None


@pytest.mark.asyncio
async def test_accept_org_invite_user_not_found(mock_request, orm_session, test_user, monkeypatch):
    """Test accepting an invitation when the user doesn't exist."""
    # Create a fresh organization for this test
    org = OrgModel(
        name="Test Org for Invite",
        prem_status=PremStatus.free,
    )
    orm_session.add(org)
    orm_session.flush()

    invite = OrgInviteModel(
        inviter_id=test_user.id,  # Use existing test user as inviter
        invitee_email="test@example.com",
        org_id=org.id,
        role=OrgRoles.developer,
        org_name=org.name,
    )
    orm_session.add(invite)
    orm_session.commit()  # Ensure it's persisted

    # Mock UserModel.get_by_id to return None
    from agentops.opsboard.models import UserModel

    def mock_get_by_id(session, user_id):
        return None

    monkeypatch.setattr(UserModel, "get_by_id", mock_get_by_id)

    # Since auth user exists in test data but UserModel.get_by_id returns None,
    # the function will try to wait for user creation and then return 500
    with pytest.raises(HTTPException) as excinfo:
        accept_org_invite(request=mock_request, org_id=str(org.id), orm=orm_session)

    assert excinfo.value.status_code == 500
    assert "User record not yet created" in excinfo.value.detail
