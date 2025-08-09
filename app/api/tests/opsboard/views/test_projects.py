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
    PremStatus,
)
from agentops.opsboard.views.projects import (
    get_projects,
    get_project,
    create_project,
    update_project,
    delete_project,
    regenerate_api_key,
)
from agentops.opsboard.schemas import (
    ProjectCreateSchema,
    ProjectUpdateSchema,
)


@pytest.mark.asyncio
async def test_get_projects(mock_request, orm_session, test_user):
    """Test getting all projects for a user."""
    # Create an org first
    org = OrgModel(name="Test Org for Projects")
    orm_session.add(org)
    orm_session.flush()

    # Create a user-org relationship with the test user fixture
    user_org = UserOrgModel(
        user_id=test_user.id, org_id=org.id, role=OrgRoles.owner, user_email=test_user.email
    )
    orm_session.add(user_org)

    # Create a project
    project = ProjectModel(name="Test Project", org_id=org.id, environment=Environment.development)
    orm_session.add(project)
    orm_session.flush()

    # Call the endpoint function
    result = await get_projects(request=mock_request, orm=orm_session)

    # Verify that it returns a list and the test project is in the results
    assert isinstance(result, list)
    assert len(result) > 0

    # Check that our test project is in the results
    project_ids = [p.id for p in result]
    assert str(project.id) in project_ids


@pytest.mark.asyncio
async def test_get_project(mock_request, orm_session, test_project):
    """Test getting a specific project by ID."""
    # Call the endpoint function
    result = get_project(request=mock_request, project_id=str(test_project.id), orm=orm_session)

    # Verify the project data matches
    assert result.id == str(test_project.id)
    assert result.name == test_project.name
    assert result.environment == test_project.environment.value
    assert result.api_key == str(test_project.api_key)
    assert result.org_id == str(test_project.org_id)
    assert result.org.id == str(test_project.org.id)
    assert result.org.name == test_project.org.name


@pytest.mark.asyncio
async def test_get_project_not_found(mock_request, orm_session):
    """Test getting a project that doesn't exist."""
    non_existent_id = str(uuid.uuid4())

    # Expect an HTTP 404 exception
    with pytest.raises(HTTPException) as excinfo:
        get_project(request=mock_request, project_id=non_existent_id, orm=orm_session)

    assert excinfo.value.status_code == 404
    assert excinfo.value.detail == "Project not found"


@pytest.mark.asyncio
async def test_create_project(mock_request, orm_session, test_user):
    """Test creating a new project."""
    # Create a fresh org and user-org relationship
    org = OrgModel(name="Test Org for Create")
    orm_session.add(org)
    orm_session.flush()

    # Add the test user as an owner of the org
    user_id = mock_request.state.session.user_id
    user_org = UserOrgModel(
        user_id=user_id, org_id=org.id, role=OrgRoles.owner, user_email="test@example.com"
    )
    orm_session.add(user_org)
    orm_session.flush()

    # Create the request body
    body = ProjectCreateSchema(
        name="New Test Project", org_id=str(org.id), environment=Environment.staging.value
    )

    # Call the endpoint function
    result = create_project(request=mock_request, orm=orm_session, body=body)

    # Verify the project was created with the right data
    assert result.name == body.name
    assert result.org_id == body.org_id
    assert result.environment == body.environment
    assert result.api_key is not None

    # Verify we can find it in the database
    created_project = orm_session.query(ProjectModel).filter_by(id=uuid.UUID(result.id)).one()
    assert created_project.name == body.name
    assert created_project.environment == Environment.staging


@pytest.mark.asyncio
async def test_create_project_not_admin(mock_request, orm_session, test_user):
    """Test creating a project without admin permissions."""
    # Create an org directly in this test
    org = OrgModel(name="Test Org for Non-Admin Test")
    orm_session.add(org)
    orm_session.flush()

    # Create a user-org relationship with developer role (not admin or owner)
    user_org = UserOrgModel(
        user_id=test_user.id, org_id=org.id, role=OrgRoles.developer, user_email=test_user.email
    )
    orm_session.add(user_org)
    orm_session.flush()

    # Create the request body
    body = ProjectCreateSchema(
        name="New Test Project", org_id=str(org.id), environment=Environment.staging.value
    )

    # Expect an HTTP 404 exception (security through obscurity - not found instead of forbidden)
    with pytest.raises(HTTPException) as excinfo:
        create_project(request=mock_request, orm=orm_session, body=body)

    assert excinfo.value.status_code == 404
    assert excinfo.value.detail == "Organization not found"


