import pytest
from sqlalchemy import orm

from agentops.opsboard.models import (
    OrgModel,
    UserOrgModel,
    ProjectModel,
    OrgRoles,
    Environment,
    PremStatus,
)

__all__ = [
    'test_org',
    'test_org_prem',
    'test_user_org_member',
    'test_user_org_owner',
    'test_user_org_owner_prem',
    'test_project',
]


@pytest.fixture
async def test_org(orm_session) -> OrgModel:
    """Create a test organization with no membership."""
    # Create an org
    org = OrgModel(name="Test Org for Projects")
    orm_session.add(org)
    orm_session.flush()  # Use flush instead of commit to keep transaction open

    # Return the org
    return org


@pytest.fixture
async def test_org_prem(orm_session) -> OrgModel:
    """Create a test organization with no membership."""
    # Create an org
    org = OrgModel(
        name="Test Premium Org for Projects",
        prem_status=PremStatus.pro,
    )
    orm_session.add(org)
    orm_session.flush()  # Use flush instead of commit to keep transaction open

    # Return the org
    return org


@pytest.fixture
async def test_user_org_member(orm_session, test_org, test_user) -> OrgModel:
    """Create a user-org relationship with member role."""
    # Create a user-org relationship with the test user as member
    user_org = UserOrgModel(
        user_id=test_user.id,
        org_id=test_org.id,
        role=OrgRoles.developer,
        user_email=test_user.email,
    )
    orm_session.add(user_org)
    orm_session.commit()

    # Return the org with users loaded
    org = orm_session.query(OrgModel).options(orm.joinedload(OrgModel.users)).filter_by(id=test_org.id).one()

    return org


@pytest.fixture
async def test_user_org_owner(orm_session, test_org, test_user) -> OrgModel:
    """Create a user-org relationship with owner role."""
    # Create a user-org relationship with the test user as owner
    user_org = UserOrgModel(
        user_id=test_user.id,
        org_id=test_org.id,
        role=OrgRoles.owner,
        user_email=test_user.email,
    )
    orm_session.add(user_org)
    orm_session.commit()  # Commit to ensure persistence

    # Return the org with users loaded
    org = orm_session.query(OrgModel).options(orm.joinedload(OrgModel.users)).filter_by(id=test_org.id).one()

    return org


@pytest.fixture
async def test_user_org_owner_prem(orm_session, test_org_prem, test_user) -> OrgModel:
    """Create a user-org relationship with owner role and premium plan."""
    # Create a user-org relationship with the test user as owner
    user_org = UserOrgModel(
        user_id=test_user.id,
        org_id=test_org_prem.id,
        role=OrgRoles.owner,
        user_email=test_user.email,
    )
    orm_session.add(user_org)
    orm_session.commit()

    # Return the org with users loaded
    org = (
        orm_session.query(OrgModel)
        .options(orm.joinedload(OrgModel.users))
        .filter_by(id=test_org_prem.id)
        .one()
    )

    return org


@pytest.fixture
async def test_project(orm_session, test_user_org_owner) -> ProjectModel:
    """Create a test project for the test organization with owner relationship."""
    # We use test_user_org_owner which gives us an org with the test user as owner
    org = test_user_org_owner

    project = ProjectModel(
        name="Test Project",
        org_id=org.id,
        environment=Environment.development,
    )
    orm_session.add(project)
    orm_session.commit()  # Commit to ensure persistence

    # Return the project with org relationship loaded
    project = (
        orm_session.query(ProjectModel)
        .options(orm.joinedload(ProjectModel.org).joinedload(OrgModel.users))
        .filter_by(id=project.id)
        .one()
    )

    return project
