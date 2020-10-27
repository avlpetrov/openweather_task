import secrets
from datetime import datetime, timedelta
from typing import Optional, List

import sqlalchemy
from databases.backends.postgres import Record
from sqlalchemy import and_, ForeignKey, select
from sqlalchemy.ext.declarative import declarative_base

from openweather_task.config import TOKEN_TTL_SECONDS, TOKEN_BYTES_LENGTH
from openweather_task.database import database, metadata

Base = declarative_base()


Token = str


class User(Base):
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


class Item(Base):
    __tablename__ = "items"
    id = sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True, index=True)
    user_id = sqlalchemy.Column(
        "user_id",
        sqlalchemy.Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    name = sqlalchemy.Column("name", sqlalchemy.String, nullable=False)


items = sqlalchemy.Table(
    "items",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True, index=True),
    sqlalchemy.Column(
        "user_id",
        sqlalchemy.Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    ),
    sqlalchemy.Column("name", sqlalchemy.String, nullable=False),
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
    async def authorize(cls, login: str, password: str) -> Optional[Token]:
        # TODO: Add SALT, store in encrypted format
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

    @classmethod
    async def get_authorized(cls, token: Token) -> Optional[Record]:
        select_user_query = users.select().where(
            and_(users.c.token == token, datetime.now() < users.c.token_expiration_time)
        )
        user = await database.fetch_one(select_user_query)
        return user


class ItemModel:
    @classmethod
    async def create(cls, name: str, user_id: int) -> int:
        insert_item_query = items.insert().values(name=name, user_id=user_id)
        item_id = await database.execute(insert_item_query)
        return item_id

    @classmethod
    async def get(cls, user_id: int, name: str) -> Optional[Record]:
        select_item_query = items.select().where(
            and_(items.c.user_id == user_id, items.c.name == name)
        )
        item = await database.fetch_one(select_item_query)
        return item

    @classmethod
    async def delete(cls, item_id: int) -> Optional[int]:
        delete_item_query = (
            items.delete().where(items.c.id == item_id).returning(items.c.id)
        )
        deleted_item_id = await database.execute(delete_item_query)
        return deleted_item_id

    @classmethod
    async def list(cls, user_id: int) -> List[Item]:
        list_items_query = (
            select([items.c.id, items.c.name])
            .where(items.c.user_id == user_id)
            .order_by("id")
        )
        items_ = await database.fetch_all(list_items_query)
        return list(Item(**item) for item in items_)
