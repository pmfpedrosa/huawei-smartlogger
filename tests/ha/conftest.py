import pytest


@pytest.fixture(autouse=True)
def custom_integrations(enable_custom_integrations):
    """Enable loading the repository's real integration in Home Assistant."""
    yield
