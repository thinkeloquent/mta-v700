
import pytest
from unittest.mock import AsyncMock, Mock, patch, ANY
from types import SimpleNamespace
from typing import Any, Dict

from fetch_client.provider.provider_client import ProviderClient, ProviderClientOptions
from fetch_client.health.models import FetchStatus
from fetch_client.client import FetchClient
from fetch_client.config import AuthConfig
from httpx import ConnectError, TimeoutException, Response

# Setup dummy config structure
def create_runtime_config(
    config: Dict[str, Any], 
    headers: Dict[str, str] = None, 
    auth_config: Any = None
) -> SimpleNamespace:
    return SimpleNamespace(
        config=config,
        headers=headers or {},
        auth_config=auth_config,
        proxy_config=SimpleNamespace(proxy_url=None)
    )

@pytest.fixture
def mock_fetch_client():
    with patch("fetch_client.provider.provider_client.FetchClient") as mock:
        client_instance = AsyncMock()
        mock.create.return_value = client_instance
        yield mock, client_instance

@pytest.fixture
def valid_config():
    return create_runtime_config(
        config={
            "base_url": "https://api.example.com",
            "health_endpoint": "/health",
            "headers": {"X-Config": "val"}
        },
        headers={"X-Precomputed": "val", "Authorization": "Bearer token"},
        auth_config=SimpleNamespace(username="testuser", type="bearer", token="token")
    )

@pytest.mark.asyncio
async def test_init_validation():
    with pytest.raises(ValueError, match="base_url is required"):
        ProviderClient("test", create_runtime_config({}))

@pytest.mark.asyncio
async def test_client_creation(mock_fetch_client, valid_config):
    mock_cls, mock_instance = mock_fetch_client
    
    provider = ProviderClient("test", valid_config)
    mock_instance.request.return_value = FetchResponseStub(200, {})
    
    await provider.get("/foo")
    
    # Check factory called
    mock_cls.create.assert_called_once()
    config_arg = mock_cls.create.call_args[0][0]
    
    assert config_arg.base_url == "https://api.example.com"
    # Should use merged headers
    assert config_arg.headers["X-Config"] == "val"
    assert config_arg.headers["Authorization"] == "Bearer token"

@pytest.mark.asyncio
async def test_request_delegation(mock_fetch_client, valid_config):
    _, mock_instance = mock_fetch_client
    mock_instance.request.return_value = FetchResponseStub(200, "ok")
    
    provider = ProviderClient("test", valid_config)
    await provider.get("/foo?q=1")
    
    mock_instance.get.assert_called_once_with("/foo?q=1", params=None, headers=None, timeout=None)

@pytest.mark.asyncio
async def test_check_health_success(mock_fetch_client, valid_config):
    _, mock_instance = mock_fetch_client
    mock_instance.request.return_value = FetchResponseStub(200, {"status": "ok"})
    
    provider = ProviderClient("test", valid_config)
    result = await provider.check_health()
    
    assert result.status == FetchStatus.CONNECTED
    assert result.response["status_code"] == 200
    mock_instance.request.assert_called_once()

@pytest.mark.asyncio
async def test_check_health_placeholders(mock_fetch_client):
    mock_cls, mock_instance = mock_fetch_client
    mock_instance.request.return_value = FetchResponseStub(200, {})
    
    config = create_runtime_config(
        config={
            "base_url": "http://api.com",
            "health_endpoint": "/users/:username/health"
        },
        auth_config=SimpleNamespace(username="alice")
    )
    
    provider = ProviderClient("test", config)
    await provider.check_health()
    
    # Verify we requested the resolved URL (though client.request arg structure depends on usage in provider)
    # Provider calls client.request(RequestBuilder(...).build())
    # We can inspect the Request object passed
    mock_instance.request.assert_called_once()
    req_obj = mock_instance.request.call_args[0][0]
    # Request object handling might be opaque if it's the internal core request object
    # But we can assume url is correctly set in it if we mocked correctly.
    # Actually, provider logic converts request options.
    assert req_obj["url"] == "/users/alice/health"

@pytest.mark.asyncio
async def test_check_health_timeout(mock_fetch_client, valid_config):
    _, mock_instance = mock_fetch_client
    mock_instance.connect = AsyncMock()
    mock_instance.request.side_effect = TimeoutException("Timed out")
    
    provider = ProviderClient("test", valid_config)
    result = await provider.check_health()
    
    assert result.status == FetchStatus.TIMEOUT
    assert result.error["type"] == "TimeoutException"

@pytest.mark.asyncio
async def test_check_health_config_error(mock_fetch_client):
    # Missing optional path in health_endpoint dict
    config = create_runtime_config({
        "base_url": "http://api.com",
        "health_endpoint": {"invalid": "key"} # Invalid
    })
    
    provider = ProviderClient("test", config)
    result = await provider.check_health()
    
    assert result.status == FetchStatus.CONFIG_ERROR
    assert "missing 'path'" in result.error["message"]

def test_diagnostics(valid_config):
    provider = ProviderClient("test", valid_config)
    
    conf = provider.get_config_used()
    assert conf.base_url == "https://api.example.com"
    assert conf.health_endpoint == "/health"
    assert conf.auth_header_present is True
    
    opts = provider.get_fetch_option_used()
    assert opts.headers["Authorization"] == "****"
    assert opts.headers["X-Config"] == "val"

# Stub for FetchResponse since we don't want to rely on real one
class FetchResponseStub:
    def __init__(self, status, data, headers=None):
        self.status = status
        self.data = data
        self.headers = headers or {"content-type": "application/json"}
        self.status_text = "OK" if status == 200 else "Error"
