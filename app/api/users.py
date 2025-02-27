import typing

from fastapi import APIRouter, Depends, Query, status
from pydantic import EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.sessions import get_async_session
from app.dependencies import get_current_admin
from app.schemas.enums import UserStatusEnum
from app.schemas.user_schemas import (RequestUserModel, RequestUserUpdateModel,
                                      ResponseUserModel, UserModel)
from app.services import user_service

router = APIRouter()


@router.get("/", response_model=typing.List[ResponseUserModel], status_code=status.HTTP_200_OK)
async def get_users(
    user_id: typing.Optional[int] = Query(None, alias="id"),
    email: typing.Optional[EmailStr] = Query(None, alias="email"),
    user_status: typing.Optional[UserStatusEnum] = Query(None, alias="status"),
    session: AsyncSession = Depends(get_async_session),
    admin=Depends(get_current_admin),
):
    return await user_service.get_users(session, user_id, email, user_status)


@router.post("/register", response_model=ResponseUserModel, status_code=status.HTTP_200_OK)
async def register_user(
    user: RequestUserModel,
    session: AsyncSession = Depends(get_async_session),
):
    return await user_service.create_user(user, session)


@router.patch("/users/{user_id}/status", response_model=UserModel)
async def update_user_status(
    user_id: int,
    status_update: RequestUserUpdateModel,
    session: AsyncSession = Depends(get_async_session),
    admin=Depends(get_current_admin),
):
    return await user_service.update_user_status(user_id, status_update, session)
