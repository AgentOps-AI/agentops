import pytest

from agentops.opsboard.views.users import get_user, update_user, update_user_survey_complete
from agentops.opsboard.schemas import UserUpdateSchema, UserResponse, StatusResponse


async def test_get_user(mock_request, orm_session, test_user):
    """Test getting user details."""
    # Call the view function
    response = get_user(request=mock_request, orm=orm_session)

    # Verify response
    assert isinstance(response, UserResponse)
    assert response.full_name == "Test User"
    assert response.email == "test@example.com"
    assert response.survey_is_complete is False


async def test_update_user(mock_request, orm_session, test_user):
    """Test updating user details."""
    # Create update data
    update_data = UserUpdateSchema(full_name="Updated Name", survey_is_complete=True)

    # Call the view function
    response = update_user(request=mock_request, orm=orm_session, body=update_data)

    # Verify response
    assert isinstance(response, UserResponse)
    assert response.full_name == "Updated Name"
    assert response.survey_is_complete is True

    # Verify database was updated
    updated_user = orm_session.get_one(type(test_user), test_user.id)
    assert updated_user.full_name == "Updated Name"
    assert updated_user.survey_is_complete is True


async def test_update_user_survey_complete(mock_request, orm_session, test_user):
    """Test marking the user survey as complete."""
    # Reset survey_is_complete to False for this test
    test_user.survey_is_complete = False
    orm_session.commit()

    # Call the view function
    response = update_user_survey_complete(request=mock_request, orm=orm_session)

    # Verify response
    assert isinstance(response, StatusResponse)
    assert response.success is True
    assert "complete" in response.message.lower()

    # Verify database was updated
    updated_user = orm_session.get_one(type(test_user), test_user.id)
    assert updated_user.survey_is_complete is True


async def test_get_user_not_found(mock_request, orm_session, monkeypatch):
    """Test getting a user that doesn't exist."""
    # Mock UserModel.get_by_id to return None
    from agentops.opsboard.models import UserModel

    monkeypatch.setattr(UserModel, 'get_by_id', lambda *args, **kwargs: None)

    # Call the view function and expect an exception
    with pytest.raises(Exception):
        get_user(request=mock_request, orm=orm_session)


async def test_update_user_not_found(mock_request, orm_session, monkeypatch):
    """Test updating a user that doesn't exist."""
    # Mock UserModel.get_by_id to return None
    from agentops.opsboard.models import UserModel

    monkeypatch.setattr(UserModel, 'get_by_id', lambda *args, **kwargs: None)

    # Call the view function and expect an exception
    with pytest.raises(Exception):
        update_user(request=mock_request, orm=orm_session, body=UserUpdateSchema(full_name="Test"))


async def test_update_user_survey_complete_not_found(mock_request, orm_session, monkeypatch):
    """Test marking survey complete for a user that doesn't exist."""
    # Mock UserModel.get_by_id to return None
    from agentops.opsboard.models import UserModel

    monkeypatch.setattr(UserModel, 'get_by_id', lambda *args, **kwargs: None)

    # Call the view function and expect an exception
    with pytest.raises(Exception):
        update_user_survey_complete(request=mock_request, orm=orm_session)
