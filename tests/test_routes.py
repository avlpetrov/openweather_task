from datetime import datetime, timedelta
from typing import Dict, List

import pytest
from async_asgi_testclient import TestClient
from databases import Database
from sqlalchemy import and_, select
from starlette import status
from starlette.responses import JSONResponse

from openweather_task.database.models import items, users
from openweather_task.main import app
from openweather_task.schemas import (
    CreateItemResponse,
    DeleteItemResponse,
    RegisterUserResponse,
)


@pytest.mark.parametrize(
    "user, register_user_request, expected_response",
    # fmt: off
    [
        # User with provided login already exists.
        (
            {
                "id": 1,
                "login": "sample_login",
                "password": "sample_password",
                "token": None,
                "token_expiration_time": None,
            },
            {"login": "sample_login", "password": "sample_password"},
            JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={"detail": "User already exists"},
            )
        ),

        # Successfully registered.
        (
            None,
            {"login": "sample_login", "password": "sample_password"},
            JSONResponse(
                status_code=status.HTTP_201_CREATED,
                content=RegisterUserResponse(
                    message="User successfully registered"
                ).dict(),
            )
        ),
    ]
    # fmt: on
)
@pytest.mark.asyncio
async def test_register_user(
    user: Dict[str, str],
    register_user_request: Dict[str, str],
    expected_response: JSONResponse,
    database: Database,
) -> None:
    try:
        if user:
            await database.execute(users.insert().values(**user))

        async with TestClient(app) as client:
            response = await client.post("/registration", json=register_user_request)

        assert response.status_code == expected_response.status_code
        assert response.content == expected_response.body

    finally:
        await database.execute("TRUNCATE users CASCADE")


@pytest.mark.parametrize(
    "user, login_request, expected_status",
    # fmt: off
    [
        # No active token, new one is generated, authorized.
        (
            {
                "id": 1,
                "login": "sample_login",
                "password": "sample_password",
                "token": None,
                "token_expiration_time": None,
            },
            {"login": "sample_login", "password": "sample_password"},
            status.HTTP_201_CREATED,
        ),

        # New token will be generated even if the old one is not expired.
        (
            {
                "id": 1,
                "login": "sample_login",
                "password": "sample_password",
                "token": "cca8568a441e4f082527908791ec3bea",
                "token_expiration_time": datetime.now() + timedelta(hours=1),
            },
            {"login": "sample_login", "password": "sample_password"},
            status.HTTP_201_CREATED,
        ),

        # No registered user, unauthorized.
        (
            None,
            {"login": "sample_login", "password": "sample_password"},
            status.HTTP_401_UNAUTHORIZED,
        ),
    ]
    # fmt: on
)
@pytest.mark.asyncio
async def test_login_user(
    user: Dict[str, str],
    login_request: Dict[str, str],
    expected_status: int,
    database: Database,
) -> None:
    try:
        if user:
            await database.execute(users.insert().values(**user))

        async with TestClient(app) as client:
            response = await client.post("/login", json=login_request)

        expected_token = await database.execute(
            select([users.c.token]).where(
                and_(
                    users.c.login == login_request["login"],
                    users.c.password == login_request["password"],
                )
            )
        )
        if user:
            assert response.json()["token"] == expected_token
        assert response.status_code == expected_status

    finally:
        await database.execute("TRUNCATE users CASCADE")


@pytest.mark.parametrize(
    "user, create_item_request, expected_response",
    # fmt: off
    [
        # Authorized to create item.
        (
            {
                "id": 1,
                "login": "sample_login",
                "password": "sample_password",
                "token": "cca8568a441e4f082527908791ec3bea",
                "token_expiration_time": datetime.now() + timedelta(hours=1),
            },
            {"name": "sample_name", "token": "cca8568a441e4f082527908791ec3bea"},
            JSONResponse(
                status_code=status.HTTP_201_CREATED,
                content=CreateItemResponse(
                    id=1, name="sample_name", message="Item created"
                ).dict()
            )
        ),

        # Expired token, unauthorized to create item.
        (
            {
                "id": 1,
                "login": "sample_login",
                "password": "sample_password",
                "token": "cca8568a441e4f082527908791ec3bea",
                "token_expiration_time": datetime.now() - timedelta(hours=1),
            },
            {"name": "sample_name", "token": "cca8568a441e4f082527908791ec3bea"},
            JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Provided token is unauthorized"}
            )
        ),

        # No token at all, unauthorized to create item.
        (
            {
                "id": 1,
                "login": "sample_login",
                "password": "sample_password",
                "token": None,
                "token_expiration_time": None,
            },
            {"name": "sample_name", "token": "cca8568a441e4f082527908791ec3bea"},
            JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Provided token is unauthorized"}
            )
        ),
    ]
)
@pytest.mark.asyncio
async def test_create_item(
    user: Dict[str, str],
    create_item_request: Dict[str, str],
    expected_response: JSONResponse,
    database: Database,
) -> None:
    try:
        if user:
            await database.execute(users.insert().values(**user))

        async with TestClient(app) as client:
            response = await client.post("/items/new", json=create_item_request)

        assert response.status_code == expected_response.status_code
        assert response.content == expected_response.body

    finally:
        await database.execute("TRUNCATE users CASCADE")


