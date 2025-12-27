
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fetch_client.health.status_checker import FetchStatusChecker
from fetch_client.health.models import FetchStatus, FetchStatusResult

class MockRuntimeConfig:
    def __init__(self, config=None, auth_config=None, proxy_config=None, headers=None):
        self.config = config or {}
        self.auth_config = auth_config
        self.proxy_config = proxy_config
        self.headers = headers or {}

@pytest.fixture
def base_runtime_config():
    return MockRuntimeConfig(
        config={"base_url": "https://api.example.com", "health_endpoint": "/health"},
        headers={}
    )

@pytest.mark.asyncio
async def test_check_delegates_to_provider_client(base_runtime_config):
    # Mock ProviderClient where it is defined
    with patch("fetch_client.provider.provider_client.ProviderClient") as MockProvider:
        mock_instance = MockProvider.return_value
        expected_result = FetchStatusResult(
            provider_name="test-provider",
            status=FetchStatus.CONNECTED,
            latency_ms=10.0,
            timestamp="2024-01-01T00:00:00Z"
        )
        mock_instance.check_health = AsyncMock(return_value=expected_result)
        mock_instance.close = AsyncMock()
        mock_instance.options = MagicMock() # Simulate options access

        checker = FetchStatusChecker("test-provider", base_runtime_config, timeout_seconds=5.0)
        result = await checker.check()

        assert result == expected_result
        MockProvider.assert_called_once()
        # Verify options were set
        assert mock_instance.options.timeout_seconds == 5.0
        mock_instance.check_health.assert_awaited_once()
        mock_instance.close.assert_awaited_once()

@pytest.mark.asyncio
async def test_check_handles_config_error(base_runtime_config):
    with patch("fetch_client.provider.provider_client.ProviderClient") as MockProvider:
        # Simulate constructor raising ValueError (e.g. invalid config)
        MockProvider.side_effect = ValueError("Invalid config")
        
        checker = FetchStatusChecker("test-provider", base_runtime_config)
        result = await checker.check()
        
        assert result.status == FetchStatus.CONFIG_ERROR
        assert result.error["type"] == "ConfigError"
        assert "Invalid config" in result.error["message"]

