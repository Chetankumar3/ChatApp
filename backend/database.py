import os
from dotenv import load_dotenv

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

load_dotenv()

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args=os.getenv("CONNECT_ARGS"),
    pool_size=int(os.getenv("POOL_SIZE")),
    max_overflow=int(os.getenv("MAX_OVERFLOW")),
    pool_timeout=int(os.getenv("POOL_TIMEOUT"))
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()
