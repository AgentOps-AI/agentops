import pytest
import uuid
from sqlalchemy.orm import Session
from agentops.opsboard.models import UserModel

__all__ = [
    "test_user",
    "test_user2",
    "test_user3",
]


@pytest.fixture(scope="session")
async def test_user(orm_session: Session) -> UserModel:
    """Create a test user that persists for the entire test session.
    This user corresponds to the first auth.users entry with ID 00000000-0000-0000-0000-000000000000."""

    user_id = uuid.UUID("00000000-0000-0000-0000-000000000000")

    # Check if user already exists
    existing_user = orm_session.query(UserModel).filter_by(id=user_id).first()
    if existing_user:
        return existing_user

    # Create a new test user
    user = UserModel(id=user_id, full_name="Test User", email="test@example.com", survey_is_complete=False)

    orm_session.add(user)
    orm_session.commit()

    return user


@pytest.fixture(scope="session")
async def test_user2(orm_session: Session) -> UserModel:
    """Create a second test user that persists for the entire test session.
    This user corresponds to the second auth.users entry with ID 00000000-0000-0000-0000-000000000001."""

    user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

    # Check if user already exists
    existing_user = orm_session.query(UserModel).filter_by(id=user_id).first()
    if existing_user:
        return existing_user

    # Create a new test user
    user = UserModel(id=user_id, full_name="Test User 2", email="test2@example.com", survey_is_complete=False)

    orm_session.add(user)
    orm_session.commit()

    return user


@pytest.fixture(scope="session")
async def test_user3(orm_session: Session) -> UserModel:
    """Create a third test user that persists for the entire test session.
    This user corresponds to a third auth.users entry with ID 00000000-0000-0000-0000-000000000002."""

    user_id = uuid.UUID("00000000-0000-0000-0000-000000000002")

    # Check if user already exists
    existing_user = orm_session.query(UserModel).filter_by(id=user_id).first()
    if existing_user:
        return existing_user

    # Create a new test user
    user = UserModel(id=user_id, full_name="Test User 3", email="test3@example.com", survey_is_complete=False)

    orm_session.add(user)
    orm_session.commit()

    return user
