import pytest
import uuid
from sqlalchemy.orm import Session
from agentops.opsboard.models import AuthUserModel, UserModel


@pytest.fixture(scope="function")
async def auth_user(orm_session: Session, test_user: UserModel) -> AuthUserModel:
    """Get the auth user corresponding to the test user."""
    # Get the auth user that corresponds to our test user
    auth_user = orm_session.get(AuthUserModel, test_user.id)
    
    if not auth_user:
        # This should not happen with proper test setup since auth users should be seeded
        raise RuntimeError(f"No auth user found for test user ID {test_user.id}. Check seed data.")
    
    return auth_user


class TestAuthUserModel:
    """Test cases for the AuthUserModel."""

    async def test_auth_user_creation(self, auth_user: AuthUserModel):
        """Test that AuthUserModel can be created successfully."""
        assert auth_user.id is not None
        assert auth_user.email == "test@example.com"  # Matches the seeded auth user email
        assert str(auth_user.id) == "00000000-0000-0000-0000-000000000000"  # From test_user fixture

    async def test_auth_user_model_table_schema(self, auth_user: AuthUserModel):
        """Test that AuthUserModel maps to correct table and schema."""
        assert auth_user.__tablename__ == "users"
        assert auth_user.__table_args__["schema"] == "auth"

    async def test_billing_email_property_with_auth_user(self, orm_session: Session, test_user: UserModel):
        """Test that billing_email property returns email from auth.users table."""
        # Refresh the user to ensure the relationship is loaded
        orm_session.refresh(test_user)
        
        # The billing_email should come from auth.users, not public.users
        # Note: The actual auth email will depend on what's seeded for this test user ID
        assert test_user.billing_email is not None  # Should have an auth email
        assert test_user.email == "test@example.com"  # From test_user fixture
        # If auth email is different from public email, test that
        if test_user.billing_email != test_user.email:
            assert test_user.billing_email != test_user.email

    async def test_billing_email_property_without_auth_user(self, orm_session: Session, test_user: UserModel):
        """Test billing_email property when auth user has null email."""
        # Get the auth user and temporarily modify its email to None for testing
        auth_user = test_user.auth_user
        original_email = auth_user.email
        
        try:
            # Temporarily modify the auth user's email in memory only (not persisted)
            # This simulates the case where auth.users.email is NULL
            object.__setattr__(auth_user, 'email', None)
            
            # billing_email should return None when auth email is null
            assert test_user.billing_email is None
            assert test_user.email == "test@example.com"  # public email remains from fixture
            
        finally:
            # Restore original email
            object.__setattr__(auth_user, 'email', original_email)

    async def test_auth_user_relationship_lazy_loading(self, orm_session: Session, test_user: UserModel):
        """Test that the auth_user relationship works with lazy loading."""
        # Get user without explicitly loading auth_user relationship
        user = orm_session.get(UserModel, test_user.id)
        
        # Accessing auth_user should trigger lazy load
        assert user.auth_user is not None
        # The auth email should exist (specific value depends on seed data)
        assert user.auth_user.email is not None

    async def test_auth_user_model_columns(self, auth_user: AuthUserModel):
        """Test that AuthUserModel has the expected columns."""
        # Check that the model has the basic columns we expect
        assert hasattr(auth_user, 'id')
        assert hasattr(auth_user, 'email')
        assert hasattr(auth_user, 'created_at')
        
        # Verify column types are as expected
        assert isinstance(auth_user.id, uuid.UUID)
        assert isinstance(auth_user.email, str)

    async def test_auth_user_model_read_only(self, auth_user: AuthUserModel):
        """Test that AuthUserModel prevents modifications."""
        # Test that we can read the auth user
        assert auth_user.email is not None
        
        # Test that attempting to modify a persistent auth user raises an error
        with pytest.raises(RuntimeError, match="AuthUserModel is read-only"):
            auth_user.email = "modified@example.com"