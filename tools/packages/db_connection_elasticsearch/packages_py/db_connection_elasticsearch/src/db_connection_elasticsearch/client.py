import logging
import asyncio
from typing import Any, Dict, Optional, Union

try:
    from elasticsearch import AsyncElasticsearch, Elasticsearch, ConnectionError as EsConnectionError, TransportError
    ES_AVAILABLE = True
except ImportError:
    AsyncElasticsearch = None
    Elasticsearch = None
    EsConnectionError = Exception
    TransportError = Exception
    ES_AVAILABLE = False

try:
    from opensearchpy import OpenSearch, AsyncOpenSearch
    OPENSEARCH_AVAILABLE = True
except ImportError:
    OpenSearch = None
    AsyncOpenSearch = None
    OPENSEARCH_AVAILABLE = False

from .config import ElasticsearchConfig, ElasticsearchConfigError
from .constants import VENDOR_ELASTIC_CLOUD, VENDOR_DIGITAL_OCEAN

logger = logging.getLogger(__name__)

class ElasticsearchConnectionError(Exception):
    """Connection failure."""
    pass

class ElasticsearchDependencyError(ImportError):
    """Missing elasticsearch/opensearch package."""
    pass

def _check_dependencies(vendor_type: str = None):
    if vendor_type == VENDOR_DIGITAL_OCEAN:
        if not OPENSEARCH_AVAILABLE:
            raise ElasticsearchDependencyError("opensearch-py package is not installed. Install with 'pip install opensearch-py'")
    else:
        if not ES_AVAILABLE:
            raise ElasticsearchDependencyError("elasticsearch package is not installed. Install with 'pip install elasticsearch'")

def _get_opensearch_kwargs(cfg: ElasticsearchConfig) -> Dict[str, Any]:
    """Convert Elasticsearch kwargs to OpenSearch format."""
    kwargs: Dict[str, Any] = {
        "timeout": cfg.request_timeout,
        "max_retries": cfg.max_retries,
        "retry_on_timeout": cfg.retry_on_timeout,
    }

    # Authentication - OpenSearch uses http_auth tuple
    if cfg.username and cfg.password:
        kwargs["http_auth"] = (cfg.username, cfg.password)

    # SSL configuration
    kwargs["use_ssl"] = cfg.use_tls or cfg.scheme == "https"
    kwargs["verify_certs"] = cfg.verify_certs
    kwargs["ssl_show_warn"] = cfg.ssl_show_warn

    if cfg.ca_certs:
        kwargs["ca_certs"] = cfg.ca_certs
    if cfg.client_cert:
        kwargs["client_cert"] = cfg.client_cert
    if cfg.client_key:
        kwargs["client_key"] = cfg.client_key

    # Host configuration
    kwargs["hosts"] = [{"host": cfg.host, "port": cfg.port}]

    return kwargs

async def get_elasticsearch_client(config: Optional[Union[ElasticsearchConfig, Dict[str, Any]]] = None):
    """Create async client (AsyncElasticsearch or AsyncOpenSearch based on vendor)."""
    if config is None:
        cfg = ElasticsearchConfig()
    elif isinstance(config, dict):
        cfg = ElasticsearchConfig(config=config)
    else:
        cfg = config

    _check_dependencies(cfg.vendor_type)

    # Use OpenSearch for DigitalOcean
    if cfg.vendor_type == VENDOR_DIGITAL_OCEAN:
        logger.info("Initializing AsyncOpenSearch client for DigitalOcean...")
        kwargs = _get_opensearch_kwargs(cfg)
    else:
        logger.info("Initializing AsyncElasticsearch client...")
        kwargs = cfg.get_connection_kwargs()

    # Log sanitized args (redact secrets for safety)
    safe_kwargs = kwargs.copy()
    if "api_key" in safe_kwargs: safe_kwargs["api_key"] = "***"
    if "basic_auth" in safe_kwargs: safe_kwargs["basic_auth"] = ("***", "***")
    if "http_auth" in safe_kwargs: safe_kwargs["http_auth"] = ("***", "***")
    logger.debug(f"Client kwargs: {safe_kwargs}")

    try:
        if cfg.vendor_type == VENDOR_DIGITAL_OCEAN:
            client = AsyncOpenSearch(**kwargs)
        else:
            client = AsyncElasticsearch(**kwargs)

        if cfg.verify_cluster_connection:
            logger.info("Verifying cluster connection...")
            if not await client.ping():
                await client.close()
                raise ElasticsearchConnectionError("Ping failed during initialization")
            logger.info("Connection verified.")

        return client
    except Exception as e:
        logger.error(f"Failed to create async client: {e}")
        raise ElasticsearchConnectionError(f"Failed to create client: {e}") from e

def get_sync_elasticsearch_client(config: Optional[Union[ElasticsearchConfig, Dict[str, Any]]] = None):
    """Create synchronous client (Elasticsearch or OpenSearch based on vendor)."""
    if config is None:
        cfg = ElasticsearchConfig()
    elif isinstance(config, dict):
        cfg = ElasticsearchConfig(config=config)
    else:
        cfg = config

    _check_dependencies(cfg.vendor_type)

    # Use OpenSearch for DigitalOcean
    if cfg.vendor_type == VENDOR_DIGITAL_OCEAN:
        logger.info("Initializing Sync OpenSearch client for DigitalOcean...")
        kwargs = _get_opensearch_kwargs(cfg)
        return OpenSearch(**kwargs)
    elif cfg.vendor_type == VENDOR_ELASTIC_CLOUD:
        logger.info("Initializing Sync Elasticsearch client for Cloud...")
        kwargs = cfg.get_connection_kwargs()
        return Elasticsearch(**kwargs)
    else:
        logger.info("Initializing Sync Elasticsearch client...")
        kwargs = cfg.get_connection_kwargs()
        return Elasticsearch(**kwargs)

async def check_connection(config: Optional[ElasticsearchConfig] = None) -> Dict[str, Any]:
    """Check connection health."""
    client = None
    try:
        client = await get_elasticsearch_client(config)
        info = await client.info()
        return {
            "success": True,
            "info": info
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        host = config.host if config else "unknown"
        return {
            "success": False,
            "error": format_connection_error(e, host)
        }
    finally:
        if client:
            await client.close()

def format_connection_error(err: Exception, host: str) -> str:
    """Format error into human-readable message."""
    # Logic to format error
    msg = str(err)
    if "Connection refused" in msg:
        return f"Connection refused to {host}. Check if server is running."
    if "SSLError" in msg:
        return f"SSL Error connecting to {host}. Check certs."
    return f"Connection error to {host}: {msg}"
