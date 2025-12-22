"""
Tests for proxy URL resolution.
"""
import pytest
from proxy_config import resolve_proxy_url, NetworkConfig, AgentProxyConfig

class TestResolveProxyUrl:
    def test_explicit_disable(self):
        """Should return None when override is False."""
        assert resolve_proxy_url(proxy_url_override=False) is None

    def test_explicit_override(self):
        """Should return override string."""
        assert resolve_proxy_url(proxy_url_override="http://override") == "http://override"

    def test_agent_proxy_priority(self):
        """Agent proxy should take precedence over env config."""
        config = NetworkConfig(
            agent_proxy=AgentProxyConfig(https_proxy="http://agent-https"),
            proxy_urls={"dev": "http://dev-proxy"}
        )
        assert resolve_proxy_url(network_config=config) == "http://agent-https"

    def test_env_config(self):
        """Should use environment specific proxy."""
        config = NetworkConfig(
            default_environment="stage",
            proxy_urls={"stage": "http://stage-proxy"}
        )
        assert resolve_proxy_url(network_config=config) == "http://stage-proxy"

    def test_env_var_fallback(self, monkeypatch):
        """Should fall back to env vars."""
        monkeypatch.setenv("PROXY_URL", "http://env-proxy")
        assert resolve_proxy_url() == "http://env-proxy"
