import pytest
from starlette.testclient import TestClient

from server.core.config import settings


@pytest.fixture
def client():
    """Test client with a test API key, using the real database."""
    # Set a test API key so auth tests can verify 401 responses
    old_key = settings.UNIFIED_API_KEY
    settings.UNIFIED_API_KEY = "test-key-for-testing"

    from server.main import app
    with TestClient(app) as c:
        yield c

    settings.UNIFIED_API_KEY = old_key


@pytest.fixture(scope="session", autouse=True)
async def _dispose_engine():
    """Dispose the async engine after all tests to avoid unclosed connection warnings."""
    yield
    from server.core.database import async_engine
    await async_engine.dispose()
