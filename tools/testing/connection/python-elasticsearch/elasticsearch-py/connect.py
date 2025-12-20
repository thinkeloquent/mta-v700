"""
elasticsearch-py Connection Test (v8.19.0+)

Tests Elasticsearch Python client connectivity with:
- URL builder (schema, host, port, index)
- Proxy support
- SSL/TLS configuration
- AsyncElasticsearch client
- Various authentication methods (API Key, Basic Auth)
- Error handling for DNS resolution and connection errors

Requirements:
    pip install elasticsearch==8.19.0
"""
import asyncio
import os
import socket
import ssl

try:
    from elasticsearch import AsyncElasticsearch
    ES_AVAILABLE = True
except ImportError:
    ES_AVAILABLE = False
    AsyncElasticsearch = None

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def format_connection_error(e: Exception, host: str = None) -> str:
    """
    Format connection errors with helpful messages.

    Handles common errors:
    - DNS resolution failures (Errno 8, nodename nor servname)
    - Connection refused
    - Connection timeout
    - SSL certificate errors

    Args:
        e: The exception that was raised
        host: The host that was being connected to

    Returns:
        Formatted error message with troubleshooting hints
    """
    error_str = str(e)
    error_lower = error_str.lower()

    # DNS resolution error (Errno 8: nodename nor servname provided, or not known)
    if "nodename nor servname" in error_lower or "errno 8" in error_lower or "name or service not known" in error_lower:
        msg = f"DNS_ERROR: Cannot resolve hostname"
        if host:
            msg += f" '{host}'"
        msg += "\n    Possible causes:"
        msg += "\n    - Hostname is misspelled or invalid"
        msg += "\n    - DNS server is unreachable"
        msg += "\n    - Host does not exist"
        msg += "\n    - Network connectivity issues"
        msg += f"\n    Original error: {e}"
        return msg

    # Connection refused
    if "connection refused" in error_lower or "errno 111" in error_lower or "errno 61" in error_lower:
        msg = f"CONNECTION_REFUSED: Server is not accepting connections"
        if host:
            msg += f" on '{host}'"
        msg += "\n    Possible causes:"
        msg += "\n    - Elasticsearch service is not running"
        msg += "\n    - Wrong port number"
        msg += "\n    - Firewall blocking connection"
        msg += f"\n    Original error: {e}"
        return msg

    # Connection timeout
    if "timed out" in error_lower or "timeout" in error_lower:
        msg = f"CONNECTION_TIMEOUT: Connection timed out"
        if host:
            msg += f" for '{host}'"
        msg += "\n    Possible causes:"
        msg += "\n    - Server is overloaded or unresponsive"
        msg += "\n    - Network latency issues"
        msg += "\n    - Firewall silently dropping packets"
        msg += f"\n    Original error: {e}"
        return msg

    # SSL certificate errors
    if "ssl" in error_lower or "certificate" in error_lower:
        msg = f"SSL_ERROR: SSL/TLS connection failed"
        msg += "\n    Possible causes:"
        msg += "\n    - Invalid or expired SSL certificate"
        msg += "\n    - Self-signed certificate not trusted"
        msg += "\n    - Wrong CA certificate configured"
        msg += "\n    Try: Set ELASTICSEARCH_VERIFY_CERTS=false for testing"
        msg += f"\n    Original error: {e}"
        return msg

    # Authentication errors
    if "401" in error_str or "unauthorized" in error_lower or "authentication" in error_lower:
        msg = f"AUTH_ERROR: Authentication failed"
        msg += "\n    Possible causes:"
        msg += "\n    - Invalid API key"
        msg += "\n    - Wrong username/password"
        msg += "\n    - API key expired or revoked"
        msg += f"\n    Original error: {e}"
        return msg

    # Generic error
    return f"{type(e).__name__}: {e}"


