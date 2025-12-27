
import pytest
from unittest.mock import MagicMock, AsyncMock
from fetch_client.health.status_checker import FetchStatusChecker
from fetch_client.health.models import FetchStatus

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
async def test_resolve_method_defaults_to_get(base_runtime_config):
    checker = FetchStatusChecker("test-provider", base_runtime_config)
    assert checker._resolve_method() == "GET"

@pytest.mark.asyncio
async def test_resolve_method_from_top_level(base_runtime_config):
    base_runtime_config.config["method"] = "post"
    checker = FetchStatusChecker("test-provider", base_runtime_config)
    assert checker._resolve_method() == "POST"

@pytest.mark.asyncio
async def test_resolve_method_from_health_endpoint_dict(base_runtime_config):
    base_runtime_config.config["health_endpoint"] = {"path": "/health", "method": "head"}
    checker = FetchStatusChecker("test-provider", base_runtime_config)
    assert checker._resolve_method() == "HEAD"
    # Also verify health endpoint resolution works (this might fail currently)
    assert checker._resolve_health_endpoint() == "/health"

@pytest.mark.asyncio
async def test_config_used_structure(base_runtime_config):
    checker = FetchStatusChecker("test-provider", base_runtime_config)
    config_used = checker._build_config_used("/health", "GET")
    assert config_used["method"] == "GET"
    assert config_used["timeout_seconds"] == 10.0
    assert "proxy_resolved" in config_used

@pytest.mark.asyncio
async def test_fetch_option_used_masking(base_runtime_config):
    checker = FetchStatusChecker("test-provider", base_runtime_config)
    merged_headers = {"Authorization": "Bearer secret-token", "User-Agent": "test-agent"}
    
    options = checker._build_fetch_option_used("GET", "https://api.example.com/health", merged_headers)
    
    assert options["method"] == "GET"
    assert options["headers"]["Authorization"] == "****"
    assert options["headers"]["User-Agent"] == "test-agent"

@pytest.mark.asyncio
async def test_proxy_masking(base_runtime_config):
    mock_proxy = MagicMock()
    mock_proxy.proxy_url = "http://user:pass@proxy.com:8080"
    base_runtime_config.proxy_config = mock_proxy
    
    checker = FetchStatusChecker("test-provider", base_runtime_config)
    options = checker._build_fetch_option_used("GET", "url", {})
    
    assert options["proxy"] == "http://user:****@proxy.com:8080"
