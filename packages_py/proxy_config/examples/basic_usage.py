"""
Basic usage examples for proxy_config package.

This package provides proxy URL resolution logic with 8-level precedence.
"""
import os
from proxy_config import resolve_proxy_url, NetworkConfig, AgentProxyConfig


# =============================================================================
# Example 1: Simple resolution from environment variables
# =============================================================================
def example1_env_var_fallback() -> None:
    """
    When no config is provided, falls back to environment variables:
    1. PROXY_URL
    2. HTTPS_PROXY
    3. HTTP_PROXY
    """
    # Set environment variables (in real app, these come from .env or cloud config)
    os.environ["HTTPS_PROXY"] = "http://corporate-proxy:8080"

    proxy_url = resolve_proxy_url()
    print(f"Example 1 - ENV fallback: {proxy_url}")
    # Output: "http://corporate-proxy:8080"

    # Cleanup
    del os.environ["HTTPS_PROXY"]


# =============================================================================
# Example 2: Environment-specific proxy URLs
# =============================================================================
def example2_environment_specific() -> None:
    """
    Configure different proxy URLs per environment (dev, staging, prod).
    The `default_environment` determines which one is selected.
    """
    network_config = NetworkConfig(
        default_environment="prod",
        proxy_urls={
            "dev": "http://dev-proxy.internal:3128",
            "staging": "http://staging-proxy.internal:3128",
            "prod": "http://prod-proxy.internal:3128"
        }
    )

    proxy_url = resolve_proxy_url(network_config)
    print(f"Example 2 - Environment-specific: {proxy_url}")
    # Output: "http://prod-proxy.internal:3128"


# =============================================================================
# Example 3: Agent proxy configuration (highest priority in config)
# =============================================================================
def example3_agent_proxy() -> None:
    """
    Agent proxy settings take precedence over environment-specific URLs.
    Useful for per-request or per-service overrides.
    """
    network_config = NetworkConfig(
        default_environment="prod",
        proxy_urls={
            "prod": "http://prod-proxy:3128"
        },
        agent_proxy=AgentProxyConfig(
            https_proxy="http://special-https-proxy:8080",
            http_proxy="http://special-http-proxy:8080"
        )
    )

    proxy_url = resolve_proxy_url(network_config)
    print(f"Example 3 - Agent proxy: {proxy_url}")
    # Output: "http://special-https-proxy:8080" (https_proxy takes precedence)


# =============================================================================
# Example 4: Explicit override (highest priority)
# =============================================================================
def example4_explicit_override() -> None:
    """
    The `proxy_url_override` parameter takes absolute precedence.
    Use this for one-off requests or testing.
    """
    network_config = NetworkConfig(
        default_environment="prod",
        proxy_urls={
            "prod": "http://prod-proxy:3128"
        }
    )

    # Override with explicit URL
    proxy_url = resolve_proxy_url(network_config, proxy_url_override="http://test-proxy:9999")
    print(f"Example 4 - Explicit override: {proxy_url}")
    # Output: "http://test-proxy:9999"


# =============================================================================
# Example 5: Explicitly disable proxy
# =============================================================================
def example5_disable_proxy() -> None:
    """
    Pass `False` as override to explicitly disable proxy.
    Useful for local development or direct connections.
    """
    os.environ["HTTPS_PROXY"] = "http://corporate-proxy:8080"

    network_config = NetworkConfig(
        default_environment="prod",
        proxy_urls={
            "prod": "http://prod-proxy:3128"
        }
    )

    # Explicitly disable proxy
    proxy_url = resolve_proxy_url(network_config, proxy_url_override=False)
    print(f"Example 5 - Disabled proxy: {proxy_url}")
    # Output: None

    # Cleanup
    del os.environ["HTTPS_PROXY"]


