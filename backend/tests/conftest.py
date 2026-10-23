import pytest
from app.config import get_settings


@pytest.fixture(autouse=True)
def configure_test_environment():
    """
    Ensures unit and integration tests execute deterministically against MockLLM
    regardless of external .env configuration.
    """
    settings = get_settings()
    original_provider = settings.LLM_PROVIDER
    settings.LLM_PROVIDER = "mock"
    yield
    settings.LLM_PROVIDER = original_provider
