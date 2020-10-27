import secrets
from enum import Enum
from typing import Any, List, Mapping, Optional

import sqlalchemy
from sqlalchemy import ForeignKey, and_, select
from sqlalchemy.ext.declarative import declarative_base

from openweather_task.database import database, metadata
from openweather_task.schemas import ItemSchema

Base = declarative_base()

__all__ = ["items", "ItemModel", "sendings", "SendingModel", "SendingStatus"]


class Item(Base):  # type: ignore
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


class Sending(Base):  # type: ignore
    __tablename__ = "sendings"
    id = sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True, index=True)
    item_id = sqlalchemy.Column(
        "item_id",
        sqlalchemy.Integer,
        ForeignKey("items.id"),
        nullable=False,
        index=True,
    )
    from_user_id = sqlalchemy.Column(
        "from_user_id",
        sqlalchemy.Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    to_user_id = sqlalchemy.Column(
        "to_user_id",
        sqlalchemy.Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    confirmation_url = sqlalchemy.Column(
        "confirmation_url", sqlalchemy.String, nullable=False
    )


sendings = sqlalchemy.Table(
    "sendings",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True, index=True),
    sqlalchemy.Column(
        "item_id",
        sqlalchemy.Integer,
        ForeignKey("items.id"),
        nullable=False,
        index=True,
    ),
    sqlalchemy.Column(
        "from_user_id",
        sqlalchemy.Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    ),
    sqlalchemy.Column(
        "to_user_id",
        sqlalchemy.Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    ),
    sqlalchemy.Column("confirmation_url", sqlalchemy.String, nullable=False),
)


class ItemModel:
    @classmethod
    async def create(cls, name: str, user_id: int) -> int:
        insert_item_query = items.insert().values(name=name, user_id=user_id)
        item_id = await database.execute(insert_item_query)
        return item_id

    @classmethod
    async def get_by_id(cls, item_id: int) -> Optional[Mapping[str, Any]]:
        select_item_query = items.select().where(items.c.id == item_id)
        item = await database.fetch_one(select_item_query)
        return item

    @classmethod
    async def get(cls, user_id: int, name: str) -> Optional[Mapping[str, Any]]:
        select_item_query = items.select().where(
            and_(items.c.user_id == user_id, items.c.name == name)
        )
        item = await database.fetch_one(select_item_query)
        return item

    @classmethod
    @database.transaction()
    async def delete(cls, item_id: int) -> Optional[int]:
        delete_item_query = (
            items.delete().where(items.c.id == item_id).returning(items.c.id)
        )
        deleted_item_id = await database.execute(delete_item_query)

        delete_item_sending_query = (
            sendings.delete().where(items.c.id == item_id).returning(items.c.id)
        )
        await database.execute(delete_item_sending_query)

        return deleted_item_id

    @classmethod
    async def list(cls, user_id: int) -> List[ItemSchema]:
        list_items_query = (
            select([items.c.id, items.c.name])
            .where(items.c.user_id == user_id)
            .order_by("id")
        )
        items_ = await database.fetch_all(list_items_query)
        return list(Item(**item) for item in items_)

    @classmethod
    async def transfer(
        cls, from_user_id: int, to_user_id: int, item_id: int
    ) -> Optional[int]:
        update_items_query = (
            items.update()
            .returning(items.c.id)
            .where(
                and_(
                    items.c.id == item_id,
                    items.c.user_id == from_user_id,
                )
            )
            .values(user_id=to_user_id)
        )
        transferred_item_id = await database.execute(update_items_query)
        return transferred_item_id


class SendingStatus(Enum):
    NO_SENDING = 0
    COMPLETED = 1
    FAILED = 2


class SendingModel:
    @classmethod
    async def initiate_sending(
        cls, from_user_id: int, to_user_id: int, item_id: int
    ) -> str:
        confirmation_url = await cls.get_confirmation_url(
            from_user_id, to_user_id, item_id
        )
        if confirmation_url:
            return confirmation_url

        url = secrets.token_urlsafe(16)
        confirmation_url = await cls.create(from_user_id, to_user_id, item_id, url)

        return confirmation_url

    @classmethod
    async def complete_sending(
        cls, to_user_id: int, item_id: int, confirmation_url: str
    ) -> SendingStatus:
        transaction = await database.transaction()

        sending = await cls.get(to_user_id, item_id, confirmation_url)
        if not sending:
            await transaction.rollback()
            return SendingStatus.NO_SENDING

        transferred_item_id = await ItemModel.transfer(
            from_user_id=sending["from_user_id"],
            to_user_id=sending["to_user_id"],
            item_id=sending["item_id"],
        )
        deleted_sending_id = await cls.delete(sending["id"])

        if transferred_item_id == item_id and deleted_sending_id == sending["id"]:
            await transaction.commit()
            return SendingStatus.COMPLETED

        await transaction.rollback()
        return SendingStatus.FAILED

    @classmethod
    async def get_confirmation_url(
        cls, from_user_id: int, to_user_id: int, item_id: int
    ) -> Optional[str]:
        select_url_query = select([sendings.c.confirmation_url]).where(
            and_(
                sendings.c.from_user_id == from_user_id,
                sendings.c.to_user_id == to_user_id,
                sendings.c.item_id == item_id,
            )
        )
        confirmation_url = await database.fetch_val(select_url_query)
        return confirmation_url

    @classmethod
    async def create(
        cls, from_user_id: int, to_user_id: int, item_id: int, confirmation_url: str
    ) -> str:
        insert_url_query = (
            sendings.insert()
            .values(
                item_id=item_id,
                from_user_id=from_user_id,
                to_user_id=to_user_id,
                confirmation_url=confirmation_url,
            )
            .returning(sendings.c.confirmation_url)
        )
        confirmation_url = await database.execute(insert_url_query)
        return confirmation_url

    @classmethod
    async def get(
        cls, to_user_id: int, item_id: int, confirmation_url: str
    ) -> Optional[Mapping[str, Any]]:

        select_sending_query = sendings.select().where(
            and_(
                sendings.c.to_user_id == to_user_id,
                sendings.c.item_id == item_id,
                sendings.c.confirmation_url == confirmation_url,
            )
        )

        sending = await database.fetch_one(select_sending_query)
        return sending

    @classmethod
    async def delete(cls, sending_id: int) -> int:

        delete_sending_query = (
            sendings.delete()
            .returning(sendings.c.id)
            .where(sendings.c.id == sending_id)
        )

        deleted_sending_id = await database.execute(delete_sending_query)
        return deleted_sending_id
