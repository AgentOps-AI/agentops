"""
SQLAlchemy models for the opsboard application.

NOTE: This is a subset of models migrated from the Supabase implementation.
We're only implementing the core user and organization management features initially.
"""

from typing import Optional, TYPE_CHECKING
import enum
from dataclasses import dataclass
import uuid
from uuid import UUID
import sqlalchemy as model
from sqlalchemy import orm
from sqlalchemy.orm import joinedload, lazyload
from sqlalchemy.dialects.postgresql import JSONB
from agentops.common.environment import (
    FREEPLAN_MAX_USERS,
    FREEPLAN_MAX_PROJECTS,
)
from agentops.common.orm import BaseModel, require_loaded
from .environment import DEMO_ORG_ID
from sqlalchemy import func

if TYPE_CHECKING:
    from agentops.api.auth import JWTPayload


def normalize_uuid(id_: str | UUID) -> UUID:
    """Normalize value to a UUID."""
    return uuid.UUID(id_) if isinstance(id_, str) else id_


class OrgRoles(enum.Enum):
    """Role types for organization members"""

    # must match the database org_roles enum type (which is lowercase)
    owner = "owner"
    admin = "admin"
    developer = "developer"
    business_user = "business_user"


class PremStatus(enum.Enum):
    """Premium status types for organizations"""

    # must match the database org_roles enum type (which is lowercase)
    free = "free"
    pro = "pro"
    enterprise = "enterprise"


@dataclass
class PremStatusAttributes:
    """Attributes for each premium status"""

    # `None` indicates there is no limit

    max_users: int | None
    max_projects: int | None


class Environment(enum.Enum):
    """Environment types for projects"""

    # must match the database org_roles enum type (which is lowercase)
    production = "production"
    staging = "staging"
    development = "development"
    community = "community"


class AuthUserModel(BaseModel):
    """
    Model representing Supabase's built-in auth.users table.

    This model is provided for cases where auth.users access is absolutely necessary,
    as Supabase does not recommend we access it directly.

    This model is read-only to prevent modification.
    """

    __tablename__ = "users"
    __table_args__ = {"schema": "auth"}
    __mapper_args__ = {"confirm_deleted_rows": False}  # Make this model read-only

    def __setattr__(self, name, value):
        """Prevent modifications to auth.users table."""
        if hasattr(self, '_sa_instance_state') and self._sa_instance_state.persistent:
            raise RuntimeError("AuthUserModel is read-only. Do not modify auth.users table directly.")
        super().__setattr__(name, value)

    id = model.Column(model.UUID, primary_key=True)
    email = model.Column(model.String, nullable=True)
    created_at = model.Column(model.DateTime(timezone=True), nullable=True)
    # there are additional columns in auth.users that we don't reference here


class UserModel(BaseModel):
    """User model that maps to the users table"""

    __tablename__ = "users"
    __table_args__ = {"schema": "public"}

    # For SQLAlchemy ORM, just use UUID primary key without trying to validate the foreign key
    # The actual foreign key constraint exists in the database already
    id = model.Column(model.UUID, primary_key=True)
    full_name = model.Column(model.String, nullable=True)
    avatar_url = model.Column(model.String, nullable=True)
    billing_address = model.Column(JSONB, nullable=True)
    payment_method = model.Column(JSONB, nullable=True)
    email = model.Column(model.String, default="", nullable=False)
    survey_is_complete = model.Column(model.Boolean, default=False, nullable=False)

    orgs = orm.relationship("UserOrgModel", back_populates="user")
    invites = orm.relationship(
        "OrgInviteModel", foreign_keys="[OrgInviteModel.inviter_id]", back_populates="inviter_user"
    )
    auth_user = orm.relationship(
        "AuthUserModel",
        foreign_keys=[id],
        primaryjoin="UserModel.id == AuthUserModel.id",
        uselist=False,
        lazy="select",  # Allow lazy loading for billing_email property
    )

    def mark_survey_complete(self):
        self.survey_is_complete = True

    @property
    def billing_email(self) -> str | None:
        """Get the user's email from Supabase `auth.users` to ensure we use the canonical email."""
        # this performs a lazy load, but it's used infrequently so that's fine
        return self.auth_user.email if self.auth_user else None

    @classmethod
    def get_by_id(cls, orm: orm.Session, user_id: str | UUID) -> Optional['UserModel']:
        """Get a user by ID with relationships preloaded."""
        return (
            orm.query(cls)
            .options(
                joinedload(cls.orgs),
                joinedload(cls.invites),
            )
            .filter(cls.id == normalize_uuid(user_id))
            .first()
        )


