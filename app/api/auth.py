from datetime import timedelta

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app import config
from app.db.sessions import get_async_session
from app.exceptions.exceptions import (InvalidCredentialsException,
                                       InvalidTokenException)
from app.schemas.auth_schemas import Token
from app.schemas.user_schemas import ResponseUserModel
from app.services import auth_service, user_service

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


@router.post("/login", response_model=Token, status_code=status.HTTP_200_OK)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_async_session),
):
    user = await auth_service.authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise InvalidCredentialsException()

    token_data = {"sub": str(user.id), "email": user.email, "role": user.role}

    access_token = auth_service.create_access_token(
        token_data, expires_delta=timedelta(minutes=config.JWT_EXPIRATION_MINUTES)
    )
    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=ResponseUserModel, status_code=status.HTTP_200_OK)
async def get_me(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_async_session),
):
    payload = auth_service.decode_access_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise InvalidTokenException()
    return await user_service.get_user_by_id(session, int(user_id))
