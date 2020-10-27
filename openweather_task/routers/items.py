from typing import List

from fastapi import APIRouter, HTTPException
from starlette import status
from starlette.responses import JSONResponse

from openweather_task.database.models import (
    ItemModel,
    SendingModel,
    SendingStatus,
    UserModel,
)
from openweather_task.schemas import (
    CreateItemRequest,
    CreateItemResponse,
    DeleteItemRequest,
    DeleteItemResponse,
    ItemSchema,
    SendItemRequest,
    SendItemResponse,
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
    response_model=List[ItemSchema],
)
async def list_items(token: str) -> List[ItemSchema]:
    user = await UserModel.get_authorized(token)
    if user:
        items = await ItemModel.list(user_id=user["id"])
        return items

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Provided token is unauthorized",
    )


@router.post(
    "/send",
    status_code=status.HTTP_201_CREATED,
    response_model=SendItemResponse,
)
async def send_item(request: SendItemRequest) -> SendItemResponse:
    sender = await UserModel.get_authorized(request.token)
    if not sender:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Provided token is unauthorized",
        )
    if sender["login"] == request.recipient:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can't send item to yourself",
        )

    item = await ItemModel.get_by_id(request.id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No such item",
        )

    recipient = await UserModel.get_by_login(request.recipient)
    if not recipient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No such recipient",
        )

    confirmation_url = await SendingModel.initiate_sending(
        from_user_id=sender["id"], to_user_id=recipient["id"], item_id=request.id
    )
    return SendItemResponse(confirmation_url=confirmation_url)


@router.get(
    "/get/{confirmation_url}",
    status_code=status.HTTP_200_OK,
)
async def get_item(id: int, confirmation_url: str, token: str) -> JSONResponse:  # noqa
    user = await UserModel.get_authorized(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Provided token is unauthorized",
        )

    item = await ItemModel.get_by_id(id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No such item",
        )

    sending_status = await SendingModel.complete_sending(
        to_user_id=user["id"], item_id=id, confirmation_url=confirmation_url
    )
    if sending_status == SendingStatus.NO_SENDING:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No such sending",
        )

    if sending_status == sending_status.COMPLETED:
        return JSONResponse(content={"message": "Item successfully received"})

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Something went wrong while receiving an item",
    )
