"""
Tests for ProxyDispatcherFactory.
"""
import pytest
import httpx
from proxy_dispatcher import ProxyDispatcherFactory, FactoryConfig

class TestProxyDispatcherFactory:
    
    @pytest.mark.asyncio
    async def test_get_async_client(self):
        """Should create an async client."""
        factory = ProxyDispatcherFactory()
        result = factory.get_proxy_dispatcher(async_client=True)
        assert isinstance(result.client, httpx.AsyncClient)
        assert result.config.verify_ssl is True # Default
        
    def test_get_sync_client(self):
        """Should create a sync client."""
        factory = ProxyDispatcherFactory()
        result = factory.get_proxy_dispatcher(async_client=False)
        assert isinstance(result.client, httpx.Client)

    def test_proxy_url_override(self):
        """Should use proxy URL from config."""
        config = FactoryConfig(proxy_url="http://override")
        factory = ProxyDispatcherFactory(config=config)
        result = factory.get_proxy_dispatcher()
        assert result.config.proxy_url == "http://override"
        assert result.proxy_dict["proxy"] == "http://override"

    def test_ssl_disable(self):
        """Should disable SSL verification."""
        factory = ProxyDispatcherFactory()
        result = factory.get_proxy_dispatcher(disable_tls=True)
        assert result.config.verify_ssl is False
        assert result.proxy_dict["verify"] is False

    @pytest.mark.asyncio
    async def test_request_kwargs(self):
        """Should return kwargs for request."""
        factory = ProxyDispatcherFactory()
        kwargs = factory.get_request_kwargs(timeout=10.0)
        assert kwargs["timeout"] == 10.0
        assert "proxy" not in kwargs # No proxy configured by default