# =============================================================================
# Example 6: Full precedence demonstration
# =============================================================================
def example6_full_precedence() -> None:
    """
    Demonstrates the full 8-level precedence hierarchy.

    Resolution order:
    1. proxy_url_override = False  -> None (disabled)
    2. proxy_url_override = string -> use override
    3. agent_proxy.https_proxy     -> agent HTTPS
    4. agent_proxy.http_proxy      -> agent HTTP
    5. proxy_urls[environment]     -> environment-specific
    6. PROXY_URL env var           -> generic env
    7. HTTPS_PROXY env var         -> HTTPS env
    8. HTTP_PROXY env var          -> HTTP env (lowest)
    """
    # Set all possible sources
    os.environ["HTTP_PROXY"] = "http://env-http:8080"
    os.environ["HTTPS_PROXY"] = "http://env-https:8080"
    os.environ["PROXY_URL"] = "http://env-proxy:8080"

    full_config = NetworkConfig(
        default_environment="prod",
        proxy_urls={
            "prod": "http://config-prod:3128"
        },
        agent_proxy=AgentProxyConfig(
            http_proxy="http://agent-http:3128",
            https_proxy="http://agent-https:3128"
        )
    )

    # Each level overrides the ones below it
    print("\nExample 6 - Full precedence:")
    print(f"1. Override False: {resolve_proxy_url(full_config, proxy_url_override=False)}")
    print(f"2. Override string: {resolve_proxy_url(full_config, proxy_url_override='http://explicit:9999')}")
    print(f"3. Agent HTTPS: {resolve_proxy_url(full_config)}")

    http_only_agent = NetworkConfig(
        default_environment="prod",
        proxy_urls={"prod": "http://config-prod:3128"},
        agent_proxy=AgentProxyConfig(http_proxy="http://agent-http:3128")
    )
    print(f"4. Agent HTTP: {resolve_proxy_url(http_only_agent)}")

    config_only = NetworkConfig(
        default_environment="prod",
        proxy_urls={"prod": "http://config-prod:3128"}
    )
    print(f"5. Config env: {resolve_proxy_url(config_only)}")
    print(f"6. PROXY_URL: {resolve_proxy_url()}")

    del os.environ["PROXY_URL"]
    print(f"7. HTTPS_PROXY: {resolve_proxy_url()}")

    del os.environ["HTTPS_PROXY"]
    print(f"8. HTTP_PROXY: {resolve_proxy_url()}")

    # Cleanup
    del os.environ["HTTP_PROXY"]


# =============================================================================
# Example 7: Integration with app_yaml_config (conceptual)
# =============================================================================
def example7_yaml_integration() -> None:
    """
    Shows how proxy_config integrates with app_yaml_config.
    The YAML global.network section maps directly to NetworkConfig.
    """
    # Simulated config loaded from app.yaml:
    # global:
    #   network:
    #     default_environment: "dev"
    #     proxy_urls:
    #       dev: "http://dev-proxy:3128"
    #       prod: "http://prod-proxy:3128"
    #     agent_proxy:
    #       https_proxy: "http://special:8080"

    yaml_network_section = {
        "default_environment": "dev",
        "proxy_urls": {
            "dev": "http://dev-proxy:3128",
            "prod": "http://prod-proxy:3128"
        },
        "agent_proxy": {
            "https_proxy": "http://special:8080"
        }
    }

    # Map YAML to NetworkConfig dataclass
    agent_proxy = None
    if yaml_network_section.get("agent_proxy"):
        agent_proxy = AgentProxyConfig(
            https_proxy=yaml_network_section["agent_proxy"].get("https_proxy"),
            http_proxy=yaml_network_section["agent_proxy"].get("http_proxy")
        )

    network_config = NetworkConfig(
        default_environment=yaml_network_section.get("default_environment"),
        proxy_urls=yaml_network_section.get("proxy_urls", {}),
        agent_proxy=agent_proxy
    )

    proxy_url = resolve_proxy_url(network_config)
    print(f"Example 7 - YAML integration: {proxy_url}")
    # Output: "http://special:8080" (agent_proxy takes precedence)


# =============================================================================
# Example 8: Using with httpx directly
# =============================================================================
def example8_httpx_usage() -> None:
    """
    Shows how to use resolved proxy URL with httpx library.
    """
    network_config = NetworkConfig(
        default_environment="prod",
        proxy_urls={
            "prod": "http://prod-proxy:3128"
        }
    )

    proxy_url = resolve_proxy_url(network_config)

    # Use with httpx
    # import httpx
    #
    # if proxy_url:
    #     client = httpx.Client(proxy=proxy_url)
    # else:
    #     client = httpx.Client()
    #
    # response = client.get("https://api.example.com")

    print(f"Example 8 - httpx usage: proxy_url={proxy_url}")
    print("  -> httpx.Client(proxy=proxy_url)")


# =============================================================================
# Run all examples
# =============================================================================
def main() -> None:
    print("=== proxy_config Examples ===\n")

    example1_env_var_fallback()
    example2_environment_specific()
    example3_agent_proxy()
    example4_explicit_override()
    example5_disable_proxy()
    example6_full_precedence()
    example7_yaml_integration()
    example8_httpx_usage()

    print("\n=== Examples Complete ===")


if __name__ == "__main__":
    main()
