"""Elasticsearch healthz routes."""

from fastapi import APIRouter
from db_connection_elasticsearch import (
    ElasticsearchConfig,
    check_connection,
)

router = APIRouter(prefix="/healthz/admin/db-connection-elasticsearch", tags=["Admin"])


@router.get("/status")
async def elasticsearch_status():
    """Elasticsearch connection status."""
    config = ElasticsearchConfig()
    result = await check_connection(config)
    return {
        "connected": result.get("success", False),
        "cluster_name": result.get("info", {}).get("cluster_name") if result.get("info") else None,
        "version": result.get("info", {}).get("version", {}).get("number") if result.get("info") else None,
        "error": result.get("error"),
    }


@router.get("/config")
async def elasticsearch_config():
    """Elasticsearch configuration."""
    config = ElasticsearchConfig()
    return {
        "host": config.host,
        "port": config.port,
        "scheme": config.scheme,
        "vendor_type": config.vendor_type,
        "use_tls": config.use_tls,
        "verify_certs": config.verify_certs,
    }
