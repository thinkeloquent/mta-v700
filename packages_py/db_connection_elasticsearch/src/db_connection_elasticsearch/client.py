import logging
import asyncio
from typing import Any, Dict, Optional, Union

try:
    from elasticsearch import AsyncElasticsearch, Elasticsearch, ConnectionError as EsConnectionError, TransportError
except ImportError:
    AsyncElasticsearch = None
    Elasticsearch = None
    EsConnectionError = Exception
    TransportError = Exception

from .config import ElasticsearchConfig, ElasticsearchConfigError
from .constants import VENDOR_ELASTIC_CLOUD, VENDOR_DIGITAL_OCEAN

logger = logging.getLogger(__name__)

class ElasticsearchConnectionError(Exception):
    """Connection failure."""
    pass

class ElasticsearchDependencyError(ImportError):
    """Missing elasticsearch package."""
    pass
    
def _check_dependencies():
    if AsyncElasticsearch is None:
        raise ElasticsearchDependencyError("elasticsearch package is not installed. Install with 'pip install elasticsearch'")

async def get_elasticsearch_client(config: Optional[Union[ElasticsearchConfig, Dict[str, Any]]] = None) -> AsyncElasticsearch:
    """Create AsyncElasticsearch client."""
    _check_dependencies()
    
    logger.info("Initializing AsyncElasticsearch client...")
    
    if config is None:
        cfg = ElasticsearchConfig()
    elif isinstance(config, dict):
        cfg = ElasticsearchConfig(config=config)
    else:
        cfg = config
        
    kwargs = cfg.get_connection_kwargs()
    
    # Log sanitized args (redact secrets for safety)
    safe_kwargs = kwargs.copy()
    if "api_key" in safe_kwargs: safe_kwargs["api_key"] = "***"
    if "basic_auth" in safe_kwargs: safe_kwargs["basic_auth"] = ("***", "***")
    logger.debug(f"Client kwargs: {safe_kwargs}")
    
    try:
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

def get_sync_elasticsearch_client(config: Optional[Union[ElasticsearchConfig, Dict[str, Any]]] = None) -> Elasticsearch:
    """Create synchronous Elasticsearch client."""
    _check_dependencies()
    
    logger.info("Initializing Sync Elasticsearch client...")
    
    if config is None:
        cfg = ElasticsearchConfig()
    elif isinstance(config, dict):
        cfg = ElasticsearchConfig(config=config)
    else:
        cfg = config

    if cfg.vendor_type == VENDOR_ELASTIC_CLOUD:
        return _create_sync_cloud_client(cfg)
    else:
        return _create_sync_url_client(cfg)

def _create_sync_cloud_client(cfg: ElasticsearchConfig) -> Elasticsearch:
    """Create sync client for Cloud."""
    logger.debug("Creating sync cloud client")
    kwargs = cfg.get_connection_kwargs()
    return Elasticsearch(**kwargs)

def _create_sync_url_client(cfg: ElasticsearchConfig) -> Elasticsearch:
    """Create sync client for URL/On-Prem."""
    logger.debug("Creating sync URL client")
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
