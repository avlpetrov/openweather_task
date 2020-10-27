from datetime import datetime, timedelta
from typing import Any, Dict, List

import pytest
from async_asgi_testclient import TestClient
from databases import Database
from sqlalchemy import and_, select
from starlette import status
from starlette.responses import JSONResponse

from openweather_task.database.models import items, sendings, users
from openweather_task.main import app
from openweather_task.schemas import (
    CreateItemResponse,
    DeleteItemResponse,
    RegisterUserResponse,
)

JSON = Dict[str, Any]


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
    user: JSON,
    register_user_request: JSON,
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
    user: JSON,
    login_request: JSON,
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
    user: JSON,
    create_item_request: JSON,
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
    user: JSON,
    item: JSON,
    delete_item_request: JSON,
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
    user: JSON,
    items_: List[JSON],
    list_items_request: JSON,
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


@pytest.mark.parametrize(
    "user_a, user_a_items, user_b, send_item_request, expected_status",
    # fmt: off
    [
        # Sending successfully initiated.
        (
            {
                "id": 1,
                "login": "Alex",
                "password": "sample_password",
                "token": "cca8568a441e4f082527908791ec3bea",
                "token_expiration_time": datetime.now() + timedelta(hours=1),
            },
            [
                {"id": 3, "user_id": 1, "name": "item_name_3"},
                {"id": 1, "user_id": 1, "name": "item_name_1"},
                {"id": 2, "user_id": 1, "name": "item_name_2"},
            ],
            {
                "id": 2,
                "login": "Ben",
                "password": "sample_password",
                "token": None,
                "token_expiration_time": None,
            },
            {"id": 3, "token": "cca8568a441e4f082527908791ec3bea", "recipient": "Ben"},
            status.HTTP_201_CREATED,
        ),

        # Sender can't send item to himself.
        (
            {
                "id": 1,
                "login": "Alex",
                "password": "sample_password",
                "token": "cca8568a441e4f082527908791ec3bea",
                "token_expiration_time": datetime.now() + timedelta(hours=1),
            },
            [
                {"id": 3, "user_id": 1, "name": "item_name_3"},
                {"id": 1, "user_id": 1, "name": "item_name_1"},
                {"id": 2, "user_id": 1, "name": "item_name_2"},
            ],
            None,
            {
                "id": 3, "token": "cca8568a441e4f082527908791ec3bea",
                "recipient": "Alex"
            },
            status.HTTP_400_BAD_REQUEST,
        ),

        # No such item to send.
        (
            {
                "id": 1,
                "login": "Alex",
                "password": "sample_password",
                "token": "cca8568a441e4f082527908791ec3bea",
                "token_expiration_time": datetime.now() + timedelta(hours=1),
            },
            [
                {"id": 3, "user_id": 1, "name": "item_name_3"},
                {"id": 1, "user_id": 1, "name": "item_name_1"},
                {"id": 2, "user_id": 1, "name": "item_name_2"},
            ],
            {
                "id": 2,
                "login": "Ben",
                "password": "sample_password",
                "token": None,
                "token_expiration_time": None,
            },
            {"id": 99, "token": "cca8568a441e4f082527908791ec3bea", "recipient": "Ben"},
            status.HTTP_404_NOT_FOUND,
        ),

        # No such recipient.
        (
            {
                "id": 1,
                "login": "Alex",
                "password": "sample_password",
                "token": "cca8568a441e4f082527908791ec3bea",
                "token_expiration_time": datetime.now() + timedelta(hours=1),
            },
            [
                {"id": 3, "user_id": 1, "name": "item_name_3"},
                {"id": 1, "user_id": 1, "name": "item_name_1"},
                {"id": 2, "user_id": 1, "name": "item_name_2"},
            ],
            None,
            {"id": 3, "token": "cca8568a441e4f082527908791ec3bea", "recipient": "Ben"},
            status.HTTP_404_NOT_FOUND,
        ),
    ]
    # fmt: on
)
@pytest.mark.asyncio
async def test_send_item(
    user_a: JSON,
    user_a_items: List[JSON],
    user_b: JSON,
    send_item_request: JSON,
    expected_status: int,
    database: Database,
) -> None:
    try:
        if user_a:
            await database.execute(users.insert().values(**user_a))
        if user_b:
            await database.execute(users.insert().values(**user_b))
        if user_a_items:
            await database.execute_many(items.insert(), values=user_a_items)

        async with TestClient(app) as client:
            response = await client.post("/send", json=send_item_request)

        assert response.status_code == expected_status

    finally:
        await database.execute("TRUNCATE users CASCADE")