class OrgModel(BaseModel):
    """Organization model that maps to the orgs table"""

    __tablename__ = "orgs"
    __table_args__ = {"schema": "public"}

    id = model.Column(model.UUID, primary_key=True, default=uuid.uuid4)
    name = model.Column(model.String, nullable=False)
    prem_status = model.Column(model.Enum(PremStatus), default=PremStatus.free, nullable=False)
    subscription_id = model.Column(model.String, nullable=True)

    users = orm.relationship("UserOrgModel", back_populates="org", cascade="all, delete-orphan")
    projects = orm.relationship("ProjectModel", back_populates="org")
    invites = orm.relationship("OrgInviteModel", back_populates="org", cascade="all, delete-orphan")

    def set_current_user(self, user_id: str | UUID) -> None:
        """
        Set the current user for this organization. THis is the user performing
        the request.

        This allows us to access `current_user_role` as a property later.
        """
        user_org = self.get_user_membership(user_id)
        self._current_user_role = user_org.role

    @property
    def current_user_role(self) -> OrgRoles:
        """Get the current user's role in this organization."""
        # this property helps us render this field in the response schema
        if not hasattr(self, "_current_user_role"):
            raise AttributeError("Current user role is not set. Call set_current_user() first.")

        return self._current_user_role

    @property
    def is_freeplan(self) -> bool:
        """Check if the organization is on a free plan."""
        return self.prem_status == PremStatus.free

    @property
    def current_member_count(self) -> int:
        """The number of users that are a member of this organization."""
        # Use optimized count if available
        if hasattr(self, '_member_count'):
            return self._member_count
        # this includes the count of invites, too, so we can prevent the admin
        # from over-inviting users
        if not hasattr(self, 'users') or not hasattr(self, 'invites'):
            raise AttributeError(
                "Member count not available. Use get_by_id or get_all_for_user to load relationships."
            )
        return len(self.users) + len(self.invites)

    @property
    def max_member_count(self) -> int | None:
        """The maximum number of users that can be a member of this organization."""
        return FREEPLAN_MAX_USERS if self.is_freeplan else None

    @property
    def current_project_count(self) -> int:
        """The number of projects that are a member of this organization."""
        # Use optimized count if available
        if hasattr(self, '_project_count'):
            return self._project_count
        if not hasattr(self, 'projects'):
            raise AttributeError(
                "Project count not available. Use get_by_id or get_all_for_user to load relationships."
            )
        return len(self.projects)

    @property
    def max_project_count(self) -> int | None:
        """The maximum number of projects that can be a member of this organization."""
        return FREEPLAN_MAX_PROJECTS if self.is_freeplan else None

    @property
    def paid_member_count(self) -> int:
        """Get count of members marked as paid."""
        # Use cached value if available (set by get_by_id_summary)
        if hasattr(self, '_paid_member_count'):
            return self._paid_member_count

        # If relationships are loaded, count only paid users
        if hasattr(self, 'users') and isinstance(self.users, list):
            return sum(1 for user_org in self.users if user_org.is_paid)

        # Fallback to database query for paid users only
        from sqlalchemy.orm import Session

        if self.id and hasattr(self, '_sa_instance_state'):
            orm = Session.object_session(self)
            if orm:
                return (
                    orm.query(UserOrgModel)
                    .filter(UserOrgModel.org_id == self.id, UserOrgModel.is_paid)
                    .count()
                )

        # Default fallback - at least the owner should be paid
        return 1

    @property
    def unpaid_member_count(self) -> int:
        """
        Get count of members not included in paid seats.
        This can be used in the future if we add granular control over who gets licensed
        """
        if hasattr(self, 'users') and isinstance(self.users, list):
            return sum(1 for user_org in self.users if not user_org.is_paid)

        from sqlalchemy.orm import Session

        if self.id and hasattr(self, '_sa_instance_state'):
            orm = Session.object_session(self)
            if orm:
                return (
                    orm.query(UserOrgModel)
                    .filter(UserOrgModel.org_id == self.id, ~UserOrgModel.is_paid)
                    .count()
                )
        return 0

    def create_user_membership(self, user_id: str | UUID, role: OrgRoles) -> 'UserOrgModel':
        """Add a user to this organization with the given role."""

        user_id = normalize_uuid(user_id)
        user_org = UserOrgModel(user_id=user_id, org_id=self.id, role=role)
        self.users.append(user_org)
        return user_org

    @require_loaded('users')
    def get_user_membership(self, user_id: str | UUID) -> Optional['UserOrgModel']:
        """Get a user's membership in this organization."""
        user_id = normalize_uuid(user_id)
        return next((user_org for user_org in self.users if user_org.user_id == user_id), None)

    def is_user_member(self, user_id: str | UUID) -> bool:
        """Check if a user is a member of this organization."""
        # If we have the current user role set from summary queries, use that
        if hasattr(self, '_current_user_role') and normalize_uuid(user_id) == normalize_uuid(
            getattr(self, '_current_user_id', user_id)
        ):
            return True
        return self.get_user_membership(user_id) is not None

    def is_user_admin_or_owner(self, user_id: str | UUID) -> bool:
        """Check if a user is an admin or owner of this organization."""
        # If we have the current user role set from summary queries, use that
        if hasattr(self, '_current_user_role') and normalize_uuid(user_id) == normalize_uuid(
            getattr(self, '_current_user_id', user_id)
        ):
            return self._current_user_role in [OrgRoles.owner, OrgRoles.admin]

        if membership := self.get_user_membership(user_id):
            return membership.role in [OrgRoles.owner, OrgRoles.admin]

        return False

    def is_user_owner(self, user_id: str | UUID) -> bool:
        """Check if a user is the owner of this organization."""
        # If we have the current user role set from summary queries, use that
        if hasattr(self, '_current_user_role') and normalize_uuid(user_id) == normalize_uuid(
            getattr(self, '_current_user_id', user_id)
        ):
            return self._current_user_role == OrgRoles.owner

        if membership := self.get_user_membership(user_id):
            return membership.role == OrgRoles.owner

        return False

    @classmethod
    def get_by_id(cls, orm: orm.Session, org_id: str | UUID) -> Optional['OrgModel']:
        """Get an organization by ID with relationships preloaded."""
        return (
            orm.query(cls)
            .options(
                joinedload(cls.users),
                joinedload(cls.invites),
                joinedload(cls.projects),
            )
            .filter(cls.id == normalize_uuid(org_id))
            .first()
        )

    @classmethod
    def get_all_for_user(cls, orm: orm.Session, user_id: str | UUID) -> Optional[list['OrgModel']]:
        """Get all organizations for a user with relationships preloaded."""
        orgs = (
            orm.query(cls)
            .options(
                joinedload(cls.users),
                joinedload(cls.invites),
                joinedload(cls.projects),
            )
            .join(UserOrgModel, UserOrgModel.org_id == cls.id)
            .filter(UserOrgModel.user_id == normalize_uuid(user_id))
            .filter(cls.id != DEMO_ORG_ID)  # TODO hard-code demo org and delete these rows
            .all()
        )
        for org in orgs:
            # populate current user so `org.current_user_role` is available
            org.set_current_user(user_id)
        return orgs

    @classmethod
    def get_all_for_user_summary(cls, orm: orm.Session, user_id: str | UUID) -> list['OrgModel']:
        """
        Get all organizations for a user with only summary data.

        This method returns orgs with counts pre-calculated, avoiding the need
        to load all related records.
        """
        from sqlalchemy import func

        user_id = normalize_uuid(user_id)

        # First, get all orgs for the user with their role
        orgs_with_roles = (
            orm.query(cls, UserOrgModel.role)
            .join(UserOrgModel, UserOrgModel.org_id == cls.id)
            .filter(UserOrgModel.user_id == user_id)
            .filter(cls.id != DEMO_ORG_ID)
            .all()
        )

        if not orgs_with_roles:
            return []

        # Extract org IDs for batch queries
        org_ids = [org.id for org, _ in orgs_with_roles]

        # Batch query for user counts
        user_counts = dict(
            orm.query(UserOrgModel.org_id, func.count(UserOrgModel.user_id))
            .filter(UserOrgModel.org_id.in_(org_ids))
            .group_by(UserOrgModel.org_id)
            .all()
        )

        # Batch query for invite counts
        invite_counts = dict(
            orm.query(OrgInviteModel.org_id, func.count(OrgInviteModel.invitee_email))
            .filter(OrgInviteModel.org_id.in_(org_ids))
            .group_by(OrgInviteModel.org_id)
            .all()
        )

        # Batch query for project counts
        project_counts = dict(
            orm.query(ProjectModel.org_id, func.count(ProjectModel.id))
            .filter(ProjectModel.org_id.in_(org_ids))
            .group_by(ProjectModel.org_id)
            .all()
        )

        # Assemble the results
        orgs = []
        for org, role in orgs_with_roles:
            # Set the current user role
            org._current_user_role = role
            org._current_user_id = user_id

            # Get counts from batch results
            user_count = user_counts.get(org.id, 0)
            invite_count = invite_counts.get(org.id, 0)
            project_count = project_counts.get(org.id, 0)

            # Store counts as private attributes
            org._member_count = user_count + invite_count
            org._user_count = user_count  # Store user count separately for billing
            org._invite_count = invite_count  # Store invite count separately
            org._project_count = project_count

            orgs.append(org)

        return orgs

    @classmethod
    def get_by_id_summary(
        cls, orm: orm.Session, org_id: str | UUID, user_id: str | UUID
    ) -> Optional['OrgModel']:
        """
        Get an organization by ID with summary data only.
        Returns org with current user role but without loading all relationships.
        """
        from sqlalchemy import func

        org_id = normalize_uuid(org_id)
        user_id = normalize_uuid(user_id)

        # Get org with user role
        result = (
            orm.query(cls, UserOrgModel.role)
            .join(UserOrgModel, (UserOrgModel.org_id == cls.id) & (UserOrgModel.user_id == user_id))
            .filter(cls.id == org_id)
            .first()
        )

        if result:
            org, role = result
            org._current_user_role = role
            org._current_user_id = user_id

            # Calculate counts separately
            user_count = (
                orm.query(func.count(UserOrgModel.user_id)).filter(UserOrgModel.org_id == org.id).scalar()
                or 0
            )
            invite_count = (
                orm.query(func.count(OrgInviteModel.invitee_email))
                .filter(OrgInviteModel.org_id == org.id)
                .scalar()
                or 0
            )
            project_count = (
                orm.query(func.count(ProjectModel.id)).filter(ProjectModel.org_id == org.id).scalar() or 0
            )

            # Calculate paid member count separately
            paid_user_count = (
                orm.query(func.count(UserOrgModel.user_id))
                .filter(UserOrgModel.org_id == org.id, UserOrgModel.is_paid)
                .scalar()
                or 0
            )

            org._member_count = user_count + invite_count
            org._user_count = user_count  # Store user count separately for billing
            org._invite_count = invite_count  # Store invite count separately
            org._project_count = project_count
            org._paid_member_count = paid_user_count  # Store paid member count
            return org

        return None

    @classmethod
    def get_all_for_user_optimized(cls, orm: orm.Session, user_id: str | UUID) -> list['OrgModel']:
        """Deprecated: Use get_all_for_user_summary instead."""
        return cls.get_all_for_user_summary(orm, user_id)

    @classmethod
    def get_by_id_for_detail(cls, orm: orm.Session, org_id: str | UUID) -> Optional['OrgModel']:
        """
        Get an organization by ID optimized for detail view.
        Only loads users (needed for detail view), not projects or invites.
        """

        org = (
            orm.query(cls)
            .options(
                joinedload(cls.users),
                # Use lazyload to prevent automatic loading but avoid errors
                lazyload(cls.projects),
                lazyload(cls.invites),
            )
            .filter(cls.id == normalize_uuid(org_id))
            .first()
        )

        if org:
            # Calculate counts without loading all data
            from sqlalchemy import func

            invite_count = (
                orm.query(func.count(OrgInviteModel.invitee_email))
                .filter(OrgInviteModel.org_id == org.id)
                .scalar()
            )
            project_count = (
                orm.query(func.count(ProjectModel.id)).filter(ProjectModel.org_id == org.id).scalar()
            )

            org._member_count = len(org.users) + invite_count
            org._user_count = len(org.users)  # Store user count separately for billing
            org._invite_count = invite_count  # Store invite count separately
            org._project_count = project_count

        return org

    @classmethod
    def get_by_id_for_permission_check(
        cls, orm: orm.Session, org_id: str | UUID, user_id: str | UUID
    ) -> Optional['OrgModel']:
        """
        Get an organization by ID with only the current user's membership loaded.
        Optimized for permission checks - doesn't load all users/invites/projects.
        """
        # Use the summary method which already handles this efficiently
        return cls.get_by_id_summary(orm, org_id, user_id)


