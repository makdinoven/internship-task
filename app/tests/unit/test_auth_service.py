from datetime import datetime, timedelta

import jwt
import pytest

from app.exceptions.exceptions import (InvalidTokenException,
                                       TokenExpiredException)
from app.models.db_models import User
from app.schemas.user_schemas import RequestUserModel
from app.services import auth_service, user_service
from app.services.auth_service import pwd_context


@pytest.mark.asyncio
async def test_password_hash_and_verify():
    """Тест функций хэширования и проверки пароля."""
    password = "mysecret"
    # Генерируем хэш пароля через pwd_context
    hashed = pwd_context.hash(password)
    # Хэш не должен равняться исходному паролю
    assert hashed != password
    # Проверяем правильный пароль
    assert pwd_context.verify(password, hashed) is True
    # Проверяем неправильный пароль
    assert pwd_context.verify("wrongpass", hashed) is False


@pytest.mark.asyncio
async def test_create_and_decode_token(monkeypatch):
    """Тест создания и декодирования JWT токена."""
    # Патчим значения непосредственно в модуле auth_service
    monkeypatch.setattr(auth_service, "JWT_SECRET", "TEST_SECRET_KEY")
    monkeypatch.setattr(auth_service, "JWT_ALGORITHM", "HS256")
    user_data = {"user_id": 42}
    token = auth_service.create_access_token(user_data)
    assert isinstance(token, str)
    # Декодируем токен напрямую с помощью PyJWT для проверки содержимого
    payload = jwt.decode(token, "TEST_SECRET_KEY", algorithms=["HS256"])
    assert payload["user_id"] == 42


@pytest.mark.asyncio
async def test_authenticate_user_success(db_session):
    """Тест успешной аутентификации пользователя по email и паролю."""
    email = "auth@example.com"
    password = "pass123"
    created_user = await user_service.create_user(
        user=RequestUserModel(email=email, password=password), session=db_session
    )
    # Пытаемся аутентифицировать с правильными данными (используем email)
    auth_user = await auth_service.authenticate_user(db_session, email=email, password=password)
    assert auth_user is not None
    assert auth_user.email == created_user.email
    assert isinstance(auth_user, User)
    assert auth_user.email == email
    # Проверяем, что при неверном пароле возвращается None
    failed_auth = await auth_service.authenticate_user(db_session, email=email, password="wrongpass")
    assert failed_auth is None


@pytest.mark.asyncio
async def test_decode_expired_token(monkeypatch):
    """Тест обработки просроченного токена при декодировании."""
    monkeypatch.setattr(auth_service, "JWT_SECRET", "TEST_SECRET")
    monkeypatch.setattr(auth_service, "JWT_ALGORITHM", "HS256")

    # Создаем токен с истекшим сроком (прошлое время)
    expired_token = jwt.encode(
        {"user_id": 1, "exp": datetime.utcnow() - timedelta(minutes=5)}, "TEST_SECRET", algorithm="HS256"
    )

    with pytest.raises(TokenExpiredException):
        auth_service.decode_access_token(expired_token)


@pytest.mark.asyncio
async def test_decode_invalid_token(monkeypatch):
    """Тест обработки токена с неверной подписью."""
    monkeypatch.setattr(auth_service, "JWT_SECRET", "TEST_SECRET")
    monkeypatch.setattr(auth_service, "JWT_ALGORITHM", "HS256")

    # Создаем токен с другим секретом
    invalid_token = jwt.encode({"user_id": 1}, "WRONG_SECRET", algorithm="HS256")

    with pytest.raises(InvalidTokenException):
        auth_service.decode_access_token(invalid_token)


@pytest.mark.asyncio
async def test_authenticate_user_not_found(db_session):
    """Тест аутентификации с несуществующим пользователем."""
    result = await auth_service.authenticate_user(db_session, email="nouser@example.com", password="nopass")
    assert result is None
