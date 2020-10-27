from fastapi import APIRouter, HTTPException
from starlette import status

from openweather_task.database.models import UserModel
from openweather_task.schemas import (
    AuthorizeUserResponse,
    AuthorizeUserRequest,
    RegisterUserRequest,
    RegisterUserResponse,
)

router = APIRouter()


@router.post(
    "/registration",
    status_code=status.HTTP_201_CREATED,
    response_model=RegisterUserResponse,
)
async def register_user(request: RegisterUserRequest) -> RegisterUserResponse:
    already_registered = await UserModel.is_registered(request.login)
    if not already_registered:
        await UserModel.create(request.login, request.password)

        registration_succeeded = await UserModel.is_registered(request.login)
        if registration_succeeded:
            return RegisterUserResponse(message="User successfully registered")

    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT, detail="User already exists"
    )


@router.post(
    "/login",
    status_code=status.HTTP_201_CREATED,
    response_model=AuthorizeUserResponse,
)
async def login_user(request: AuthorizeUserRequest) -> AuthorizeUserResponse:
    token = await UserModel.authorize(request.login, request.password)
    if token:
        return AuthorizeUserResponse(token=token)

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No such user")