@pytest.mark.parametrize(
    "user, item, delete_item_request, expected_response",
    # fmt: off
    [
        # Authorized, item successfully deleted.
        (
            {
                "id": 1,
                "login": "sample_login",
                "password": "sample_password",
                "token": "cca8568a441e4f082527908791ec3bea",
                "token_expiration_time": datetime.now() + timedelta(hours=1),
            },
            {"id": 1, "user_id": 1, "name": "sample_item_name"},
            {"id": 1, "token": "cca8568a441e4f082527908791ec3bea"},
            JSONResponse(
                status_code=status.HTTP_200_OK,
                content=DeleteItemResponse(message="Item successfully deleted").dict()
            )
        ),

        # Authorized, but no such item to delete.
        (
            {
                "id": 1,
                "login": "sample_login",
                "password": "sample_password",
                "token": "cca8568a441e4f082527908791ec3bea",
                "token_expiration_time": datetime.now() + timedelta(hours=1),
            },
            None,
            {"id": 1, "token": "cca8568a441e4f082527908791ec3bea"},
            JSONResponse(
                status_code=status.HTTP_204_NO_CONTENT,
                content=DeleteItemResponse(message="No such item").dict()
            )
        ),

        # No user with such token, unauthorized.
        (
            {
                "id": 1,
                "login": "sample_login",
                "password": "sample_password",
                "token": None,
                "token_expiration_time": None,
            },
            None,
            {"id": 1, "token": "cca8568a441e4f082527908791ec3bea"},
            JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Provided token is unauthorized"}
            )
        ),
    ]
    # fmt: on
)
@pytest.mark.asyncio
async def test_delete_item(
    user: Dict[str, str],
    item: Dict[str, str],
    delete_item_request: Dict[str, str],
    expected_response: JSONResponse,
    database: Database,
) -> None:
    try:
        if user:
            await database.execute(users.insert().values(**user))

        if item:
            await database.execute(items.insert().values(**item))

        async with TestClient(app) as client:
            response = await client.delete(
                f"/items/{delete_item_request['id']}", json=delete_item_request
            )

        assert response.status_code == expected_response.status_code
        assert response.content == expected_response.body

    finally:
        await database.execute("TRUNCATE users CASCADE")


@pytest.mark.parametrize(
    "user, items_, list_items_request, expected_response",
    # fmt: off
    [
        # Non-empty items list.
        (
            {
                "id": 1,
                "login": "sample_login",
                "password": "sample_password",
                "token": "cca8568a441e4f082527908791ec3bea",
                "token_expiration_time": datetime.now() + timedelta(hours=1),
            },
            [
                {"id": 3, "user_id": 1, "name": "item_name_3"},
                {"id": 1, "user_id": 1, "name": "item_name_1"},
                {"id": 2, "user_id": 1, "name": "item_name_2"},
            ],
            {"token": "cca8568a441e4f082527908791ec3bea"},
            JSONResponse(
                status_code=status.HTTP_200_OK,
                content=[
                    {"id": 1, "name": "item_name_1"},
                    {"id": 2, "name": "item_name_2"},
                    {"id": 3, "name": "item_name_3"},
                ],
            )
        ),

        # Empty items list.
        (
            {
                "id": 1,
                "login": "sample_login",
                "password": "sample_password",
                "token": "cca8568a441e4f082527908791ec3bea",
                "token_expiration_time": datetime.now() + timedelta(hours=1),
            },
            None,
            {"token": "cca8568a441e4f082527908791ec3bea"},
            JSONResponse(
                status_code=status.HTTP_200_OK,
                content=[],
            )
        ),
    ]
    # fmt: on
)
@pytest.mark.asyncio
async def test_list_items(
    user: Dict[str, str],
    items_: List[Dict[str, str]],
    list_items_request: Dict[str, str],
    expected_response: JSONResponse,
    database: Database,
) -> None:
    try:
        if user:
            await database.execute(users.insert().values(**user))

        if items_:
            await database.execute_many(items.insert(), values=items_)

        async with TestClient(app) as client:
            response = await client.get("/items", query_string=list_items_request)

        assert response.status_code == expected_response.status_code
        assert response.content == expected_response.body

    finally:
        await database.execute("TRUNCATE users CASCADE")
