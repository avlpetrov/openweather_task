from starlette.responses import RedirectResponse

from openweather_task.database import database
from fastapi import FastAPI

from .routers import users, items
from openweather_task.config import APP_NAME, DEBUG

app: FastAPI = FastAPI(title=APP_NAME, debug=DEBUG)


@app.on_event("startup")
async def startup():
    await database.connect()


@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()


@app.get("/")
async def redirect_to_docs() -> RedirectResponse:
    return RedirectResponse(url="/docs")


app.include_router(users.router)
app.include_router(items.router)
