"""
Test: Verify pytest-asyncio auto mode works without decorators.

This test validates that pytest.ini asyncio_mode=auto is properly configured
and async tests run without requiring @pytest.mark.asyncio decorator.
"""
import asyncio


async def test_async_mode_works():
    """
    Test: Async test runs without @pytest.mark.asyncio decorator.

    If this test passes, it confirms pytest-asyncio is configured correctly
    with asyncio_mode=auto in pytest.ini.
    """
    await asyncio.sleep(0.001)
    assert True


async def test_async_assertions_work():
    """
    Test: Async assertions work in auto mode.
    """
    result = await async_helper()
    assert result == "success"


async def async_helper() -> str:
    """Helper async function for testing."""
    await asyncio.sleep(0.001)
    return "success"


class TestAsyncMode:
    """Test class: Async methods work without decorator."""

    async def test_async_in_class(self):
        """Test: Async test method in class works."""
        await asyncio.sleep(0.001)
        assert True

    async def test_async_with_fixture(self, mock_bot):
        """Test: Async test with fixture works."""
        await asyncio.sleep(0.001)
        assert mock_bot.id == 123456789
