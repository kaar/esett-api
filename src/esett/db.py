import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

DATABASE_URL = os.environ.get(
    "ESETT_DATABASE_URL",
    "postgresql+asyncpg://esett:esett@localhost:5432/esett",
)

engine = create_async_engine(DATABASE_URL, echo=False)
SessionFactory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession]:
    async with SessionFactory() as session:
        yield session
