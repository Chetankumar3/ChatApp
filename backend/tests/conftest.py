import os
from dotenv import load_dotenv
from sqlalchemy import NullPool
load_dotenv()
from datetime import datetime, timedelta, timezone
import sys
from pathlib import Path

import jwt

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from main import app

import pytest_asyncio
import bcrypt
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

# 1. Import your app, DB base, and models
# (Adjust "main" and "login" if they are inside a "routers" or "src" folder)
from database import Base, get_db
import DB_models
from src.login import create_jwt_token

# CRITICAL: Must use sqlite+aiosqlite://
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_async_engine(
    DATABASE_URL,
    poolclass=NullPool,
    echo=False
)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_db():
    """Creates the database tables once before any tests run."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Teardown: Wipe the DB file structure after the entire test suite finishes
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture()
async def db_session():
    """The async transaction rollback fixture."""
    async with engine.connect() as conn:
        transaction = await conn.begin()

        # Bind the session to this specific connection
        session = AsyncSession(bind=conn, expire_on_commit=False)

        yield session

        # Teardown: Close session and instantly rollback the transaction
        await session.close()
        await transaction.rollback()


@pytest_asyncio.fixture()
async def client(db_session):
    """Overrides the FastAPI dependency to use our isolated async session."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


@pytest_asyncio.fixture()
async def authorized_client(client, db_session):
    """
    Creates a valid user, hashes a password, generates a JWT using
    your actual login logic, and injects it into the test client.
    """
    # 1. Create the main user record
    test_user = DB_models.user(
        username="test_user", name="Test Account", email="test@example.com"
    )
    db_session.add(test_user)
    await db_session.flush()  # Flush to let SQLite generate the test_user.id

    # 2. Create the linked password record with a real bcrypt hash
    # (Just in case any test logic actually verifies it!)
    hashed = bcrypt.hashpw("testpassword123".encode("utf-8"), bcrypt.gensalt())
    test_password = DB_models.passwords(
        userId=test_user.id,
        hashedPassword=hashed.decode("utf-8"),
    )
    db_session.add(test_password)
    await db_session.commit()
    await db_session.refresh(test_user)

    # 3. Generate the token using the exact logic from login.py!
    token = create_jwt_token(test_user.id)

    # 4. Attach token to headers
    client.headers = {**client.headers, "Authorization": f"Bearer {token}"}

    yield client


SECRET_KEY = "dummy-testing-secret-key"  # must match your app's secret
ALGORITHM = "HS256"


@pytest_asyncio.fixture
async def expired_token():
    def _make(user_id: int):
        payload = {
            "user_id": user_id,
            "exp": datetime.now(timezone.utc) - timedelta(minutes=5),  # already expired
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
    """This is the fixture where Alice's data lives."""
    # 1. The data is defined here
    alice = DB_models.user(
        username="alice_wonder", name="Alice", email="alice@example.com"
    )

    # 2. It is inserted into the database here
    db_session.add(alice)
    await db_session.commit()
    await db_session.refresh(alice)

    # 3. It is handed over to your test here
    yield alice
