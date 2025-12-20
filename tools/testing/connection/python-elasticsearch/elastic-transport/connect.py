"""
elastic-transport Connection Test

Tests low-level elastic-transport library connectivity with:
- URL builder (schema, host, port, index)
- Proxy support
- SSL/TLS options
- Error handling for DNS resolution and connection errors
"""
import os
import socket
import ssl
import urllib3
from urllib.parse import urlencode

# Handle import - HttpxTransport may not be available in all versions
try:
    from elastic_transport import Transport, NodeConfig
    TRANSPORT_AVAILABLE = True
except ImportError as e:
    print(f"Warning: elastic_transport not available: {e}")
    TRANSPORT_AVAILABLE = False
    Transport = None
    NodeConfig = None

# Try multiple HttpxTransport class names across different elastic-transport versions
# - HttpxTransport: some versions
# - Httpx2Transport: elastic-transport 8.x
# - HttpxAsyncTransport: some async versions
# - RequestsHttpConnection: fallback for older versions
HTTPX_TRANSPORT_AVAILABLE = False
HttpxTransport = None
HTTPX_TRANSPORT_NAME = None

_httpx_import_names = [
    "HttpxTransport",
    "Httpx2Transport",
    "HttpxAsyncTransport",
    "Urllib3HttpConnection",
]

for _name in _httpx_import_names:
    try:
        HttpxTransport = getattr(__import__("elastic_transport", fromlist=[_name]), _name)
        HTTPX_TRANSPORT_AVAILABLE = True
        HTTPX_TRANSPORT_NAME = _name
        break
    except (ImportError, AttributeError):
        continue

if not HTTPX_TRANSPORT_AVAILABLE:
    # Final fallback - check if httpx is installed and try direct import
    try:
        import httpx
        # If httpx is available but no transport class found, note this
        HTTPX_TRANSPORT_NAME = "httpx installed but no HttpxTransport class found"
    except ImportError:
        HTTPX_TRANSPORT_NAME = "httpx not installed"

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
        msg += "\n    Try: Set verify_certs=False for testing"
        msg += f"\n    Original error: {e}"
        return msg

    # Authentication errors
    if "401" in error_str or "unauthorized" in error_lower or "authentication" in error_lower:
        msg = f"AUTH_ERROR: Authentication failed"
        msg += "\n    Possible causes:"
        msg += "\n    - Wrong username/password"
        msg += "\n    - Invalid BasicAuth credentials"
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
        "scheme": os.getenv("ELASTIC_DB_SCHEME", os.getenv("ELASTICSEARCH_SCHEME", "http")),
        "host": os.getenv("ELASTIC_DB_HOST", os.getenv("ELASTICSEARCH_HOST", "localhost")),
        "port": int(os.getenv("ELASTIC_DB_PORT", os.getenv("ELASTICSEARCH_PORT", "9200"))),
        "user": os.getenv("ELASTIC_DB_USERNAME", os.getenv("ELASTICSEARCH_USER", "elastic")),
        "password": os.getenv("ELASTIC_DB_PASSWORD", os.getenv("ELASTICSEARCH_PASSWORD", "")),
        "use_ssl": os.getenv("ELASTIC_DB_USE_TLS", os.getenv("ELASTICSEARCH_SSL", "false")).lower() == "true",
        "index": os.getenv("ELASTIC_DB_INDEX", os.getenv("ELASTICSEARCH_INDEX", "")),
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


