"""
Basic usage examples for proxy_dispatcher package.

This package provides HTTP client factory with proxy configuration.
"""
import asyncio
from proxy_dispatcher import (
    ProxyDispatcherFactory,
    FactoryConfig,
    get_proxy_dispatcher,
    get_async_client,
    get_sync_client,
    get_request_kwargs,
    create_proxy_dispatcher_factory
)


# =============================================================================
# Example 1: Create factory with environment-specific proxy URLs
# =============================================================================
async def example1_factory_with_env_proxy() -> None:
    """
    >>> factory = ProxyDispatcherFactory(
    ...     config=FactoryConfig(
    ...         proxy_urls=ProxyUrlConfig(
    ...             PROD="http://proxy.company.com:8080",
    ...             QA="http://qa-proxy.company.com:8080",
    ...         ),
    ...     ),
    ... )
    >>> result = factory.get_proxy_dispatcher()
    >>> async with result.client as client:
    ...     response = await client.get("https://api.example.com")
    """
    factory = ProxyDispatcherFactory(
        config=FactoryConfig(
            proxy_urls={
                "PROD": "http://proxy.company.com:8080",
                "QA": "http://qa-proxy.company.com:8080",
                "dev": "http://dev-proxy:3128"
            },
            default_environment="dev"
        )
    )

    result = factory.get_proxy_dispatcher()

    print("Example 1 - Factory with env proxy:")
    print(f"  proxy_url: {result.config.proxy_url}")
    print(f"  verify_ssl: {result.config.verify_ssl}")
    print(f"  timeout: {result.config.timeout}")

    # Use the client (httpx.AsyncClient)
    # async with result.client as client:
    #     response = await client.get("https://api.example.com")


# =============================================================================
# Example 2: Get request kwargs for direct HTTP calls
# =============================================================================
def example2_get_request_kwargs() -> None:
    """
    >>> factory = ProxyDispatcherFactory(...)
    >>> kwargs = factory.get_request_kwargs("QA")
    >>> response = httpx.post("https://api.example.com", json=data, **kwargs)
    """
    factory = ProxyDispatcherFactory(
        config=FactoryConfig(
            proxy_urls={
                "QA": "http://qa-proxy:8080",
                "PROD": "http://prod-proxy:8080"
            },
            default_environment="QA",
            cert_verify=True
        )
    )

    kwargs = factory.get_request_kwargs(timeout=30.0)

    print("\nExample 2 - Get request kwargs:")
    print(f"  kwargs: {kwargs}")

    # Use with httpx directly
    # import httpx
    # response = httpx.post("https://api.example.com", json=data, **kwargs)


# =============================================================================
# Example 3: Convenience function for quick scripts
# =============================================================================
def example3_convenience_function() -> None:
    """
    >>> factory = create_proxy_dispatcher_factory(
    ...     config=FactoryConfig(
    ...         proxy_urls=ProxyUrlConfig(PROD="http://proxy:8080"),
    ...     ),
    ... )
    >>> result = factory.get_proxy_dispatcher()
    """
    # Using the convenience factory creator
    factory = create_proxy_dispatcher_factory(
        config=FactoryConfig(
            proxy_urls={
                "PROD": "http://proxy:8080"
            }
        )
    )

    result = factory.get_proxy_dispatcher()

    print("\nExample 3 - Convenience function:")
    print(f"  proxy_url: {result.config.proxy_url}")

    # Or use global convenience functions (uses env vars)
    global_result = get_proxy_dispatcher()
    print(f"  global_result.proxy_url: {global_result.config.proxy_url}")


# =============================================================================
# Example 4: Get async/sync clients directly
# =============================================================================
async def example4_get_clients() -> None:
    """
    Convenience functions to get pre-configured httpx clients.
    """
    # Get async client
    async_client = get_async_client(timeout=30.0)
    print("\nExample 4 - Get clients:")
    print(f"  async_client: {type(async_client).__name__}")

    # Get sync client
    sync_client = get_sync_client(timeout=30.0)
    print(f"  sync_client: {type(sync_client).__name__}")

    # Get kwargs for manual client creation
    kwargs = get_request_kwargs(timeout=30.0)
    print(f"  request_kwargs: {list(kwargs.keys())}")

    # Clean up
    await async_client.aclose()
    sync_client.close()


