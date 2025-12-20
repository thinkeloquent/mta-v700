"""
opensearch-py Connection Test

Tests OpenSearch Python client connectivity with:
- URL builder (schema, host, port, index)
- Proxy support
- SSL/TLS options
- Compatible with both OpenSearch and Elasticsearch
- Error handling for DNS resolution and connection errors
"""
import os
import socket
import ssl
import urllib3

try:
    from opensearchpy import OpenSearch
    OPENSEARCH_AVAILABLE = True
except ImportError:
    OPENSEARCH_AVAILABLE = False
    OpenSearch = None

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Disable SSL warnings when SSL verification is disabled
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


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
        msg += "\n    - OpenSearch/Elasticsearch service is not running"
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
        msg += "\n    Try: Set verify_certs=False for testing"
        msg += f"\n    Original error: {e}"
        return msg

    # Authentication errors
    if "401" in error_str or "unauthorized" in error_lower or "authentication" in error_lower:
        msg = f"AUTH_ERROR: Authentication failed"
        msg += "\n    Possible causes:"
        msg += "\n    - Wrong username/password"
        msg += "\n    - User does not have required permissions"
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
    username: str = None,
    password: str = None,
) -> str:
    """
    Build OpenSearch/Elasticsearch URL from components.

    Args:
        scheme: http or https
        host: OpenSearch host
        port: OpenSearch port
        index: Optional index name
        path: Optional path (e.g., "_search", "_doc/1")
        username: Optional username for URL auth
        password: Optional password for URL auth

    Returns:
        Full URL string
    """
    auth = ""
    if username and password:
        auth = f"{username}:{password}@"
    elif username:
        auth = f"{username}@"

    url = f"{scheme}://{auth}{host}:{port}"
    if index:
        url = f"{url}/{index}"
    if path:
        url = f"{url}/{path}"
    return url


def get_es_config():
    """Get OpenSearch/Elasticsearch configuration from environment."""
    # Priority: ELASTIC_DB_* > ELASTICSEARCH_* > OPENSEARCH_* > defaults
    return {
        "scheme": os.getenv("ELASTIC_DB_SCHEME", os.getenv("ELASTICSEARCH_SCHEME", os.getenv("OPENSEARCH_SCHEME", "http"))),
        "host": os.getenv("ELASTIC_DB_HOST", os.getenv("ELASTICSEARCH_HOST", os.getenv("OPENSEARCH_HOST", "localhost"))),
        "port": int(os.getenv("ELASTIC_DB_PORT", os.getenv("ELASTICSEARCH_PORT", os.getenv("OPENSEARCH_PORT", "9200")))),
        "user": os.getenv("ELASTIC_DB_USERNAME", os.getenv("ELASTICSEARCH_USER", os.getenv("OPENSEARCH_USER", "admin"))),
        "password": os.getenv("ELASTIC_DB_PASSWORD", os.getenv("ELASTICSEARCH_PASSWORD", os.getenv("OPENSEARCH_PASSWORD", "admin"))),
        "use_ssl": os.getenv("ELASTIC_DB_USE_TLS", os.getenv("ELASTICSEARCH_SSL", os.getenv("OPENSEARCH_SSL", "false"))).lower() == "true",
        "index": os.getenv("ELASTIC_DB_INDEX", os.getenv("ELASTICSEARCH_INDEX", os.getenv("OPENSEARCH_INDEX", ""))),
        # Proxy settings
        "http_proxy": os.getenv("HTTP_PROXY", os.getenv("http_proxy", "")),
        "https_proxy": os.getenv("HTTPS_PROXY", os.getenv("https_proxy", "")),
        "no_proxy": os.getenv("NO_PROXY", os.getenv("no_proxy", "")),
    }


def get_proxy_url(config: dict) -> str | None:
    """Get proxy URL based on scheme."""
    scheme = config.get("scheme", "http")
    if scheme == "https":
        return config.get("https_proxy") or None
    return config.get("http_proxy") or None


