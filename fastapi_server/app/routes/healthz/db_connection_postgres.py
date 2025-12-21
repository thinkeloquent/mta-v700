"""Postgres healthz routes."""

from fastapi import APIRouter
from db_connection_postgres import (
    PostgresConfig,
    get_db_manager,
    DatabaseConnectionError
)

router = APIRouter(prefix="/healthz/admin/db-connection-postgres", tags=["Admin"])


@router.get("/status")
async def postgres_status():
    """Postgres connection status."""
    try:
        config = PostgresConfig()
        manager = DatabaseManager(config)
        is_healthy = await manager.test_connection()
        await manager.dispose()
        return {
            "connected": is_healthy,
            "host": config.host,
            "database": config.database,
            "error": None,
        }
    except Exception as e:
        return {
            "connected": False,
            "host": None,
            "database": None,
            "error": str(e),
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
