"""
Elastic Cloud on Google Cloud Platform Connection Test

Tests Elasticsearch connectivity to Elastic Cloud (GCP) with:
- Cloud ID authentication (recommended for Elastic Cloud)
- API Key authentication
- Basic Auth (username/password)
- AsyncElasticsearch client
- Error handling for DNS resolution and connection errors

Elastic Cloud Connection Methods:
1. Cloud ID + API Key (recommended)
2. Cloud ID + Basic Auth
3. Direct URL + API Key
4. Direct URL + Basic Auth

Requirements:
    pip install elasticsearch==8.19.0

Environment Variables:
    # Cloud ID (from Elastic Cloud console)
    ELASTIC_CLOUD_ID=my-deployment:dXMtY2VudHJhbDEuZ2NwLmNsb3VkLmVzLmlvOjQ0MyQ...

    # API Key (recommended - from Elastic Cloud console or Kibana)
    ELASTICSEARCH_API_KEY=base64_encoded_api_key

    # OR Basic Auth
    ELASTICSEARCH_USER=elastic
    ELASTICSEARCH_PASSWORD=your_password

    # Optional: Direct endpoint (alternative to Cloud ID)
    ELASTICSEARCH_HOST=my-deployment.es.us-central1.gcp.cloud.es.io
    ELASTICSEARCH_PORT=443

    # Optional: Index to test
    ELASTICSEARCH_INDEX=my-index
"""
import asyncio
import base64
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
        msg += "\n    - Cloud ID is invalid or malformed"
        msg += "\n    - Hostname is misspelled or invalid"
        msg += "\n    - DNS server is unreachable"
        msg += "\n    - Elastic Cloud deployment does not exist"
        msg += "\n    - Network connectivity issues"
        msg += f"\n    Original error: {e}"
        return msg

    # Connection refused
    if "connection refused" in error_lower or "errno 111" in error_lower or "errno 61" in error_lower:
        msg = f"CONNECTION_REFUSED: Server is not accepting connections"
        if host:
            msg += f" on '{host}'"
        msg += "\n    Possible causes:"
        msg += "\n    - Elastic Cloud deployment is stopped or paused"
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
        msg += "\n    - Elastic Cloud deployment is starting up"
        msg += "\n    - Network latency issues"
        msg += "\n    - Firewall silently dropping packets"
        msg += f"\n    Original error: {e}"
        return msg

    # SSL certificate errors
    if "ssl" in error_lower or "certificate" in error_lower:
        msg = f"SSL_ERROR: SSL/TLS connection failed"
        msg += "\n    Possible causes:"
        msg += "\n    - Invalid or expired SSL certificate"
        msg += "\n    - Network intercepting SSL traffic (corporate proxy)"
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
        msg += "\n    - Insufficient permissions"
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


def parse_cloud_id(cloud_id: str) -> tuple[str, str]:
    """
    Parse Cloud ID to extract the Elasticsearch host.

    Cloud ID format: deployment-name:base64(host:port$es_uuid$kibana_uuid)

    Args:
        cloud_id: The Cloud ID from Elastic Cloud console

    Returns:
        Tuple of (es_host, error_message)
    """
    if not cloud_id:
        return "", "Cloud ID is empty"

    try:
        # Cloud ID format: name:base64_data
        parts = cloud_id.split(":")
        if len(parts) < 2:
            return "", "Invalid Cloud ID format (missing ':')"

        # Decode the base64 part
        encoded = parts[1]
        # Add padding if needed
        padding = 4 - (len(encoded) % 4)
        if padding != 4:
            encoded += "=" * padding

        decoded = base64.b64decode(encoded).decode("utf-8")
        # Format: host:port$es_uuid$kibana_uuid
        host_parts = decoded.split("$")
        if host_parts:
            host_port = host_parts[0]
            # Extract just the host (before any port)
            host = host_port.split(":")[0] if ":" in host_port else host_port
            # For ES, construct the full host
            if len(host_parts) > 1:
                es_uuid = host_parts[1]
                full_host = f"{es_uuid}.{host}"
                return full_host, ""
        return "", "Could not parse Cloud ID"
    except Exception as e:
        return "", f"Error parsing Cloud ID: {e}"


