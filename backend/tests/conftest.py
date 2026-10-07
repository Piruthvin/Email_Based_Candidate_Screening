import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from app.core.config import get_settings

settings = get_settings()

@pytest_asyncio.fixture
async def test_engine():
    engine = create_async_engine(settings.async_database_url, poolclass=NullPool)
    yield engine
    await engine.dispose()

@pytest_asyncio.fixture
async def db_session(test_engine):
    async_session = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
        try:
            await session.close()
        except Exception:
            pass
