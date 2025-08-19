import pydantic
from enum import Enum
from uuid import UUID
from typing import Optional


def uuid_to_str(v) -> str:
    """Convert UUID to string for Pydantic models."""
    if isinstance(v, UUID):
        return str(v)
    return v


class BaseSchema(pydantic.BaseModel):
    """
    Base schema type intended to be used for creating input schemas.
    """

    pass


class BaseResponse(BaseSchema):
    """
    Base response type intended to be directly populated by a sqlalchemy model.
    """

    model_config = pydantic.ConfigDict(
        from_attributes=True,
    )


class StatusResponse(BaseResponse):
    """
    Status response type intended to be used for simple success/failure responses.
    """

    success: bool = True
    message: str | None = None


class UserResponse(BaseResponse):
    """
    User response model.
    """

    id: str
    full_name: str | None
    avatar_url: str | None
    billing_address: dict | None
    payment_method: dict | None
    email: str | None
    survey_is_complete: bool | None

    @pydantic.field_validator("id", mode="before")
    @classmethod
    def validate_uuid(cls, v):
        return uuid_to_str(v)


class UserUpdateSchema(BaseSchema):
    """
    User update schema.
    """

    full_name: str | None = None
    avatar_url: str | None = None
    billing_address: dict | None = None
    payment_method: dict | None = None
    email: str | None = None
    survey_is_complete: bool | None = None


class UserOrgResponse(BaseResponse):
    """
    User-organization relationship information including role.
    """

    user_id: str
    org_id: str
    role: str
    user_email: str | None
    is_paid: bool = False  # Whether this member counts against paid seats

    @pydantic.field_validator("user_id", "org_id", mode="before")
    @classmethod
    def validate_uuid(cls, v):
        return uuid_to_str(v)


class OrgResponse(BaseResponse):
    """
    Organization response model.
    This contains fields which live directly on the OrgModel.
    """

    id: str
    name: str
    prem_status: str
    subscription_id: str | None = None
    subscription_end_date: int | None = None
    subscription_start_date: int | None = None
    subscription_cancel_at_period_end: bool | None = None
    current_user_role: str | None = None
    current_member_count: int | None = None
    max_member_count: int | None = None
    current_project_count: int | None = None
    max_project_count: int | None = None
    paid_member_count: Optional[int] = None

    @pydantic.field_validator("id", mode="before")
    @classmethod
    def validate_uuid(cls, v):
        return uuid_to_str(v)

    @pydantic.field_validator("current_user_role", mode="before")
    @classmethod
    def validate_current_user_role_enum(cls, v):
        """Convert the role Enum to a string."""
        return v.value if isinstance(v, Enum) else v

    @pydantic.field_validator("prem_status", mode="before")
    @classmethod
    def validate_prem_status_enum(cls, v):
        """Convert the prem_status Enum to a string."""
        return v.value if isinstance(v, Enum) else v


class OrgDetailResponse(OrgResponse):
    """
    Detailed organization response that includes user information.
    Used for single organization view.
    """

    users: list[UserOrgResponse]

    @pydantic.field_validator("users", mode="before")
    @classmethod
    def validate_users(cls, v):
        if not v:
            return []
        return v


class OrgCreateSchema(BaseSchema):
    """
    Schema for creating an organization.
    """

    name: str


class OrgUpdateSchema(BaseSchema):
    """
    Schema for updating an organization.
    """

    name: str


class OrgInviteSchema(BaseSchema):
    """
    Schema for inviting a user to an organization.
    Email is used to identify the user, and role specifies their permissions level.
    """

    email: str
    role: str


class OrgInviteResponse(BaseResponse):
    """
    Organization invite response model.
    """

    inviter_id: str
    invitee_email: str
    org_id: str
    role: str
    org_name: str
    created_at: str | None = None

    @pydantic.field_validator("inviter_id", "org_id", mode="before")
    @classmethod
    def validate_uuid(cls, v):
        return uuid_to_str(v)

    @pydantic.field_validator("created_at", mode="before")
    @classmethod
    def validate_created_at(cls, v):
        """Convert datetime to string."""
        if v is None:
            return None
        return v.isoformat() if hasattr(v, 'isoformat') else str(v)


class OrgInviteDetailResponse(BaseResponse):
    """
    Detailed organization invite response model for organization admin view.
    Includes additional information like inviter email and user existence status.
    """

    invitee_email: str
    inviter_email: str
    role: str
    org_id: str
    org_name: str
    created_at: str | None = None
    user_exists: bool

    @pydantic.field_validator("org_id", mode="before")
    @classmethod
    def validate_uuid(cls, v):
        return uuid_to_str(v)

    @pydantic.field_validator("created_at", mode="before")
    @classmethod
    def validate_created_at(cls, v):
        """Convert datetime to string."""
        if v is None:
            return None
        return v.isoformat() if hasattr(v, 'isoformat') else str(v)


class OrgMemberRemoveSchema(BaseSchema):
    """
    Schema for removing a user from an organization.
    """

    user_id: str


class OrgMemberRoleSchema(BaseSchema):
    """
    Schema for changing a user's role in an organization.
    """

    user_id: str
    role: str


class ValidateDiscountCodeBody(BaseSchema):
    """
    Schema for validating a discount code (promotion code or coupon ID).
    """

    discount_code: str


class ValidateDiscountCodeResponse(BaseResponse):
    """
    Response schema for discount code validation.
    """

    valid: bool
    discount_type: str | None = None  # 'percent_off' or 'amount_off'
    discount_value: float | None = None  # percentage or amount in cents
    discount_description: str | None = None
    currency: str | None = None  # only for amount_off
    is_100_percent_off: bool = False  # Explicit flag for 100% off discounts


class CreateFreeSubscriptionResponse(BaseResponse):
    """
    Response schema for free subscription creation.
    """

    message: str
    subscription_id: str
    org_id: str


class OrgSummaryResponse(BaseResponse):
    """
    Organization summary information for inclusion in other responses.
    """

    id: str
    name: str
    prem_status: str
    current_user_role: str

    @pydantic.field_validator("id", mode="before")
    @classmethod
    def validate_uuid(cls, v):
        return uuid_to_str(v)

    @pydantic.field_validator("prem_status", mode="before")
    @classmethod
    def validate_prem_status_enum(cls, v):
        """Convert the prem_status Enum to a string."""
        return v.value if isinstance(v, Enum) else v

    @pydantic.field_validator("current_user_role", mode="before")
    @classmethod
    def validate_current_user_role_enum(cls, v):
        """Convert the role Enum to a string."""
        return v.value if isinstance(v, Enum) else v


class ProjectSummaryResponse(BaseResponse):
    """
    Project response model for listing projects.
    """

    id: str
    name: str
    api_key: str
    org: OrgSummaryResponse
    span_count: int = 0
    trace_count: int = 0

    @pydantic.field_validator("id", "api_key", mode="before")
    @classmethod
    def validate_uuid(cls, v):
        return uuid_to_str(v)


class ProjectResponse(BaseResponse):
    """
    Project response model.
    Basic project information including organization details.
    """

    id: str
    org_id: str
    name: str
    environment: str
    api_key: str
    org: OrgResponse

    @pydantic.field_validator("id", "org_id", "api_key", mode="before")
    @classmethod
    def validate_uuid(cls, v):
        return uuid_to_str(v)


class ProjectCreateSchema(BaseSchema):
    """
    Schema for creating a project.
    """

    name: str
    org_id: str
    environment: str | None = None


class ProjectUpdateSchema(BaseSchema):
    """
    Schema for updating a project.
    Only name and environment can be updated.
    """

    name: str | None = None
    environment: str | None = None