@pytest.mark.asyncio
async def test_update_project(mock_request, orm_session, test_project):
    """Test updating a project's name and environment."""

    # Create the update body
    body = ProjectUpdateSchema(name="Updated Project Name", environment=Environment.production.value)

    # Execute the update
    result = update_project(request=mock_request, project_id=str(test_project.id), orm=orm_session, body=body)

    # Verify the updates were applied
    assert result.name == body.name
    assert result.environment == body.environment

    # Refresh the session to get the latest data
    orm_session.expire_all()

    # Verify the database was updated
    updated_project = orm_session.query(ProjectModel).filter_by(id=test_project.id).one()
    assert updated_project.name == body.name
    assert updated_project.environment == Environment.production


@pytest.mark.asyncio
async def test_update_project_not_admin(mock_request, orm_session, test_project):
    """Test updating a project without admin permissions."""
    # Get the current test project and its organization
    project_id = test_project.id
    org_id = test_project.org_id

    # Change the user's role to developer (not admin or owner)
    user_id = mock_request.state.session.user_id
    user_org = test_project.org.get_user_membership(str(user_id))

    if user_org:
        # Change the existing role to developer
        user_org.role = OrgRoles.developer
    else:
        # Create a new membership with developer role
        user_org = UserOrgModel(
            user_id=user_id, org_id=org_id, role=OrgRoles.developer, user_email="test@example.com"
        )
        orm_session.add(user_org)

    # Commit the changes
    orm_session.commit()

    # Create the update body
    body = ProjectUpdateSchema(name="Updated Project Name", environment=Environment.production.value)

    # Expect an HTTP 403 exception
    with pytest.raises(HTTPException) as excinfo:
        update_project(request=mock_request, project_id=str(project_id), orm=orm_session, body=body)

    assert excinfo.value.status_code == 403
    assert excinfo.value.detail == "You don't have permission to update this project"


@pytest.mark.asyncio
async def test_update_project_invalid_environment(mock_request, orm_session, test_project):
    """Test updating a project with an invalid environment."""
    # Create the update body with an invalid environment
    body = ProjectUpdateSchema(name="Updated Project Name", environment="invalid_environment")

    # Expect an HTTP 400 exception
    with pytest.raises(HTTPException) as excinfo:
        update_project(request=mock_request, project_id=str(test_project.id), orm=orm_session, body=body)

    assert excinfo.value.status_code == 400
    assert excinfo.value.detail == "Invalid environment"


@pytest.mark.asyncio
async def test_delete_project(mock_request, orm_session, test_user):
    """Test deleting a project."""
    # Create all the test data in this test
    org = OrgModel(name="Test Org for Delete")
    orm_session.add(org)
    orm_session.flush()

    # Create a user-org relationship with test_user fixture
    user_org = UserOrgModel(
        user_id=test_user.id, org_id=org.id, role=OrgRoles.owner, user_email=test_user.email
    )
    orm_session.add(user_org)
    orm_session.flush()

    # Create a project
    project = ProjectModel(name="Project to Delete", org_id=org.id, environment=Environment.development)
    orm_session.add(project)
    orm_session.flush()

    # Load relationships to ensure they're available
    project = (
        orm_session.query(ProjectModel)
        .options(orm.joinedload(ProjectModel.org).joinedload(OrgModel.users))
        .filter_by(id=project.id)
        .one()
    )

    # Call the endpoint function directly with the session
    result = delete_project(request=mock_request, project_id=str(project.id), orm=orm_session)

    # Verify the status response
    assert result.success is True
    assert result.message == "Project deleted successfully"

    projects = orm_session.query(ProjectModel).filter_by(id=project.id).all()
    assert len(projects) == 0


