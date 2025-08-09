import pytest
import uuid
from fastapi import HTTPException
from unittest.mock import patch

from agentops.opsboard.models import (
    OrgModel,
    UserOrgModel,
    ProjectModel,
    OrgRoles,
    Environment,
)
from agentops.opsboard.views.projects import (
    get_projects,
    get_project,
    create_project,
    update_project,
)
from agentops.opsboard.schemas import (
    ProjectCreateSchema,
    ProjectUpdateSchema,
)


@pytest.mark.asyncio
async def test_get_projects_with_missing_count(mock_request, orm_session, test_user):
    """Test getting projects when a project has no trace/span count data."""
    # Create an org first
    org = OrgModel(name="Test Org for Missing Counts")
    orm_session.add(org)
    orm_session.flush()

    # Create a user-org relationship with the test user fixture
    user_org = UserOrgModel(
        user_id=test_user.id, org_id=org.id, role=OrgRoles.owner, user_email=test_user.email
    )
    orm_session.add(user_org)

    # Create a project
    project = ProjectModel(
        name="Test Project Without Counts", org_id=org.id, environment=Environment.development
    )
    orm_session.add(project)
    orm_session.flush()

    # Mock TraceCountsModel.select to return empty counts
    empty_counts = []
    with patch('agentops.api.models.metrics.TraceCountsModel.select', return_value=empty_counts):
        # Call the endpoint function
        result = await get_projects(request=mock_request, orm=orm_session)

    # Verify that it returns a list and the test project is in the results
    assert isinstance(result, list)
    assert len(result) > 0

    # Find our project in the results
    project_response = None
    for p in result:
        if p.id == str(project.id):
            project_response = p
            break

    assert project_response is not None
    assert project_response.name == project.name
    # Verify that the counts are not set (they should be None or default)
    assert project_response.span_count == 0
    assert project_response.trace_count == 0


@pytest.mark.asyncio
async def test_get_project_user_not_member(mock_request, orm_session, test_user, test_user2):
    """Test getting a project when the user is not a member of the organization."""
    # Create an org that the test user is NOT a member of
    org = OrgModel(name="Test Org Not Member")
    orm_session.add(org)
    orm_session.flush()

    # Add test_user2 as the owner (not the main test user)
    user_org = UserOrgModel(
        user_id=test_user2.id, org_id=org.id, role=OrgRoles.owner, user_email=test_user2.email
    )
    orm_session.add(user_org)

    # Create a project in that org
    project = ProjectModel(name="Test Project Non-Member", org_id=org.id, environment=Environment.development)
    orm_session.add(project)
    orm_session.commit()

    # Expect an HTTP 404 exception when the main test user tries to access it
    with pytest.raises(HTTPException) as excinfo:
        get_project(request=mock_request, project_id=str(project.id), orm=orm_session)

    assert excinfo.value.status_code == 404
    assert excinfo.value.detail == "Project not found"


@pytest.mark.asyncio
async def test_create_project_default_environment(mock_request, orm_session, test_user):
    """Test creating a project without specifying an environment (should use development)."""
    # Create a fresh org and user-org relationship
    org = OrgModel(name="Test Org for Default Environment")
    orm_session.add(org)
    orm_session.flush()

    # Add the test user as an owner of the org
    user_id = mock_request.state.session.user_id
    user_org = UserOrgModel(
        user_id=user_id, org_id=org.id, role=OrgRoles.owner, user_email="test@example.com"
    )
    orm_session.add(user_org)
    orm_session.flush()

    # Create the request body WITHOUT environment field
    body = ProjectCreateSchema(
        name="Project With Default Environment",
        org_id=str(org.id),
        # environment is intentionally omitted
    )

    # Call the endpoint function
    result = create_project(request=mock_request, orm=orm_session, body=body)

    # Verify the project was created with the default environment
    assert result.name == body.name
    assert result.org_id == body.org_id
    assert result.environment == Environment.development.value
    assert result.api_key is not None

    # Verify in the database
    created_project = orm_session.query(ProjectModel).filter_by(id=uuid.UUID(result.id)).one()
    assert created_project.name == body.name
    assert created_project.environment == Environment.development


@pytest.mark.asyncio
async def test_update_project_name_only(mock_request, orm_session, test_project):
    """Test updating only a project's name, not environment."""
    # Create the update body with only name
    new_name = "Updated Project Name Only"
    body = ProjectUpdateSchema(name=new_name)

    # Execute the update
    result = update_project(request=mock_request, project_id=str(test_project.id), orm=orm_session, body=body)

    # Verify only the name was updated
    assert result.name == new_name
    assert result.environment == test_project.environment.value  # should remain unchanged

    # Refresh the session to get the latest data
    orm_session.expire_all()

    # Verify the database was updated correctly
    updated_project = orm_session.query(ProjectModel).filter_by(id=test_project.id).one()
    assert updated_project.name == new_name
    assert updated_project.environment == test_project.environment  # should remain unchanged


@pytest.mark.asyncio
async def test_update_project_environment_only(mock_request, orm_session, test_project):
    """Test updating only a project's environment, not name."""
    # Get the original name for verification later
    original_name = test_project.name

    # Create the update body with only environment
    new_environment = Environment.production.value
    body = ProjectUpdateSchema(environment=new_environment)

    # Execute the update
    result = update_project(request=mock_request, project_id=str(test_project.id), orm=orm_session, body=body)

    # Verify only the environment was updated
    assert result.name == original_name  # should remain unchanged
    assert result.environment == new_environment

    # Refresh the session to get the latest data
    orm_session.expire_all()

    # Verify the database was updated correctly
    updated_project = orm_session.query(ProjectModel).filter_by(id=test_project.id).one()
    assert updated_project.name == original_name  # should remain unchanged
    assert updated_project.environment == Environment.production