def create_opensearch_client(config: dict, use_proxy: bool = True, **kwargs) -> OpenSearch:
    """
    Create OpenSearch client with optional proxy support.

    Args:
        config: Configuration dictionary
        use_proxy: Whether to use proxy if configured
        **kwargs: Additional kwargs to pass to OpenSearch constructor

    Returns:
        OpenSearch client instance
    """
    proxy_url = get_proxy_url(config) if use_proxy else None

    client_kwargs = {
        "hosts": [{"host": config["host"], "port": config["port"]}],
        "http_compress": True,
        "use_ssl": config["scheme"] == "https" or config["use_ssl"],
        "verify_certs": False,
        "ssl_assert_hostname": False,
        "ssl_show_warn": False,
        **kwargs,
    }

    # Add proxy if configured
    # opensearch-py uses 'http_proxy' and 'https_proxy' parameters
    if proxy_url:
        if config.get("http_proxy"):
            client_kwargs["http_proxy"] = config["http_proxy"]
        if config.get("https_proxy"):
            client_kwargs["https_proxy"] = config["https_proxy"]

    return OpenSearch(**client_kwargs)


def main():
    if not OPENSEARCH_AVAILABLE:
        print("ERROR: opensearch-py is not installed")
        print("Install with: pip install opensearch-py")
        return

    print("=" * 60)
    print("opensearch-py Connection Test")
    print("=" * 60)

    config = get_es_config()
    proxy_url = get_proxy_url(config)

    # Determine scheme based on use_ssl if not explicitly set
    if config["use_ssl"] and config["scheme"] == "http":
        config["scheme"] = "https"

    print(f"\nConfig:")
    print(f"  Scheme: {config['scheme']}")
    print(f"  Host: {config['host']}")
    print(f"  Port: {config['port']}")
    print(f"  User: {config['user']}")
    print(f"  Index: {config['index'] or 'N/A'}")
    print(f"  SSL: {config['use_ssl']}")
    print(f"  Proxy: {proxy_url or 'N/A'}")

    # Build and display URLs
    base_url = build_url(
        scheme=config["scheme"],
        host=config["host"],
        port=config["port"],
    )
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
        print("  Tests will likely fail. Check ELASTICSEARCH_HOST or OPENSEARCH_HOST environment variable.")
    else:
        print(f"  OK: Hostname '{config['host']}' is resolvable")

    # ---------------------------------------------------------
    # Test 1: Basic HTTP connection (no SSL, no auth)
    # ---------------------------------------------------------
    print("\n[Test 1] Basic HTTP connection (no SSL, no auth)")
    try:
        client = OpenSearch(
            hosts=[{"host": config["host"], "port": config["port"]}],
            http_compress=True,
            use_ssl=False,
            verify_certs=False,
            ssl_show_warn=False,
        )
        info = client.info()
        print(f"  SUCCESS: Connected to OpenSearch/Elasticsearch")
        print(f"  Version: {info['version']['number']}")
        print(f"  Cluster: {info['cluster_name']}")
    except Exception as e:
        print(f"  FAILURE: {format_connection_error(e, config['host'])}")

    # ---------------------------------------------------------
    # Test 2: HTTP with basic auth (no SSL)
    # ---------------------------------------------------------
    print("\n[Test 2] HTTP with basic auth (no SSL)")
    try:
        client = OpenSearch(
            hosts=[{"host": config["host"], "port": config["port"]}],
            http_auth=(config["user"], config["password"]),
            http_compress=True,
            use_ssl=False,
            verify_certs=False,
            ssl_show_warn=False,
        )
        info = client.info()
        print(f"  SUCCESS: Connected to OpenSearch/Elasticsearch")
        print(f"  Version: {info['version']['number']}")
        print(f"  Cluster: {info['cluster_name']}")
    except Exception as e:
        print(f"  FAILURE: {format_connection_error(e, config['host'])}")

    # ---------------------------------------------------------
    # Test 3: HTTPS with SSL verification disabled
    # ---------------------------------------------------------
    print("\n[Test 3] HTTPS with SSL verification disabled")
    try:
        client = OpenSearch(
            hosts=[{"host": config["host"], "port": config["port"]}],
            http_auth=(config["user"], config["password"]),
            http_compress=True,
            use_ssl=True,
            verify_certs=False,
            ssl_assert_hostname=False,
            ssl_show_warn=False,
        )
        info = client.info()
        print(f"  SUCCESS: Connected to OpenSearch/Elasticsearch")
        print(f"  Version: {info['version']['number']}")
        print(f"  Cluster: {info['cluster_name']}")
    except Exception as e:
        print(f"  FAILURE: {format_connection_error(e, config['host'])}")

    # ---------------------------------------------------------
    # Test 4: Custom SSL context with verification disabled
    # ---------------------------------------------------------
    print("\n[Test 4] Custom SSL context with verification disabled")
    try:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        client = OpenSearch(
            hosts=[{"host": config["host"], "port": config["port"]}],
            http_auth=(config["user"], config["password"]),
            http_compress=True,
            use_ssl=True,
            ssl_context=ssl_context,
        )
        info = client.info()
        print(f"  SUCCESS: Connected to OpenSearch/Elasticsearch")
        print(f"  Version: {info['version']['number']}")
        print(f"  Cluster: {info['cluster_name']}")
    except Exception as e:
        print(f"  FAILURE: {format_connection_error(e, config['host'])}")

    # ---------------------------------------------------------
    # Test 5: Connection with URL string
    # ---------------------------------------------------------
    print("\n[Test 5] Connection with URL string")
    try:
        url = build_url(
            scheme=config["scheme"],
            host=config["host"],
            port=config["port"],
            username=config["user"],
            password=config["password"],
        )
        client = OpenSearch(
            hosts=[url],
            http_compress=True,
            use_ssl=config["scheme"] == "https",
            verify_certs=False,
            ssl_show_warn=False,
        )
        info = client.info()
        print(f"  SUCCESS: Connected to OpenSearch/Elasticsearch")
        print(f"  Version: {info['version']['number']}")
        print(f"  Cluster: {info['cluster_name']}")
    except Exception as e:
        print(f"  FAILURE: {format_connection_error(e, config['host'])}")

    # ---------------------------------------------------------
    # Test 6: Connection with proxy (if configured)
    # ---------------------------------------------------------
    if proxy_url:
        print(f"\n[Test 6] Connection with proxy: {proxy_url}")
        try:
            client = create_opensearch_client(
                config,
                use_proxy=True,
                http_auth=(config["user"], config["password"]),
            )
            info = client.info()
            print(f"  SUCCESS: Connected via proxy to OpenSearch/Elasticsearch")
            print(f"  Version: {info['version']['number']}")
            print(f"  Cluster: {info['cluster_name']}")
        except Exception as e:
            print(f"  FAILURE: {format_connection_error(e, config['host'])}")
    else:
        print("\n[Test 6] Connection with proxy - SKIPPED (no proxy set)")

    # ---------------------------------------------------------
    # Test 7: Index-specific operations
    # ---------------------------------------------------------
    if config["index"]:
        print(f"\n[Test 7] Index-specific operations: {config['index']}")
        try:
            client = OpenSearch(
                hosts=[{"host": config["host"], "port": config["port"]}],
                http_auth=(config["user"], config["password"]),
                http_compress=True,
                use_ssl=config["scheme"] == "https",
                verify_certs=False,
                ssl_show_warn=False,
            )

            # Check if index exists
            exists = client.indices.exists(index=config["index"])
            if exists:
                print(f"  Index '{config['index']}' exists")
                # Get index info
                stats = client.indices.stats(index=config["index"])
                doc_count = stats["_all"]["primaries"]["docs"]["count"]
                print(f"  Document count: {doc_count}")
            else:
                print(f"  Index '{config['index']}' does not exist")

        except Exception as e:
            print(f"  FAILURE: {format_connection_error(e, config['host'])}")
    else:
        print("\n[Test 7] Index-specific operations - SKIPPED (no index set)")

    print("\n" + "=" * 60)
    print("Tests completed")
    print("=" * 60)


if __name__ == "__main__":
    main()