@pytest.mark.asyncio
async def test_delete_project_not_owner(mock_request, orm_session, test_user):
    """Test deleting a project without owner permissions."""
    # Create all the test data in this test
    org = OrgModel(name="Test Org for Non-Owner Delete")
    orm_session.add(org)
    orm_session.flush()

    # Create a user-org relationship with admin role (not owner) using test_user
    user_org = UserOrgModel(
        user_id=test_user.id,
        org_id=org.id,
        role=OrgRoles.admin,  # Admin role, not owner
        user_email=test_user.email,
    )
    orm_session.add(user_org)
    orm_session.flush()

    # Create a project
    project = ProjectModel(
        name="Project for Non-Owner Delete Test", org_id=org.id, environment=Environment.development
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

    # Expect an HTTP 403 exception
    with pytest.raises(HTTPException) as excinfo:
        delete_project(request=mock_request, project_id=str(project.id), orm=orm_session)

    assert excinfo.value.status_code == 403
    assert excinfo.value.detail == "Only organization owners can delete projects"


@pytest.mark.asyncio
async def test_create_project_limit(mock_request, orm_session, test_user):
    """Test creating a project when the organization has reached its project limit."""
    # Create a fresh organization with free plan (which has a project limit of 1)
    org = OrgModel(
        name="Test Org with Project Limit",
        prem_status=PremStatus.free,  # Free plan has a project limit of 1
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

    # Create a project (which takes up the only allowed project slot)
    project = ProjectModel(name="First Project", org_id=org.id, environment=Environment.development)
    orm_session.add(project)
    orm_session.commit()  # Commit to ensure it's persisted

    # Reload the org with all relationships
    org = OrgModel.get_by_id(orm_session, org.id)

    # Create the request body for a second project (which should exceed the limit)
    body = ProjectCreateSchema(
        name="Second Project", org_id=str(org.id), environment=Environment.development.value
    )

    # Expect an HTTP 403 exception due to project limit
    with pytest.raises(HTTPException) as excinfo:
        create_project(request=mock_request, orm=orm_session, body=body)

    assert excinfo.value.status_code == 403
    assert excinfo.value.detail == "Organization has reached it's project limit"

    # Verify no second project was created
    projects = orm_session.query(ProjectModel).filter_by(org_id=org.id).all()
    assert len(projects) == 1


@pytest.mark.asyncio
async def test_create_project_after_upgrade(mock_request, orm_session, test_user):
    """Test creating projects after upgrading from free to enterprise plan."""
    # Create a fresh organization with free plan (which has a project limit of 1)
    org = OrgModel(
        name="Test Org for Plan Upgrade",
        prem_status=PremStatus.free,  # Free plan has a project limit of 1
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

    # Create a project (using up the only allowed slot in the free plan)
    project = ProjectModel(name="First Project", org_id=org.id, environment=Environment.development)
    orm_session.add(project)
    orm_session.commit()

    # Upgrade the organization plan to enterprise (which has no project limit)
    org.prem_status = PremStatus.enterprise
    orm_session.commit()

    # Reload the org with all relationships
    org = OrgModel.get_by_id(orm_session, org.id)

    # Create the request body for a second project (which should now work)
    body = ProjectCreateSchema(
        name="Second Project", org_id=str(org.id), environment=Environment.development.value
    )

    # This should now succeed with the enterprise plan
    result = create_project(request=mock_request, orm=orm_session, body=body)

    # Verify the project was created with the right data
    assert result.name == body.name
    assert result.org_id == body.org_id
    assert result.api_key is not None

    # Verify we now have two projects in the database
    projects = orm_session.query(ProjectModel).filter_by(org_id=org.id).all()
    assert len(projects) == 2


@pytest.mark.asyncio
async def test_regenerate_api_key(mock_request, orm_session, test_user):
    """Test regenerating a project's API key."""
    # Create all the test data in this test
    org = OrgModel(name="Test Org for Regenerate Key")
    orm_session.add(org)
    orm_session.flush()

    # Create a user-org relationship with owner role using test_user
    user_org = UserOrgModel(
        user_id=test_user.id, org_id=org.id, role=OrgRoles.owner, user_email=test_user.email
    )
    orm_session.add(user_org)
    orm_session.flush()

    # Create a project with a specific API key
    initial_api_key = uuid.uuid4()
    project = ProjectModel(
        name="Project for Key Regeneration",
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

    # Save the original API key
    original_api_key = project.api_key

    # Call the endpoint function
    result = regenerate_api_key(request=mock_request, project_id=str(project.id), orm=orm_session)

    # Verify the response contains a new API key
    assert result.api_key != str(original_api_key)

    # Verify the database was updated
    updated_project = orm_session.query(ProjectModel).filter_by(id=project.id).one()
    assert str(updated_project.api_key) != str(original_api_key)
