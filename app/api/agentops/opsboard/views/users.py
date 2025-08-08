from typing import Optional
from fastapi import Request, Depends

from agentops.common.orm import get_orm_session, Session

from ..models import UserModel
from ..schemas import StatusResponse, UserResponse, UserUpdateSchema


def get_user(
    *,
    request: Request,
    orm: Session = Depends(get_orm_session),
) -> UserResponse:
    """
    Get all details for the authenticated user.
    """
    # TODO I kinda want to return only a subset of the available fields on most
    # requests, but really it's just the billing address I don't think we should
    # be sending around all the time.
    user: Optional[UserModel] = UserModel.get_by_id(orm, request.state.session.user_id)
    assert user, "User not found"

    # Create the response, using billing_email (from auth.users) if available
    # This ensures we return the canonical email from auth.users
    response = UserResponse.model_validate(user)
    if user.billing_email:
        response.email = user.billing_email

    return response


def update_user(
    *,
    request: Request,
    orm: Session = Depends(get_orm_session),
    body: UserUpdateSchema,
) -> UserResponse:
    """
    Update the authenticated user's details.
    """
    user: Optional[UserModel] = UserModel.get_by_id(orm, request.state.session.user_id)
    assert user, "User not found"

    update_dict = body.model_dump(exclude_unset=True, exclude_none=True)
    for key, value in update_dict.items():
        setattr(user, key, value)

    orm.commit()

    # re-fetch user with relationships loaded instead of using refresh with args
    user = UserModel.get_by_id(orm, request.state.session.user_id)
    return UserResponse.model_validate(user)


def update_user_survey_complete(
    *,
    request: Request,
    orm: Session = Depends(get_orm_session),
) -> StatusResponse:
    """
    Mark the authenticated user's survey as complete.
    """
    user: Optional[UserModel] = UserModel.get_by_id(orm, request.state.session.user_id)
    assert user, "User not found"

    user.mark_survey_complete()
    orm.commit()

    return StatusResponse(message="User survey marked complete")