def get_cloud_config():
    """Get Elastic Cloud configuration from environment."""
    return {
        # Cloud ID (base64 encoded deployment info from Elastic Cloud console)
        "cloud_id": os.getenv("ELASTIC_CLOUD_ID", ""),
        # Direct endpoint (alternative to Cloud ID)
        "scheme": os.getenv("ELASTICSEARCH_SCHEME", "https"),
        "host": os.getenv("ELASTICSEARCH_HOST", ""),
        "port": int(os.getenv("ELASTICSEARCH_PORT", "443")),
        # Authentication
        "user": os.getenv("ELASTICSEARCH_USER", "elastic"),
        "password": os.getenv("ELASTICSEARCH_PASSWORD", ""),
        "api_key": os.getenv("ELASTICSEARCH_API_KEY", ""),
        # Index to test
        "index": os.getenv("ELASTICSEARCH_INDEX", ""),
        # SSL settings (Elastic Cloud uses valid certs, so verify by default)
        "verify_certs": os.getenv("ELASTICSEARCH_VERIFY_CERTS", "true").lower() == "true",
        "ssl_show_warn": os.getenv("ELASTICSEARCH_SSL_SHOW_WARN", "true").lower() == "true",
        "ca_certs": os.getenv("ELASTICSEARCH_CA_CERTS", ""),
    }


def get_ssl_config(config: dict) -> dict:
    """
    Build SSL configuration for Elastic Cloud.

    Note: Elastic Cloud uses valid SSL certificates by default,
    so verify_certs should typically be True.

    Args:
        config: Configuration dictionary

    Returns:
        SSL config kwargs for AsyncElasticsearch
    """
    ssl_config = {
        "verify_certs": config.get("verify_certs", True),
        "ssl_show_warn": config.get("ssl_show_warn", True),
    }

    # Optional CA certs (usually not needed for Elastic Cloud)
    if config.get("ca_certs"):
        ssl_config["ca_certs"] = config["ca_certs"]

    return ssl_config


def create_cloud_client_with_cloud_id(config: dict) -> AsyncElasticsearch:
    """
    Create AsyncElasticsearch client using Cloud ID.

    This is the recommended method for connecting to Elastic Cloud.
    Cloud ID contains encoded deployment information.

    Args:
        config: Configuration dictionary with cloud_id

    Returns:
        AsyncElasticsearch client instance
    """
    ssl_config = get_ssl_config(config)
    cloud_id = config["cloud_id"]

    # API Key authentication (recommended)
    if config.get("api_key"):
        return AsyncElasticsearch(
            cloud_id=cloud_id,
            api_key=config["api_key"],
            **ssl_config,
        )

    # Basic Auth (username/password)
    if config.get("user") and config.get("password"):
        return AsyncElasticsearch(
            cloud_id=cloud_id,
            basic_auth=(config["user"], config["password"]),
            **ssl_config,
        )

    # No authentication (will fail on Elastic Cloud)
    return AsyncElasticsearch(
        cloud_id=cloud_id,
        **ssl_config,
    )


def create_cloud_client_with_url(config: dict) -> AsyncElasticsearch:
    """
    Create AsyncElasticsearch client using direct URL.

    Use this method if you have the direct Elasticsearch endpoint URL.

    Args:
        config: Configuration dictionary with host/port

    Returns:
        AsyncElasticsearch client instance
    """
    ssl_config = get_ssl_config(config)
    url = f"{config['scheme']}://{config['host']}:{config['port']}"

    # API Key authentication (recommended)
    if config.get("api_key"):
        return AsyncElasticsearch(
            url,
            api_key=config["api_key"],
            **ssl_config,
        )

    # Basic Auth (username/password)
    if config.get("user") and config.get("password"):
        return AsyncElasticsearch(
            url,
            basic_auth=(config["user"], config["password"]),
            **ssl_config,
        )

    # No authentication (will fail on Elastic Cloud)
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


async def get_cluster_health(client: AsyncElasticsearch) -> dict:
    """Get cluster health status."""
    try:
        return await client.cluster.health()
    except Exception as e:
        print(f"    Error getting cluster health: {e}")
        return {}


