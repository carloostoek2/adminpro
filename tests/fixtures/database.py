"""
Database fixtures for testing.

Provides isolated in-memory database for each test.
"""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text

from bot.database.base import Base
from bot.database.models import BotConfig


@pytest_asyncio.fixture
async def test_db():
    """
    Fixture: Provides an isolated in-memory database for each test.

    Creates a new SQLite in-memory database, creates all tables,
    yields the session factory, then cleans up after the test.

    Yields:
        async_sessionmaker: Session factory bound to test database
    """
    # Create in-memory engine
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session factory
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    # Create BotConfig singleton
    async with session_factory() as session:
        config = BotConfig(
            id=1,
            wait_time_minutes=5,
            vip_reactions=["🔥", "❤️"],
            free_reactions=["👍"],
            subscription_fees={"monthly": 10, "yearly": 100}
        )
        session.add(config)
        await session.commit()

    yield session_factory

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def test_session(test_db):
    """
    Fixture: Provides an active database session for a test.

    Automatically commits or rolls back based on test outcome.

    Args:
        test_db: The test_db fixture (session factory)

    Yields:
        AsyncSession: Active database session
    """
    async with test_db() as session:
        yield session
        # Rollback after test to ensure isolation
        await session.rollback()
