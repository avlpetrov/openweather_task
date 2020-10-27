from starlette.config import Config

config = Config(".env")

APP_NAME: str = config("APP_NAME", default="OpenWeather Task App")
DEBUG: bool = config("DEBUG", default=False)

DATABASE_URI = config("DATABASE_URI")
CONNECTION_POOL_SIZE = config("CONNECTION_POOL_SIZE", default=20)
TOKEN_TTL_SECONDS = config("TOKEN_TTL", default=60 * 60 * 24)
TOKEN_BYTES_LENGTH = config("TOKEN_BYTES_LENGTH", default=32)
