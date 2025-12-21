"""Postgres healthz routes."""

from fastapi import APIRouter
from db_connection_postgres import (
    PostgresConfig,
    DatabaseManager,
    get_db_manager,
    DatabaseConnectionError
)

router = APIRouter(prefix="/healthz/admin/db-connection-postgres", tags=["Admin"])

# SSL modes to try in order of preference
SSL_MODES = [
    ("verify-full", "SSL with full verification"),
    ("verify-ca", "SSL with CA verification"),
    ("require", "SSL required, no verification"),
    ("prefer", "SSL preferred"),
    ("disable", "No SSL"),
]


async def try_connection(ssl_mode: str) -> dict:
    """Try connecting with a specific SSL mode."""
    try:
        config = PostgresConfig(ssl_mode=ssl_mode)
        manager = DatabaseManager(config)
        is_healthy = await manager.test_connection()
        await manager.dispose()
        return {
            "ssl_mode": ssl_mode,
            "connected": is_healthy,
            "error": None,
        }
    except Exception as e:
        return {
            "ssl_mode": ssl_mode,
            "connected": False,
            "error": str(e),
        }


@router.get("/status")
async def postgres_status():
    """Postgres connection status with current config."""
    try:
        config = PostgresConfig()
        manager = DatabaseManager(config)
        is_healthy = await manager.test_connection()
        await manager.dispose()
        return {
            "connected": is_healthy,
            "host": config.host,
            "database": config.database,
            "ssl_mode": config.ssl_mode,
            "error": None,
        }
    except Exception as e:
        return {
            "connected": False,
            "host": None,
            "database": None,
            "ssl_mode": None,
            "error": str(e),
        }


@router.get("/probe")
async def postgres_probe():
    """Try all SSL modes and report which ones work."""
    config = PostgresConfig()
    results = []

    for ssl_mode, description in SSL_MODES:
        result = await try_connection(ssl_mode)
        result["description"] = description
        results.append(result)

    # Find first successful connection
    successful = [r for r in results if r["connected"]]

    return {
        "host": config.host,
        "port": config.port,
        "database": config.database,
        "user": config.user,
        "current_ssl_mode": config.ssl_mode,
        "recommended_ssl_mode": successful[0]["ssl_mode"] if successful else None,
        "results": results,
    }


@router.get("/config")
async def postgres_config():
    """Postgres configuration."""
    config = PostgresConfig()
    return {
        "host": config.host,
        "port": config.port,
        "database": config.database,
        "user": config.user,
        "ssl_mode": config.ssl_mode,
    }