class UserOrgModel(BaseModel):
    """Model that maps to the user_orgs table (many-to-many)"""

    __tablename__ = "user_orgs"
    __table_args__ = {"schema": "public"}

    user_id = model.Column(model.UUID, model.ForeignKey("public.users.id"), primary_key=True)
    org_id = model.Column(model.UUID, model.ForeignKey("public.orgs.id"), primary_key=True)
    role = model.Column(
        model.Enum(OrgRoles, name="org_roles", create_constraint=False, native_enum=True),
        default=OrgRoles.owner,
    )
    user_email = model.Column(model.String)
    is_paid = model.Column(model.Boolean, default=False)

    user = orm.relationship("UserModel", back_populates="orgs")
    org = orm.relationship("OrgModel", back_populates="users")


class OrgInviteModel(BaseModel):
    """Model that maps to the org_invites table."""

    __tablename__ = "org_invites"
    __table_args__ = {"schema": "public"}

    inviter_id = model.Column(model.UUID, model.ForeignKey("public.users.id"), nullable=False)
    invitee_email = model.Column(model.String, primary_key=True)
    org_id = model.Column(model.UUID, model.ForeignKey("public.orgs.id"), primary_key=True)
    role = model.Column(
        model.Enum(OrgRoles, name="org_roles", create_constraint=False, native_enum=True),
        nullable=False,
    )
    org_name = model.Column(model.String, nullable=False)
    created_at = model.Column(model.DateTime(timezone=True), default=model.func.now())

    inviter_user = orm.relationship("UserModel", foreign_keys=[inviter_id], back_populates="invites")
    org = orm.relationship("OrgModel", back_populates="invites")