@pytest.mark.parametrize(
    "user_a, user_a_items, user_b, item_sending, get_item_request, expected_status",
    # fmt: off
    [
        # Receiving succeeded.
        (
            {
                "id": 1,
                "login": "Alex",
                "password": "sample_password",
                "token": None,
                "token_expiration_time": None,
            },
            [
                {"id": 3, "user_id": 1, "name": "item_name_3"},
                {"id": 1, "user_id": 1, "name": "item_name_1"},
                {"id": 2, "user_id": 1, "name": "item_name_2"},
            ],
            {
                "id": 2,
                "login": "Ben",
                "password": "sample_password",
                "token": "cca8568a441e4f082527908791ec3bea",
                "token_expiration_time": datetime.now() + timedelta(hours=1),
            },
            {
                "id": 1,
                "item_id": 3,
                "from_user_id": 1,
                "to_user_id": 2,
                "confirmation_url": "3ciaK7RvNsBgY-ehrkqZtg",
            },

            {
                "id": 3,
                "token": "cca8568a441e4f082527908791ec3bea",
                "confirmation_url": "3ciaK7RvNsBgY-ehrkqZtg",
            },
            status.HTTP_200_OK,
        ),

        # No such user, unauthorized.
        (
            None,
            None,
            None,
            None,
            {
                "id": 3,
                "token": "cca8568a441e4f082527908791ec3bea",
                "confirmation_url": "3ciaK7RvNsBgY-ehrkqZtg",
            },
            status.HTTP_401_UNAUTHORIZED,
        ),

        # No item sending with such confirmation url.
        (
            {
                "id": 1,
                "login": "Alex",
                "password": "sample_password",
                "token": None,
                "token_expiration_time": None,
            },
            [
                {"id": 3, "user_id": 1, "name": "item_name_3"},
                {"id": 1, "user_id": 1, "name": "item_name_1"},
                {"id": 2, "user_id": 1, "name": "item_name_2"},
            ],
            {
                "id": 2,
                "login": "Ben",
                "password": "sample_password",
                "token": "cca8568a441e4f082527908791ec3bea",
                "token_expiration_time": datetime.now() + timedelta(hours=1),
            },
            None,
            {
                "id": 3,
                "token": "cca8568a441e4f082527908791ec3bea",
                "confirmation_url": "3ciaK7RvNsBgY-ehrkqZtg",
            },
            status.HTTP_404_NOT_FOUND,
        ),
    ]
    # fmt: on
)
@pytest.mark.asyncio
async def test_get_item(
    user_a: JSON,
    user_a_items: List[JSON],
    user_b: JSON,
    item_sending: JSON,
    get_item_request: JSON,
    expected_status: int,
    database: Database,
) -> None:
    try:
        if user_a:
            await database.execute(users.insert().values(**user_a))
        if user_a_items:
            await database.execute_many(items.insert(), values=user_a_items)
        if user_b:
            await database.execute(users.insert().values(**user_b))
        if item_sending:
            await database.execute(sendings.insert().values(**item_sending))

        async with TestClient(app) as client:
            response = await client.get(
                f"/get/{get_item_request['confirmation_url']}",
                query_string=get_item_request,
            )

        assert response.status_code == expected_status

    finally:
        await database.execute("TRUNCATE users CASCADE")
