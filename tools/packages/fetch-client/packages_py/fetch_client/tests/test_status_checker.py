"""
Tests for FetchStatusChecker.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fetch_client.health import FetchStatusChecker, FetchStatus

from types import SimpleNamespace

@pytest.fixture
def mock_runtime_config():
    """Create mock runtime config."""
    config = SimpleNamespace()
    config.config = {
        "base_url": "https://api.example.com",
        "headers": {"Accept": "application/json"},
    }
    config.auth_config = SimpleNamespace()
    config.auth_config.type = SimpleNamespace(value="bearer")
    config.auth_config.token = "test-token"
    # Additional fields needed for conversion/logging
    config.auth_config.username = None
    config.auth_config.password = None
    config.auth_config.email = None
    config.auth_config.header_name = None
    
    config.auth_config.resolution = SimpleNamespace(is_placeholder=False)
    config.proxy_config = None
    return config


@pytest.mark.asyncio
async def test_successful_connection(mock_runtime_config):
    """Test successful provider connection."""
    with patch('fetch_client.health.status_checker.FetchClient') as MockFetchClient:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.status_text = "OK"
        mock_response.headers = {"content-type": "application/json"}
        mock_response.data = {"models": []}
        
        mock_client.get.return_value = mock_response
        MockFetchClient.create.return_value = mock_client

        checker = FetchStatusChecker(
            provider_name="test",
            runtime_config=mock_runtime_config,
        )
        result = await checker.check()

        if result.status != FetchStatus.CONNECTED:
            print(f"DEBUG ERROR: {result.error}")

        assert result.status == FetchStatus.CONNECTED
        assert result.latency_ms > 0
        assert result.response["status_code"] == 200


@pytest.mark.asyncio
async def test_timeout_error(mock_runtime_config):
    """Test timeout handling."""
    import httpx

    with patch('fetch_client.health.status_checker.FetchClient') as MockFetchClient:
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.TimeoutException("timeout")
        MockFetchClient.create.return_value = mock_client

        checker = FetchStatusChecker(
            provider_name="test",
            runtime_config=mock_runtime_config,
        )
        result = await checker.check()

        assert result.status == FetchStatus.TIMEOUT
        assert result.error["type"] == "TimeoutException"

@pytest.mark.asyncio
async def test_config_error_missing_base_url():
    """Test config error when base_url is missing."""
    config = MagicMock()
    config.config = {} # No base_url
    
    checker = FetchStatusChecker(
            provider_name="test",
            runtime_config=config,
    )
    result = await checker.check()
    
    assert result.status == FetchStatus.CONFIG_ERROR
    assert result.error["message"] == "base_url is required"
