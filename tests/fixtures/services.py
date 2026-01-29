"""
Service fixtures for testing.

Provides mocked and real service containers for tests.
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, Mock

from bot.services.container import ServiceContainer


@pytest.fixture
def mock_bot():
    """
    Fixture: Mock del bot de Telegram.

    Provides mock of required Telegram API methods:
    - get_chat
    - get_chat_member
    - create_chat_invite_link
    - ban_chat_member
    - unban_chat_member
    - send_message
    - get_me (returns bot info)
    """
    bot = Mock()
    bot.id = 123456789
    bot.username = "test_bot"
    bot.first_name = "Test Bot"

    # Mock async methods
    bot.get_chat = AsyncMock()
    bot.get_chat_member = AsyncMock()
    bot.create_chat_invite_link = AsyncMock(return_value=Mock(
        invite_link="https://t.me/test/invite123",
        expire_date=None,
        member_limit=None
    ))
    bot.ban_chat_member = AsyncMock()
    bot.unban_chat_member = AsyncMock()
    bot.send_message = AsyncMock()
    bot.get_me = AsyncMock(return_value=Mock(
        id=bot.id,
        username=bot.username,
        first_name=bot.first_name
    ))

    return bot


@pytest_asyncio.fixture
async def container(test_session, mock_bot):
    """
    Fixture: ServiceContainer with test database and mock bot.

    Provides a fully configured ServiceContainer ready for testing:
    - Connected to in-memory test database
    - Mocked Telegram bot
    - All services available via lazy loading

    Args:
        test_session: Database session fixture
        mock_bot: Mocked Telegram bot fixture

    Yields:
        ServiceContainer: Configured container for testing
    """
    container = ServiceContainer(test_session, mock_bot)
    yield container


@pytest_asyncio.fixture
async def container_with_preload(container):
    """
    Fixture: ServiceContainer with critical services preloaded.

    Use this when you need immediate access to subscription/config
    services without triggering lazy loading during the test.

    Yields:
        ServiceContainer: Container with subscription and config loaded
    """
    await container.preload_critical_services()
    yield container