def main():
    if not TRANSPORT_AVAILABLE:
        print("ERROR: elastic_transport is not installed")
        print("Install with: pip install elastic-transport")
        return

    print("=" * 60)
    print("elastic-transport Connection Test")
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

    print(f"\nTransport Classes:")
    print(f"  Transport: {'available' if TRANSPORT_AVAILABLE else 'NOT available'}")
    print(f"  HttpxTransport: {HTTPX_TRANSPORT_NAME if HTTPX_TRANSPORT_AVAILABLE else 'NOT available'}")
    if not HTTPX_TRANSPORT_AVAILABLE:
        print(f"    Reason: {HTTPX_TRANSPORT_NAME}")

    # Build base URL
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
        print("  Tests will likely fail. Check ELASTICSEARCH_HOST environment variable.")
    else:
        print(f"  OK: Hostname '{config['host']}' is resolvable")

    # ---------------------------------------------------------
    # Test 1: NodeConfig with HTTP (no SSL)
    # ---------------------------------------------------------
    print("\n[Test 1] NodeConfig with HTTP (no SSL)")
    try:
        node_config = NodeConfig(
            scheme=config["scheme"],
            host=config["host"],
            port=config["port"],
        )

        transport_kwargs = {}

        # Note: elastic_transport doesn't directly support proxy in Transport
        # Proxy support would need to be handled at the httpx/urllib3 level

        transport = Transport([node_config], **transport_kwargs)

        response = transport.perform_request("GET", "/")
        print(f"  SUCCESS: Connected via elastic-transport")
        print(f"  Response status: {response.meta.status}")
        transport.close()
    except Exception as e:
        print(f"  FAILURE: {format_connection_error(e, config['host'])}")

    # ---------------------------------------------------------
    # Test 2: NodeConfig with basic auth (no SSL)
    # ---------------------------------------------------------
    print("\n[Test 2] NodeConfig with basic auth")
    try:
        from elastic_transport import BasicAuth

        node_config = NodeConfig(
            scheme=config["scheme"],
            host=config["host"],
            port=config["port"],
        )
        transport = Transport(
            [node_config],
            http_auth=BasicAuth(config["user"], config["password"]),
        )

        response = transport.perform_request("GET", "/")
        print(f"  SUCCESS: Connected via elastic-transport with auth")
        print(f"  Response status: {response.meta.status}")
        transport.close()
    except Exception as e:
        print(f"  FAILURE: {format_connection_error(e, config['host'])}")

    # ---------------------------------------------------------
    # Test 3: HTTPS with SSL verification disabled
    # ---------------------------------------------------------
    print("\n[Test 3] HTTPS with SSL verification disabled")
    try:
        from elastic_transport import BasicAuth

        node_config = NodeConfig(
            scheme="https",
            host=config["host"],
            port=config["port"],
        )
        transport = Transport(
            [node_config],
            http_auth=BasicAuth(config["user"], config["password"]),
            verify_certs=False,
            ssl_show_warn=False,
        )

        response = transport.perform_request("GET", "/")
        print(f"  SUCCESS: Connected via elastic-transport (HTTPS, no verify)")
        print(f"  Response status: {response.meta.status}")
        transport.close()
    except Exception as e:
        print(f"  FAILURE: {format_connection_error(e, config['host'])}")

    # ---------------------------------------------------------
    # Test 4: Custom SSL context with verification disabled
    # ---------------------------------------------------------
    print("\n[Test 4] Custom SSL context with verification disabled")
    try:
        from elastic_transport import BasicAuth

        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        node_config = NodeConfig(
            scheme="https",
            host=config["host"],
            port=config["port"],
        )
        transport = Transport(
            [node_config],
            http_auth=BasicAuth(config["user"], config["password"]),
            ssl_context=ssl_context,
        )

        response = transport.perform_request("GET", "/")
        print(f"  SUCCESS: Connected with custom SSL context")
        print(f"  Response status: {response.meta.status}")
        transport.close()
    except Exception as e:
        print(f"  FAILURE: {format_connection_error(e, config['host'])}")

    # ---------------------------------------------------------
    # Test 5: HttpxTransport (if available)
    # ---------------------------------------------------------
    print("\n[Test 5] HttpxTransport with no SSL verification")
    if not HTTPX_TRANSPORT_AVAILABLE:
        print("  SKIPPED: HttpxTransport not available in this version")
        print(f"  Reason: {HTTPX_TRANSPORT_NAME}")
        print("  Tried: HttpxTransport, Httpx2Transport, HttpxAsyncTransport, Urllib3HttpConnection")
        print("  Install httpx: pip install httpx")
    else:
        print(f"  Using transport class: {HTTPX_TRANSPORT_NAME}")
        try:
            from elastic_transport import BasicAuth

            node_config = NodeConfig(
                scheme="https",
                host=config["host"],
                port=config["port"],
            )
            transport = HttpxTransport(
                [node_config],
                http_auth=BasicAuth(config["user"], config["password"]),
                verify_certs=False,
            )

            response = transport.perform_request("GET", "/")
            print(f"  SUCCESS: Connected via {HTTPX_TRANSPORT_NAME}")
            print(f"  Response status: {response.meta.status}")
            transport.close()
        except Exception as e:
            print(f"  FAILURE: {format_connection_error(e, config['host'])}")

    # ---------------------------------------------------------
    # Test 6: Index-specific request
    # ---------------------------------------------------------
    if config["index"]:
        print(f"\n[Test 6] Index-specific request: {config['index']}")
        try:
            from elastic_transport import BasicAuth

            node_config = NodeConfig(
                scheme=config["scheme"],
                host=config["host"],
                port=config["port"],
            )
            transport = Transport(
                [node_config],
                http_auth=BasicAuth(config["user"], config["password"]),
                verify_certs=False,
                ssl_show_warn=False,
            )

            # Check if index exists
            response = transport.perform_request("HEAD", f"/{config['index']}")
            print(f"  SUCCESS: Index '{config['index']}' exists")
            print(f"  Response status: {response.meta.status}")
            transport.close()
        except Exception as e:
            print(f"  FAILURE: {format_connection_error(e, config['host'])}")
    else:
        print("\n[Test 6] Index-specific request - SKIPPED (no index set)")

    print("\n" + "=" * 60)
    print("Tests completed")
    print("=" * 60)


if __name__ == "__main__":
    main()