async def run_tests():
    """Run all Elastic Cloud connection tests."""
    config = get_cloud_config()

    print("=" * 60)
    print("Elastic Cloud (GCP) Connection Test")
    print("=" * 60)

    print(f"\nConfig:")
    print(f"  Cloud ID: {'set' if config['cloud_id'] else 'not set'}")
    print(f"  Host: {config['host'] or 'N/A'}")
    print(f"  Port: {config['port']}")
    print(f"  User: {config['user'] or 'N/A'}")
    print(f"  API Key: {'set' if config['api_key'] else 'not set'}")
    print(f"  Index: {config['index'] or 'N/A'}")
    print(f"  Verify Certs: {config['verify_certs']}")

    # Determine which connection method to use
    has_cloud_id = bool(config["cloud_id"])
    has_host = bool(config["host"])
    has_api_key = bool(config["api_key"])
    has_basic_auth = bool(config["user"] and config["password"])

    if not has_cloud_id and not has_host:
        print("\nERROR: Either ELASTIC_CLOUD_ID or ELASTICSEARCH_HOST must be set")
        print("\nTo get your Cloud ID:")
        print("  1. Go to https://cloud.elastic.co")
        print("  2. Select your deployment")
        print("  3. Click 'Manage' -> Copy Cloud ID")
        return

    if not has_api_key and not has_basic_auth:
        print("\nERROR: Either ELASTICSEARCH_API_KEY or ELASTICSEARCH_USER/PASSWORD must be set")
        print("\nTo create an API Key:")
        print("  1. Go to Kibana -> Stack Management -> API Keys")
        print("  2. Create a new API key")
        print("  3. Copy the base64 encoded key")
        return

    # Validate connectivity before running tests
    print("\n[Pre-flight] Validating connectivity...")

    # If using Cloud ID, parse it to get the host for validation
    es_host = ""
    if has_cloud_id:
        es_host, parse_error = parse_cloud_id(config["cloud_id"])
        if parse_error:
            print(f"  WARNING: {parse_error}")
        elif es_host:
            is_valid, error_msg = validate_host(es_host)
            if not is_valid:
                print(f"  WARNING: {error_msg}")
                print("  Tests will likely fail. Check your ELASTIC_CLOUD_ID.")
            else:
                print(f"  OK: Cloud ID host '{es_host}' is resolvable")

    # If using direct host, validate it
    if has_host:
        is_valid, error_msg = validate_host(config["host"])
        if not is_valid:
            print(f"  WARNING: {error_msg}")
            print("  Tests will likely fail. Check ELASTICSEARCH_HOST environment variable.")
        else:
            print(f"  OK: Direct host '{config['host']}' is resolvable")

    # ---------------------------------------------------------
    # Test 1: Cloud ID + API Key (recommended)
    # ---------------------------------------------------------
    if has_cloud_id and has_api_key:
        print("\n[Test 1] Cloud ID + API Key Authentication")
        client = None
        try:
            client = create_cloud_client_with_cloud_id({
                **config,
                "user": "",
                "password": "",
            })
            info = await client.info()
            print(f"  SUCCESS: Connected to Elasticsearch {info['version']['number']}")
            print(f"  Cluster: {info['cluster_name']}")
            print(f"  Tagline: {info.get('tagline', 'N/A')}")

            # Get cluster health
            health = await get_cluster_health(client)
            if health:
                print(f"  Status: {health.get('status', 'unknown')}")
                print(f"  Nodes: {health.get('number_of_nodes', 0)}")

            # Check index if specified
            if config["index"]:
                exists = await check_index_exists(client, config["index"])
                print(f"  Index '{config['index']}' exists: {exists}")

        except Exception as e:
            print(f"  FAILURE: {format_connection_error(e, es_host or config['host'])}")
        finally:
            if client:
                await client.close()
    else:
        print("\n[Test 1] Cloud ID + API Key - SKIPPED (missing cloud_id or api_key)")

    # ---------------------------------------------------------
    # Test 2: Cloud ID + Basic Auth
    # ---------------------------------------------------------
    if has_cloud_id and has_basic_auth:
        print("\n[Test 2] Cloud ID + Basic Auth")
        client = None
        try:
            client = create_cloud_client_with_cloud_id({
                **config,
                "api_key": "",
            })
            info = await client.info()
            print(f"  SUCCESS: Connected to Elasticsearch {info['version']['number']}")
            print(f"  Cluster: {info['cluster_name']}")

            # Check index if specified
            if config["index"]:
                exists = await check_index_exists(client, config["index"])
                print(f"  Index '{config['index']}' exists: {exists}")

        except Exception as e:
            print(f"  FAILURE: {format_connection_error(e, es_host or config['host'])}")
        finally:
            if client:
                await client.close()
    else:
        print("\n[Test 2] Cloud ID + Basic Auth - SKIPPED (missing cloud_id or credentials)")

    # ---------------------------------------------------------
    # Test 3: Direct URL + API Key
    # ---------------------------------------------------------
    if has_host and has_api_key:
        print("\n[Test 3] Direct URL + API Key")
        client = None
        try:
            client = create_cloud_client_with_url({
                **config,
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
    else:
        print("\n[Test 3] Direct URL + API Key - SKIPPED (missing host or api_key)")

    # ---------------------------------------------------------
    # Test 4: Direct URL + Basic Auth
    # ---------------------------------------------------------
    if has_host and has_basic_auth:
        print("\n[Test 4] Direct URL + Basic Auth")
        client = None
        try:
            client = create_cloud_client_with_url({
                **config,
                "api_key": "",
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
        print("\n[Test 4] Direct URL + Basic Auth - SKIPPED (missing host or credentials)")

    # ---------------------------------------------------------
    # Test 5: Index operations (if connected and index specified)
    # ---------------------------------------------------------
    if config["index"] and (has_cloud_id or has_host):
        print(f"\n[Test 5] Index Operations: {config['index']}")
        client = None
        try:
            # Use best available connection method
            if has_cloud_id:
                client = create_cloud_client_with_cloud_id(config)
            else:
                client = create_cloud_client_with_url(config)

            # Check if index exists
            exists = await check_index_exists(client, config["index"])
            if exists:
                print(f"  Index '{config['index']}' exists")

                # Get index stats
                try:
                    stats = await client.indices.stats(index=config["index"])
                    doc_count = stats["_all"]["primaries"]["docs"]["count"]
                    size_bytes = stats["_all"]["primaries"]["store"]["size_in_bytes"]
                    print(f"  Document count: {doc_count}")
                    print(f"  Size: {size_bytes / 1024 / 1024:.2f} MB")
                except Exception as e:
                    print(f"  Could not get stats: {e}")

                # Get index mapping
                try:
                    mapping = await client.indices.get_mapping(index=config["index"])
                    fields = list(mapping[config["index"]]["mappings"].get("properties", {}).keys())
                    print(f"  Fields: {len(fields)}")
                    if fields[:5]:
                        print(f"  Sample fields: {', '.join(fields[:5])}")
                except Exception as e:
                    print(f"  Could not get mapping: {e}")
            else:
                print(f"  Index '{config['index']}' does not exist")

        except Exception as e:
            print(f"  FAILURE: {format_connection_error(e, es_host or config['host'])}")
        finally:
            if client:
                await client.close()
    else:
        print("\n[Test 5] Index Operations - SKIPPED (no index specified)")

    # ---------------------------------------------------------
    # Test 6: Custom SSL context (for advanced scenarios)
    # ---------------------------------------------------------
    if has_cloud_id or has_host:
        print("\n[Test 6] Custom SSL Context")
        client = None
        try:
            ssl_context = ssl.create_default_context()
            # For Elastic Cloud, we typically want to verify certs
            ssl_context.check_hostname = True
            ssl_context.verify_mode = ssl.CERT_REQUIRED

            if has_cloud_id and has_api_key:
                client = AsyncElasticsearch(
                    cloud_id=config["cloud_id"],
                    api_key=config["api_key"],
                    ssl_context=ssl_context,
                )
            elif has_cloud_id and has_basic_auth:
                client = AsyncElasticsearch(
                    cloud_id=config["cloud_id"],
                    basic_auth=(config["user"], config["password"]),
                    ssl_context=ssl_context,
                )
            elif has_host and has_api_key:
                url = f"{config['scheme']}://{config['host']}:{config['port']}"
                client = AsyncElasticsearch(
                    url,
                    api_key=config["api_key"],
                    ssl_context=ssl_context,
                )
            elif has_host and has_basic_auth:
                url = f"{config['scheme']}://{config['host']}:{config['port']}"
                client = AsyncElasticsearch(
                    url,
                    basic_auth=(config["user"], config["password"]),
                    ssl_context=ssl_context,
                )
            else:
                print("  SKIPPED: No valid auth configuration")
                return

            info = await client.info()
            print(f"  SUCCESS: Connected with custom SSL context")
            print(f"  Version: {info['version']['number']}")

        except Exception as e:
            print(f"  FAILURE: {format_connection_error(e, es_host or config['host'])}")
        finally:
            if client:
                await client.close()

    print("\n" + "=" * 60)
    print("Tests completed")
    print("=" * 60)
    print("\nElastic Cloud Setup Guide:")
    print("  1. Create deployment at https://cloud.elastic.co")
    print("  2. Choose GCP as cloud provider")
    print("  3. Copy Cloud ID from deployment overview")
    print("  4. Create API key in Kibana -> Stack Management -> API Keys")
    print("  5. Set environment variables:")
    print("     export ELASTIC_CLOUD_ID='your-cloud-id'")
    print("     export ELASTICSEARCH_API_KEY='your-api-key'")


def main():
    if not ES_AVAILABLE:
        print("ERROR: elasticsearch is not installed")
        print("Install with: pip install elasticsearch==8.19.0")
        return

    asyncio.run(run_tests())


if __name__ == "__main__":
    main()
