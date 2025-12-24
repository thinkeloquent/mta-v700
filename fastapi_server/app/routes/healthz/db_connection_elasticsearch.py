"""Elasticsearch healthz routes."""

from fastapi import APIRouter, Request
from db_connection_elasticsearch import (
    ElasticsearchConfig,
    check_connection,
)
from app_yaml_config import AppYamlConfig
from yaml_config_factory import YamlConfigFactory, create_runtime_config_response

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
async def elasticsearch_config(request: Request):
    """Elasticsearch configuration."""
    config_instance = AppYamlConfig.get_instance()
    factory = YamlConfigFactory(config_instance)
    result = await factory.compute_all("storages.elasticsearch", request=request)
    return create_runtime_config_response(result)