class SparseFieldException(ValueError):
    """Exception raised when trying to access a field that is not available in the sparse model."""

    def __init__(self, field_name: str):
        super().__init__(
            f"`{field_name}` is not available in sparse model. Call `get_project()` to load the full model."
        )

    @classmethod
    def raise_for_field(cls, field_name: str):
        raise cls(field_name)


class BaseProjectModel:
    """Base model for projects that defines common attributes and interface."""

    is_sparse: bool
    id: UUID
    api_key: UUID

    @property
    def is_freeplan(self) -> bool:
        """Check if the project is on a free plan."""
        raise NotImplementedError("Subclasses must implement is_freeplan")

    def get_project(self, orm: "orm.Session") -> Optional["ProjectModel"]:
        """Get the full project model from the database."""
        raise NotImplementedError("Subclasses must implement get_project")


class ProjectModel(BaseProjectModel, BaseModel):
    """Model that maps to the projects table"""

    __tablename__ = "projects"
    __table_args__ = {"schema": "public"}

    is_sparse = False
    id = model.Column(model.UUID, primary_key=True, default=uuid.uuid4)
    org_id = model.Column(model.UUID, model.ForeignKey("public.orgs.id"), nullable=False)
    api_key = model.Column(model.UUID, unique=True, default=uuid.uuid4)
    name = model.Column(model.String, nullable=False)
    environment = model.Column(model.Enum(Environment), default=Environment.development, nullable=False)

    org = orm.relationship("OrgModel", back_populates="projects")

    @property
    @require_loaded('org')
    def is_freeplan(self) -> bool:
        """Check if the organization is on a pro plan."""
        return self.org.is_freeplan

    def get_project(self, orm: orm.Session) -> Optional["ProjectModel"]:
        """For ProjectModel, return self since it's already the full model."""
        return self

    @classmethod
    def get_by_id(cls, orm: orm.Session, project_id: str | UUID) -> Optional['ProjectModel']:
        """Get a project by ID with org and necessary relationships preloaded."""
        # This loads org.users, org.invites, and org.projects relationships which are
        # needed when returning a `ProjectResponse` in these view functions:
        # - get_project
        # - create_project
        # - update_project
        # - regenerate_api_key
        # TODO: Consider optimizing with count queries instead of loading full relationships
        # when we only need counts for org.current_member_count and org.current_project_count.
        return (
            orm.query(cls)
            .filter(cls.id == normalize_uuid(project_id))
            .options(
                joinedload(cls.org).joinedload(OrgModel.users),
                joinedload(cls.org).joinedload(OrgModel.invites),
                joinedload(cls.org).joinedload(OrgModel.projects),
            )
            .first()
        )

    @classmethod
    def get_by_api_key(cls, orm: orm.Session, api_key: str | UUID) -> Optional['ProjectModel']:
        """Get a project by API key with org and necessary relationships preloaded."""
        return (
            orm.query(cls)
            .filter(cls.api_key == normalize_uuid(api_key))
            .options(
                joinedload(cls.org).joinedload(OrgModel.users),
                joinedload(cls.org).joinedload(OrgModel.invites),
                joinedload(cls.org).joinedload(OrgModel.projects),
            )
            .first()
        )

    @classmethod
    def get_all_for_user(cls, orm: orm.Session, user_id: str | UUID) -> list['ProjectModel']:
        """Get all projects the user has access to across all organizations they belong to."""
        projects = (
            orm.query(cls)
            .join(OrgModel, cls.org_id == OrgModel.id)
            .join(
                UserOrgModel,
                UserOrgModel.org_id == OrgModel.id,
            )
            .filter(UserOrgModel.user_id == normalize_uuid(user_id))
            .filter(OrgModel.id != DEMO_ORG_ID)  # TODO hard-code demo org and delete these rows
            .options(
                joinedload(cls.org).joinedload(OrgModel.users),
                joinedload(cls.org).joinedload(OrgModel.invites),
                joinedload(cls.org).joinedload(OrgModel.projects),
            )
            .all()
        )

        # Set the current user for each project's org
        for project in projects:
            project.org.set_current_user(user_id)

        return projects

    @classmethod
    def get_all_for_user_optimized(cls, orm: orm.Session, user_id: str | UUID) -> list['ProjectModel']:
        """
        Get all projects the user has access to across all organizations they belong to.

        Optimized version that only loads minimal data needed for project summaries.
        This avoids loading all users, invites, and projects for each organization.
        """
        # Use a single query with minimal joins
        projects = (
            orm.query(cls)
            .join(OrgModel, cls.org_id == OrgModel.id)
            .join(UserOrgModel, UserOrgModel.org_id == OrgModel.id)
            .filter(UserOrgModel.user_id == normalize_uuid(user_id))
            .filter(OrgModel.id != DEMO_ORG_ID)
            .options(
                # Only load the org relationship itself, not all its relationships
                joinedload(cls.org),
                # Only load the specific user's membership for current_user_role
                joinedload(cls.org).joinedload(OrgModel.users).load_only(UserOrgModel.role),
            )
            .all()
        )

        # Set the current user for each project's org with minimal overhead
        for project in projects:
            # Manually set the user's role without loading all org members
            user_org = next((uo for uo in project.org.users if uo.user_id == normalize_uuid(user_id)), None)
            if user_org:
                project.org._current_user_role = user_org.role

        return projects


