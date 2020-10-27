from typing import List

from fastapi import APIRouter, HTTPException
from starlette import status
from starlette.responses import JSONResponse

from openweather_task.database.models import UserModel, ItemModel
from openweather_task.schemas import (
    CreateItemResponse,
    CreateItemRequest,
    DeleteItemResponse,
    DeleteItemRequest,
    Item,
    ListItemsRequest,
)

router = APIRouter()


@router.post(
    "/items/new",
    status_code=status.HTTP_201_CREATED,
    response_model=CreateItemResponse,
)
async def create_item(request: CreateItemRequest) -> CreateItemResponse:
    user = await UserModel.get_authorized(request.token)
    if user:
        item = await ItemModel.get(user_id=user["id"], name=request.name)
        if item:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Item already exists"
            )

        item_id = await ItemModel.create(name=request.name, user_id=user["id"])
        return CreateItemResponse(id=item_id, name=request.name, message="Item created")

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Provided token is unauthorized",
    )


@router.delete(
    "/items/{id}",
    response_model=DeleteItemResponse,
)
async def delete_item(request: DeleteItemRequest) -> JSONResponse:
    user = await UserModel.get_authorized(request.token)
    if user:
        item_id = await ItemModel.delete(request.id)
        if item_id:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content=DeleteItemResponse(message="Item successfully deleted").dict(),
            )

        return JSONResponse(
            status_code=status.HTTP_204_NO_CONTENT,
            content=DeleteItemResponse(message="No such item").dict(),
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Provided token is unauthorized",
    )


@router.get(
    "/items",
    status_code=status.HTTP_200_OK,
    response_model=List[Item],
)
async def list_items(token: str) -> List[Item]:
    user = await UserModel.get_authorized(token)
    if user:
        items = await ItemModel.list(user_id=user["id"])
        return items

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Provided token is unauthorized",
    )
