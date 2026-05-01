import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bcrypt
import jwt
import pytest_asyncio
from dotenv import load_dotenv
from httpx import AsyncClient, ASGITransport
from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

load_dotenv()

# Add ChatApp/ root to sys.path so `backend` is importable as a package
CHATAPP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CHATAPP_ROOT))

from backend.main_service.main import app
from backend.main_service.database import Base, get_db
from backend.main_service import DB_models
from backend.main_service.src.login import create_jwt_token

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_async_engine(DATABASE_URL, poolclass=NullPool, echo=False)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture()
async def db_session():
    async with engine.connect() as conn:
        transaction = await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        yield session
        await session.close()
        await transaction.rollback()


@pytest_asyncio.fixture()
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


@pytest_asyncio.fixture()
async def authorized_client(client, db_session):
    test_user = DB_models.user(
        username="test_user", name="Test Account", email="test@example.com"
    )
    db_session.add(test_user)
    await db_session.flush()

    hashed = bcrypt.hashpw("testpassword123".encode("utf-8"), bcrypt.gensalt())
    db_session.add(DB_models.passwords(
        userId=test_user.id,
        hashedPassword=hashed.decode("utf-8"),
    ))
    await db_session.commit()
    await db_session.refresh(test_user)

    token = create_jwt_token(test_user.id)
    client.headers = {**client.headers, "Authorization": f"Bearer {token}"}
    yield client


SECRET_KEY = "dummy-testing-secret-key"
ALGORITHM = "HS256"


@pytest_asyncio.fixture
async def expired_token():
    def _make(user_id: int):
        payload = {
            "user_id": user_id,
            "exp": datetime.now(timezone.utc) - timedelta(minutes=5),
        }
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return _make


@pytest_asyncio.fixture
async def make_token():
    def _make(user_id: int):
        payload = {
            "user_id": user_id,
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return _make


@pytest_asyncio.fixture()
async def user_a(db_session):
    alice = DB_models.user(
        username="alice_wonder", name="Alice", email="alice@example.com"
    )
    db_session.add(alice)
    await db_session.commit()
    await db_session.refresh(alice)
    yield alice