def validate_host(host: str) -> tuple[bool, str]:
    """
    Validate hostname before attempting connection.

    Args:
        host: Hostname to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not host:
        return False, "Host is empty or not set"

    if host == "localhost" or host == "127.0.0.1":
        return True, ""

    try:
        socket.gethostbyname(host)
        return True, ""
    except socket.gaierror as e:
        return False, f"Cannot resolve hostname '{host}': {e}"


def build_url(
    scheme: str = "http",
    host: str = "localhost",
    port: int = 9200,
    index: str = None,
    path: str = None,
) -> str:
    """
    Build Elasticsearch URL from components.

    Args:
        scheme: http or https
        host: Elasticsearch host
        port: Elasticsearch port
        index: Optional index name
        path: Optional path (e.g., "_search", "_doc/1")

    Returns:
        Full URL string
    """
    url = f"{scheme}://{host}:{port}"
    if index:
        url = f"{url}/{index}"
    if path:
        url = f"{url}/{path}"
    return url


def get_es_config():
    """Get Elasticsearch configuration from environment."""
    # Priority: ELASTIC_DB_* > ELASTICSEARCH_* > defaults
    return {
        "scheme": os.getenv("ELASTIC_DB_SCHEME", os.getenv("ELASTICSEARCH_SCHEME", "https")),
        "host": os.getenv("ELASTIC_DB_HOST", os.getenv("ELASTICSEARCH_HOST", "localhost")),
        "port": int(os.getenv("ELASTIC_DB_PORT", os.getenv("ELASTICSEARCH_PORT", "9200"))),
        "user": os.getenv("ELASTIC_DB_USERNAME", os.getenv("ELASTICSEARCH_USER", "")),
        "password": os.getenv("ELASTIC_DB_PASSWORD", os.getenv("ELASTICSEARCH_PASSWORD", "")),
        "api_key": os.getenv("ELASTIC_DB_API_KEY", os.getenv("ELASTICSEARCH_API_KEY", "")),
        "index": os.getenv("ELASTIC_DB_INDEX", os.getenv("ELASTICSEARCH_INDEX", "")),
        # SSL settings
        "verify_certs": os.getenv("ELASTIC_DB_VERIFY_CERTS", os.getenv("ELASTICSEARCH_VERIFY_CERTS", "false")).lower() == "true",
        "ssl_show_warn": os.getenv("ELASTIC_DB_SSL_SHOW_WARN", os.getenv("ELASTICSEARCH_SSL_SHOW_WARN", "false")).lower() == "true",
        "ca_certs": os.getenv("ELASTIC_DB_CA_CERTS", os.getenv("ELASTICSEARCH_CA_CERTS", "")),
        "client_cert": os.getenv("ELASTIC_DB_CLIENT_CERT", os.getenv("ELASTICSEARCH_CLIENT_CERT", "")),
        "client_key": os.getenv("ELASTIC_DB_CLIENT_KEY", os.getenv("ELASTICSEARCH_CLIENT_KEY", "")),
        # Proxy settings
        "http_proxy": os.getenv("HTTP_PROXY", os.getenv("http_proxy", "")),
        "https_proxy": os.getenv("HTTPS_PROXY", os.getenv("https_proxy", "")),
    }


def get_ssl_config(config: dict) -> dict:
    """
    Build SSL configuration dictionary.

    Args:
        config: Configuration dictionary

    Returns:
        SSL config kwargs for AsyncElasticsearch
    """
    ssl_config = {
        "verify_certs": config.get("verify_certs", False),
        "ssl_show_warn": config.get("ssl_show_warn", False),
    }

    # Optional CA certs
    if config.get("ca_certs"):
        ssl_config["ca_certs"] = config["ca_certs"]

    # Optional client certificate
    if config.get("client_cert"):
        ssl_config["client_cert"] = config["client_cert"]

    # Optional client key
    if config.get("client_key"):
        ssl_config["client_key"] = config["client_key"]

    return ssl_config


def get_proxy_url(config: dict) -> str | None:
    """Get proxy URL based on scheme."""
    scheme = config.get("scheme", "https")
    if scheme == "https":
        return config.get("https_proxy") or None
    return config.get("http_proxy") or None


def create_async_client(url: str, config: dict) -> AsyncElasticsearch:
    """
    Create AsyncElasticsearch client with proper authentication.

    Priority:
    1. API Key authentication
    2. Basic Auth (username/password)
    3. No authentication

    Args:
        url: Elasticsearch URL
        config: Configuration dictionary

    Returns:
        AsyncElasticsearch client instance
    """
    ssl_config = get_ssl_config(config)

    # Check for API Key authentication
    if url and config.get("api_key"):
        return AsyncElasticsearch(
            url,
            api_key=config["api_key"],
            **ssl_config,
        )

    # Check for Basic Auth
    if url and config.get("user") and config.get("password"):
        return AsyncElasticsearch(
            url,
            basic_auth=(config["user"], config["password"]),
            **ssl_config,
        )

    # No authentication
    return AsyncElasticsearch(
        url,
        **ssl_config,
    )


async def check_index_exists(client: AsyncElasticsearch, index: str) -> bool:
    """
    Check if an index exists.

    Args:
        client: AsyncElasticsearch client
        index: Index name to check

    Returns:
        True if index exists, False otherwise
    """
    try:
        return await client.indices.exists(index=index)
    except Exception as e:
        print(f"    Error checking index: {e}")
        return False


async def run_tests():
    """Run all connection tests."""
    config = get_es_config()
    proxy_url = get_proxy_url(config)

    # Build base URL
    base_url = build_url(
        scheme=config["scheme"],
        host=config["host"],
        port=config["port"],
    )

    print("=" * 60)
    print("elasticsearch-py AsyncElasticsearch Connection Test")
    print("=" * 60)

    print(f"\nConfig:")
    print(f"  Scheme: {config['scheme']}")
    print(f"  Host: {config['host']}")
    print(f"  Port: {config['port']}")
    print(f"  User: {config['user'] or 'N/A'}")
    print(f"  API Key: {'set' if config['api_key'] else 'not set'}")
    print(f"  Index: {config['index'] or 'N/A'}")
    print(f"  Proxy: {proxy_url or 'N/A'}")

    print(f"\nSSL Config:")
    print(f"  verify_certs: {config['verify_certs']}")
    print(f"  ssl_show_warn: {config['ssl_show_warn']}")
    print(f"  ca_certs: {config['ca_certs'] or 'N/A'}")
    print(f"  client_cert: {config['client_cert'] or 'N/A'}")
    print(f"  client_key: {config['client_key'] or 'N/A'}")

    print(f"\n  Base URL: {base_url}")

    if config["index"]:
        index_url = build_url(
            scheme=config["scheme"],
            host=config["host"],
            port=config["port"],
            index=config["index"],
        )
        print(f"  Index URL: {index_url}")

    # Validate host before running tests
    print("\n[Pre-flight] Validating hostname...")
    is_valid, error_msg = validate_host(config["host"])
    if not is_valid:
        print(f"  WARNING: {error_msg}")
        print("  Tests will likely fail. Check ELASTICSEARCH_HOST environment variable.")
    else:
        print(f"  OK: Hostname '{config['host']}' is resolvable")

    # ---------------------------------------------------------
    # Test 1: API Key Authentication
    # ---------------------------------------------------------
    if config["api_key"]:
        print("\n[Test 1] AsyncElasticsearch with API Key")
        client = None
        try:
            client = create_async_client(base_url, {
                **config,
                "user": "",  # Force API key auth
                "password": "",
            })
            info = await client.info()
            print(f"  SUCCESS: Connected to Elasticsearch {info['version']['number']}")
            print(f"  Cluster: {info['cluster_name']}")

            # Check index if specified
            if config["index"]:
                exists = await check_index_exists(client, config["index"])
                print(f"  Index '{config['index']}' exists: {exists}")

        except Exception as e:
            print(f"  FAILURE: {format_connection_error(e, config['host'])}")
        finally:
            if client:
                await client.close()
    else:
        print("\n[Test 1] API Key Authentication - SKIPPED (no API key set)")

    # ---------------------------------------------------------
    # Test 2: Basic Auth (Username/Password)
    # ---------------------------------------------------------
    if config["user"] and config["password"]:
        print("\n[Test 2] AsyncElasticsearch with Basic Auth")
        client = None
        try:
            client = create_async_client(base_url, {
                **config,
                "api_key": "",  # Force basic auth
            })
            info = await client.info()
            print(f"  SUCCESS: Connected to Elasticsearch {info['version']['number']}")
            print(f"  Cluster: {info['cluster_name']}")

            # Check index if specified
            if config["index"]:
                exists = await check_index_exists(client, config["index"])
                print(f"  Index '{config['index']}' exists: {exists}")

        except Exception as e:
            print(f"  FAILURE: {format_connection_error(e, config['host'])}")
        finally:
            if client:
                await client.close()
    else:
        print("\n[Test 2] Basic Auth - SKIPPED (no username/password set)")

    # ---------------------------------------------------------
    # Test 3: No Authentication
    # ---------------------------------------------------------
    print("\n[Test 3] AsyncElasticsearch without authentication")
    client = None
    try:
        client = create_async_client(base_url, {
            **config,
            "api_key": "",
            "user": "",
            "password": "",
        })
        info = await client.info()
        print(f"  SUCCESS: Connected to Elasticsearch {info['version']['number']}")
        print(f"  Cluster: {info['cluster_name']}")

        # Check index if specified
        if config["index"]:
            exists = await check_index_exists(client, config["index"])
            print(f"  Index '{config['index']}' exists: {exists}")

    except Exception as e:
        print(f"  FAILURE: {format_connection_error(e, config['host'])}")
    finally:
        if client:
            await client.close()

    # ---------------------------------------------------------
    # Test 4: Full authentication flow with index check
    # ---------------------------------------------------------
    print("\n[Test 4] Full authentication flow (auto-detect auth method)")
    client = None
    try:
        client = create_async_client(base_url, config)
        info = await client.info()
        print(f"  SUCCESS: Connected to Elasticsearch {info['version']['number']}")
        print(f"  Cluster: {info['cluster_name']}")
        print(f"  Tagline: {info.get('tagline', 'N/A')}")

        # Check index if specified
        if config["index"]:
            print(f"\n  Checking index: {config['index']}")
            exists = await check_index_exists(client, config["index"])
            if exists:
                print(f"    Index exists: True")
                # Get index stats
                try:
                    stats = await client.indices.stats(index=config["index"])
                    doc_count = stats["_all"]["primaries"]["docs"]["count"]
                    size_bytes = stats["_all"]["primaries"]["store"]["size_in_bytes"]
                    print(f"    Document count: {doc_count}")
                    print(f"    Size: {size_bytes / 1024 / 1024:.2f} MB")
                except Exception as e:
                    print(f"    Could not get stats: {e}")
            else:
                print(f"    Index exists: False")

    except Exception as e:
        print(f"  FAILURE: {format_connection_error(e, config['host'])}")
    finally:
        if client:
            await client.close()

    # ---------------------------------------------------------
    # Test 5: Custom SSL context
    # ---------------------------------------------------------
    print("\n[Test 5] Custom SSL context (verification disabled)")
    client = None
    try:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        # Create client with custom SSL context
        if config.get("api_key"):
            client = AsyncElasticsearch(
                base_url,
                api_key=config["api_key"],
                ssl_context=ssl_context,
            )
        elif config.get("user") and config.get("password"):
            client = AsyncElasticsearch(
                base_url,
                basic_auth=(config["user"], config["password"]),
                ssl_context=ssl_context,
            )
        else:
            client = AsyncElasticsearch(
                base_url,
                ssl_context=ssl_context,
            )

        info = await client.info()
        print(f"  SUCCESS: Connected with custom SSL context")
        print(f"  Version: {info['version']['number']}")

    except Exception as e:
        print(f"  FAILURE: {format_connection_error(e, config['host'])}")
    finally:
        if client:
            await client.close()

    print("\n" + "=" * 60)
    print("Tests completed")
    print("=" * 60)


def main():
    if not ES_AVAILABLE:
        print("ERROR: elasticsearch is not installed")
        print("Install with: pip install elasticsearch==8.19.0")
        return

    asyncio.run(run_tests())


if __name__ == "__main__":
    main()
