import secrets
from datetime import datetime, timedelta
from typing import Any, Mapping, Optional

import sqlalchemy
from sqlalchemy import and_
from sqlalchemy.ext.declarative import declarative_base

from openweather_task.config import TOKEN_BYTES_LENGTH, TOKEN_TTL_SECONDS
from openweather_task.database import database, metadata

Base = declarative_base()


__all__ = ["users", "UserModel", "Base"]


class User(Base):  # type: ignore
    __tablename__ = "users"
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, index=True)
    login = sqlalchemy.Column(sqlalchemy.String, nullable=False, unique=True)
    password = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    token = sqlalchemy.Column(sqlalchemy.String, unique=True, index=True)
    token_expiration_time = sqlalchemy.Column(sqlalchemy.DateTime)


users = sqlalchemy.Table(
    "users",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True, index=True),
    sqlalchemy.Column("login", sqlalchemy.String, nullable=False, unique=True),
    sqlalchemy.Column("password", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("token", sqlalchemy.String, unique=True, index=True),
    sqlalchemy.Column("token_expiration_time", sqlalchemy.DateTime),
)


class UserModel:
    @classmethod
    async def create(cls, login: str, password: str) -> int:
        insert_user_query = users.insert().values(login=login, password=password)
        user_id = await database.execute(insert_user_query)
        return user_id

    @classmethod
    async def is_registered(cls, login: str) -> bool:
        select_user_query = users.select().where(users.c.login == login)
        user = await database.fetch_one(select_user_query)
        return bool(user)

    @classmethod
    async def authorize(cls, login: str, password: str) -> Optional[str]:
        token = secrets.token_hex(nbytes=TOKEN_BYTES_LENGTH)
        token_expiration_time = datetime.now() + timedelta(seconds=TOKEN_TTL_SECONDS)

        select_user_query = users.select().where(
            and_(users.c.login == login, users.c.password == password)
        )
        user = await database.execute(select_user_query)
        if user:

            set_token_query = (
                users.update()
                .where(and_(users.c.login == login, users.c.password == password))
                .values(token=token, token_expiration_time=token_expiration_time)
            )
            await database.execute(set_token_query)
            return token

        return None

    @classmethod
    async def get_authorized(cls, token: str) -> Optional[Mapping[str, Any]]:
        select_user_query = users.select().where(
            and_(users.c.token == token, datetime.now() < users.c.token_expiration_time)
        )
        user = await database.fetch_one(select_user_query)
        return user

    @classmethod
    async def get_by_login(cls, login: str) -> Optional[Mapping[str, Any]]:
        select_user_query = users.select().where(users.c.login == login)
        user = await database.fetch_one(select_user_query)
        return user
