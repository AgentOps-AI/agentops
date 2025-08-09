from typing import Literal
import pydantic


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


class RedirectMessageResponse(StatusResponse):
    """
    Response type for redirecting to a specific URL.
    """

    url: str


class LoginSchema(BaseSchema):
    """
    Schema for login data.
    """

    email: str
    password: str


class OTPSchema(BaseSchema):
    """
    Schema for the request to send a one-time password (OTP) to the user's email.
    """

    email: str


OAuthProvider = Literal["google", "github"]


class OAuthSchema(BaseSchema):
    """
    Schema for the request to initiate OAuth login.
    """

    provider: OAuthProvider
    redirect_to: str | None = None


class SignupSchema(BaseSchema):
    """
    Schema for user signup data.
    """

    email: str
    password: str
    full_name: str


class PasswordResetSchema(BaseSchema):
    """
    Schema for the request to reset a user's password.
    """

    email: str
