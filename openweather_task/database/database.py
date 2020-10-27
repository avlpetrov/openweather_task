import sqlalchemy
from databases import Database

from openweather_task.config import DATABASE_URI, CONNECTION_POOL_SIZE

__all__ = ["database", "metadata"]

database = Database(DATABASE_URI, max_size=CONNECTION_POOL_SIZE)
metadata = sqlalchemy.MetaData()
