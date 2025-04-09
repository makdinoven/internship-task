import asyncio
import os
import uuid

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.sessions import get_async_session
from app.main import app
from app.models.db_models import Base, User
from app.services import auth_service
from app.services.auth_service import pwd_context

# Используем отдельную БД SQLite для тестов
TEST_DB_URL = "sqlite+aiosqlite:///./test.db"
# Удаляем файл тестовой БД, если остался от предыдущего запуска
if os.path.exists("test.db"):
    os.remove("test.db")

os.environ["DATABASE_URL"] = "sqlite:///./test.db"

engine = create_async_engine(TEST_DB_URL, future=True)
AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)  # type: ignore


async def async_create_all():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# Создаем таблицы в новой тестовой БД
asyncio.run(async_create_all())


# Переопределяем зависимость get_db для FastAPI, чтобы использовать тестовую БД
async def override_get_db():
    async with AsyncSessionLocal() as session:
        # Создаем новую сессию на время запроса
        yield session
        # Откатываем изменения после запроса (чтобы тесты были изолированы, если не вызвать commit)
        await session.rollback()


app.dependency_overrides[get_async_session] = override_get_db  # type: ignore


@pytest_asyncio.fixture
async def db_session():
    """Асинхронная сессия БД для модульных тестов."""
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()  # откатываем изменения после каждого теста


@pytest_asyncio.fixture
async def client():
    """HTTP-клиент для интеграционных тестов, использующий FastAPI приложение."""
    async with AsyncClient(app=app, base_url="http://testserver") as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_headers(db_session, client):
    email_prefix = "testuser_" + uuid.uuid4().hex[:6]
    password = "testpass"
    email = f"{email_prefix}@example.com"

    # Создаем пользователя напрямую
    hashed_password = pwd_context.hash(password)
    user = User(email=email, password=hashed_password)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Генерируем JWT-токен
    token = auth_service.create_access_token({"sub": str(user.id), "email": user.email})
    return {"Authorization": f"Bearer {token}"}