class SparseProjectModel(BaseProjectModel):
    """
    Sparse model for projects that is typically populated by a JWT token.

    In contexts where we only need the cache fields available inside the JWT, this
    let's us save some db overhead and still reference a typed project object.
    """

    is_sparse = True
    org_id = property(lambda self: SparseFieldException.raise_for_field("org_id"))
    name = property(lambda self: SparseFieldException.raise_for_field("name"))
    environment = property(lambda self: SparseFieldException.raise_for_field("environment"))
    org = property(lambda self: SparseFieldException.raise_for_field("org"))
    _prem_status: PremStatus

    def __init__(self, id: str | UUID, api_key: str | UUID, prem_status: str | PremStatus):
        self.id = normalize_uuid(id)
        self.api_key = normalize_uuid(api_key)
        self._prem_status = PremStatus(prem_status) if isinstance(prem_status, str) else prem_status

    @property
    def is_freeplan(self) -> bool:
        """Check if the project is on a free plan."""
        return self._prem_status == PremStatus.free

    def get_project(self, orm: orm.Session) -> Optional[ProjectModel]:
        """Get the full project model from the database."""
        return ProjectModel.get_by_id(orm, self.id)

    @classmethod
    def from_auth_payload(cls, token: "JWTPayload") -> "SparseProjectModel":
        """
        Create a SparseProjectModel from a JWT token.
        """
        return cls(
            id=token.project_id,
            api_key=token.api_key,
            prem_status=token.project_prem_status,
        )