# =============================================================================
# Example 5: Environment-specific dispatcher
# =============================================================================
def example5_environment_specific() -> None:
    """
    Get dispatchers for specific environments.
    """
    factory = ProxyDispatcherFactory(
        config=FactoryConfig(
            proxy_urls={
                "dev": "http://dev-proxy:3128",
                "staging": "http://staging-proxy:3128",
                "prod": "http://prod-proxy:3128"
            }
        )
    )

    # Get dispatcher for specific environment
    dev_dispatcher = factory.get_dispatcher_for_environment("dev")
    prod_dispatcher = factory.get_dispatcher_for_environment("prod")

    print("\nExample 5 - Environment-specific:")
    print(f"  dev proxy: {dev_dispatcher.config.proxy_url}")
    print(f"  prod proxy: {prod_dispatcher.config.proxy_url}")


# =============================================================================
# Example 6: Full configuration with SSL and certificates
# =============================================================================
def example6_full_config() -> None:
    """
    Full configuration with SSL verification and certificates.
    """
    factory = ProxyDispatcherFactory(
        config=FactoryConfig(
            proxy_urls={
                "prod": "http://secure-proxy:8080"
            },
            default_environment="prod",
            cert_verify=True,
            cert="/path/to/client-cert.pem",
            ca_bundle="/path/to/ca-bundle.crt"
        )
    )

    result = factory.get_proxy_dispatcher(
        timeout=60.0,
        disable_tls=False
    )

    print("\nExample 6 - Full config:")
    print(f"  proxy_url: {result.config.proxy_url}")
    print(f"  verify_ssl: {result.config.verify_ssl}")
    print(f"  cert: {result.config.cert}")
    print(f"  ca_bundle: {result.config.ca_bundle}")


# =============================================================================
# Example 7: Disable proxy explicitly
# =============================================================================
def example7_disable_proxy() -> None:
    """
    Explicitly disable proxy even if env vars are set.
    """
    factory = ProxyDispatcherFactory(
        config=FactoryConfig(
            proxy_urls={
                "prod": "http://prod-proxy:8080"
            },
            proxy_url=False  # Explicitly disable
        )
    )

    result = factory.get_proxy_dispatcher()

    print("\nExample 7 - Disable proxy:")
    print(f"  proxy_url: {result.config.proxy_url}")  # None


# =============================================================================
# Example 8: Override proxy URL
# =============================================================================
def example8_override_proxy() -> None:
    """
    Override proxy URL (takes precedence over env-specific).
    """
    factory = ProxyDispatcherFactory(
        config=FactoryConfig(
            proxy_urls={
                "prod": "http://prod-proxy:8080"
            },
            proxy_url="http://override-proxy:9999"  # Takes precedence
        )
    )

    result = factory.get_proxy_dispatcher()

    print("\nExample 8 - Override proxy:")
    print(f"  proxy_url: {result.config.proxy_url}")  # http://override-proxy:9999


# =============================================================================
# Example 9: Integration with FastAPI (dependency injection)
# =============================================================================
def example9_fastapi_integration() -> None:
    """
    See examples/fastapi_app/main.py for full example.
    """
    import os

    factory_config = FactoryConfig(
        default_environment=os.getenv("APP_ENV", "dev"),
        proxy_urls={
            "dev": "http://dev-proxy:3128",
            "prod": "http://prod-proxy:3128"
        }
    )

    # Create singleton factory at app startup
    factory = ProxyDispatcherFactory(config=factory_config)

    # In FastAPI dependencies:
    # async def get_http_client():
    #     result = factory.get_proxy_dispatcher(async_client=True)
    #     async with result.client as client:
    #         yield client

    print("\nExample 9 - FastAPI integration:")
    print(f"  Factory created with default_env: {factory_config.default_environment}")
    print("  See examples/fastapi_app/ for full integration")


# =============================================================================
# Example 10: Real HTTP request with proxy
# =============================================================================
async def example10_real_request() -> None:
    """
    Make a real HTTP request using the proxy dispatcher.
    """
    factory = ProxyDispatcherFactory(
        config=FactoryConfig(
            proxy_urls={
                "dev": None  # No proxy for dev
            },
            default_environment="dev"
        )
    )

    result = factory.get_proxy_dispatcher(async_client=True)

    print("\nExample 10 - Real request:")
    print(f"  proxy_url: {result.config.proxy_url}")
    print(f"  client type: {type(result.client).__name__}")

    # Uncomment to make actual request:
    # async with result.client as client:
    #     response = await client.get("https://httpbin.org/get")
    #     print(f"  status: {response.status_code}")


# =============================================================================
# Run all examples
# =============================================================================
async def main() -> None:
    print("=== proxy_dispatcher Examples ===\n")

    await example1_factory_with_env_proxy()
    example2_get_request_kwargs()
    example3_convenience_function()
    await example4_get_clients()
    example5_environment_specific()
    example6_full_config()
    example7_disable_proxy()
    example8_override_proxy()
    example9_fastapi_integration()
    await example10_real_request()

    print("\n=== Examples Complete ===")


if __name__ == "__main__":
    asyncio.run(main())
