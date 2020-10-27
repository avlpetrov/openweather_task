from pydantic import BaseModel

from openweather_task.database.models import Token


__all__ = [
    "AuthorizeUserRequest",
    "AuthorizeUserResponse",
    "RegisterUserRequest",
    "RegisterUserResponse",
    "CreateItemRequest",
    "CreateItemResponse",
    "DeleteItemRequest",
    "DeleteItemResponse",
    "ListItemsRequest",
    "Item",
]


class RegisterUserRequest(BaseModel):
    login: str
    password: str

    class Config:
        orm_mode = True


class RegisterUserResponse(BaseModel):
    message: str

    class Config:
        orm_mode = True


class AuthorizeUserRequest(BaseModel):
    login: str
    password: str

    class Config:
        orm_mode = True


class AuthorizeUserResponse(BaseModel):
    token: Token

    class Config:
        orm_mode = True


class CreateItemRequest(BaseModel):
    name: str
    token: Token

    class Config:
        orm_mode = True


class CreateItemResponse(BaseModel):
    id: int
    name: str
    message: str

    class Config:
        orm_mode = True


class DeleteItemRequest(BaseModel):
    id: int
    token: str

    class Config:
        orm_mode = True


class DeleteItemResponse(BaseModel):
    message: str

    class Config:
        orm_mode = True


class ListItemsRequest(BaseModel):
    token: str

    class Config:
        orm_mode = True


class Item(BaseModel):
    id: int
    name: str

    class Config:
        orm_mode = True