class BillingAuditLog(BaseModel):
    __tablename__ = "billing_audit_logs"

    id = model.Column(model.UUID, primary_key=True, default=uuid.uuid4)
    org_id = model.Column(model.UUID, model.ForeignKey("public.orgs.id"), nullable=False)
    user_id = model.Column(model.UUID, model.ForeignKey("public.users.id"), nullable=True)
    action = model.Column(
        model.String, nullable=False
    )  # 'seats_updated', 'member_licensed', 'member_unlicensed'
    details = model.Column(model.JSON, nullable=False)  # JSON with before/after values
    created_at = model.Column(model.DateTime, default=func.now())


class WebhookEvent(BaseModel):
    """Model for tracking processed webhook events to ensure idempotency"""

    __tablename__ = "webhook_events"

    event_id = model.Column(model.String, primary_key=True)
    processed_at = model.Column(model.DateTime, default=func.now())


class BillingPeriod(BaseModel):
    """Model for billing period snapshots used in dashboard"""

    __tablename__ = "billing_periods"

    id = model.Column(model.UUID, primary_key=True, default=uuid.uuid4)
    org_id = model.Column(model.UUID, model.ForeignKey("public.orgs.id"), nullable=False)
    period_start = model.Column(model.DateTime, nullable=False)
    period_end = model.Column(model.DateTime, nullable=False)
    stripe_invoice_id = model.Column(model.String(255), nullable=True)

    # Costs breakdown (stored as cents)
    seat_cost = model.Column(model.Integer, nullable=False, default=0)
    seat_count = model.Column(model.Integer, nullable=False, default=0)

    # Usage costs (JSON for extensibility)
    usage_costs = model.Column(JSONB, nullable=False, default={})  # {"tokens": 1500, "spans": 2000}
    usage_quantities = model.Column(JSONB, nullable=False, default={})  # {"tokens": 5000000, "spans": 125000}

    total_cost = model.Column(model.Integer, nullable=False, default=0)
    status = model.Column(model.String(20), default='pending')  # 'pending', 'invoiced', 'paid'
    invoiced_at = model.Column(model.DateTime, nullable=True)
    created_at = model.Column(model.DateTime, default=func.now())

    __table_args__ = (model.UniqueConstraint('org_id', 'period_start', name='_org_period_uc'),)
