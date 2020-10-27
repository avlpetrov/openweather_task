import sqlalchemy
from databases import Database

from openweather_task.config import CONNECTION_POOL_SIZE, DATABASE_URI

__all__ = ["database", "metadata"]

database = Database(DATABASE_URI, max_size=CONNECTION_POOL_SIZE)
metadata = sqlalchemy.MetaData()
