import pytest
import uuid
from fastapi import HTTPException
from sqlalchemy import orm

from agentops.opsboard.models import (
    OrgModel,
    UserOrgModel,
    ProjectModel,
    OrgRoles,
    Environment,
)
from agentops.opsboard.views.projects import (
    regenerate_api_key,
)


@pytest.mark.asyncio
async def test_regenerate_api_key_not_admin(mock_request, orm_session, test_user):
    """Test regenerating a project's API key without admin permissions."""
    # Create all the test data in this test
    org = OrgModel(name="Test Org for Non-Admin Regenerate Key")
    orm_session.add(org)
    orm_session.flush()

    # Create a user-org relationship with developer role (not admin or owner)
    user_org = UserOrgModel(
        user_id=test_user.id, 
        org_id=org.id, 
        role=OrgRoles.developer,  # Developer role, not admin or owner
        user_email=test_user.email
    )
    orm_session.add(user_org)
    orm_session.flush()

    # Create a project with a specific API key
    initial_api_key = uuid.uuid4()
    project = ProjectModel(
        name="Project for Non-Admin Key Regeneration",
        org_id=org.id,
        environment=Environment.development,
        api_key=initial_api_key,
    )
    orm_session.add(project)
    orm_session.flush()

    # Load relationships to ensure they're available
    project = (
        orm_session.query(ProjectModel)
        .options(orm.joinedload(ProjectModel.org).joinedload(OrgModel.users))
        .filter_by(id=project.id)
        .one()
    )

    # Expect an HTTP 404 exception (security through obscurity)
    with pytest.raises(HTTPException) as excinfo:
        regenerate_api_key(request=mock_request, project_id=str(project.id), orm=orm_session)

    assert excinfo.value.status_code == 404
    assert excinfo.value.detail == "Project not found"

    # Verify the API key wasn't changed
    unchanged_project = orm_session.query(ProjectModel).filter_by(id=project.id).one()
    assert unchanged_project.api_key == initial_api_key


@pytest.mark.asyncio
async def test_regenerate_api_key_project_not_found(mock_request, orm_session):
    """Test regenerating an API key for a project that doesn't exist."""
    non_existent_id = str(uuid.uuid4())

    # Expect an HTTP 404 exception
    with pytest.raises(HTTPException) as excinfo:
        regenerate_api_key(request=mock_request, project_id=non_existent_id, orm=orm_session)

    assert excinfo.value.status_code == 404
    assert excinfo.value.detail == "Project not found"