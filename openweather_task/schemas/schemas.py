from pydantic import BaseModel

__all__ = [
    "AuthorizeUserRequest",
    "AuthorizeUserResponse",
    "RegisterUserRequest",
    "RegisterUserResponse",
    "CreateItemRequest",
    "CreateItemResponse",
    "DeleteItemRequest",
    "DeleteItemResponse",
    "ItemSchema",
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
    token: str

    class Config:
        orm_mode = True


class CreateItemRequest(BaseModel):
    name: str
    token: str

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


class ItemSchema(BaseModel):
    id: int
    name: str

    class Config:
        orm_mode = True
