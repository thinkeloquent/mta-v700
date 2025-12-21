#!/usr/bin/env python3
"""
PostgreSQL Connection Test - Python Client Integration

Authentication: Password
Protocol: PostgreSQL wire protocol (not HTTP)
Health Check: SELECT 1

Uses internal packages:
  - provider_api_getters: Credential resolution
  - app_static_config_yaml: YAML configuration loading
  - db_connection_postgres: Configuration resolution
"""
import asyncio
import os
import sys
from pathlib import Path
from typing import Any

# ============================================================================
# Project Setup - Add packages to path
# ============================================================================
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "packages_py" / "app_yaml_config" / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "packages_py" / "provider_api_getters" / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "packages_py" / "db_connection_postgres" / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "packages_py" / "env_resolve" / "src"))

# Load static config
from app_yaml_config import AppYamlConfig
CONFIG_DIR = PROJECT_ROOT / "common" / "config"
# Initialize with common files
static_config = AppYamlConfig.initialize(["server.yaml"], config_dir=str(CONFIG_DIR))

# Import internal packages
# Import internal packages
from db_connection_postgres.config import PostgresConfig

# ============================================================================
# Configuration
# ============================================================================
# Use PostgresConfig to resolve environment variables
pg_config = PostgresConfig()

# Helper to expose as dict for debugging/compatibility
CONFIG = {
    "POSTGRES_HOST": pg_config.host,
    "POSTGRES_PORT": pg_config.port,
    "POSTGRES_USER": pg_config.user,
    "POSTGRES_PASSWORD": pg_config.password,
    "POSTGRES_DB": pg_config.database,
    "POSTGRES_SCHEMA": pg_config.schema,
    "DEBUG": os.getenv("DEBUG", "true").lower() not in ("false", "0"),
}

def get_connection_url() -> str:
    """Get connection URL."""
    return pg_config.get_dsn()


# ============================================================================
# Health Check
# ============================================================================
async def health_check() -> dict[str, Any]:
    """Health check using asyncpg directly (ProviderHealthChecker removed)."""
    print("\n=== PostgreSQL Health Check (asyncpg) ===\n")
    try:
        return await health_check_asyncpg()
    except Exception as e:
        print(f"Health check failed: {e}")
        return {"success": False, "error": str(e)}

# ============================================================================
# Sample Operations using asyncpg
# ============================================================================
async def health_check_asyncpg() -> dict[str, Any]:
    """Perform health check using asyncpg."""
    print(f"Connecting to: {pg_config.host}:{pg_config.port}/{pg_config.database}")

    try:
        import asyncpg
    except ImportError:
        print("Error: asyncpg package not installed.")
        return {"success": False, "error": "asyncpg package not installed"}

    try:
        # Use kwd arguments from config
        conn = await asyncpg.connect(**pg_config.get_connection_kwargs())

        # Test connection
        result = await conn.fetchval("SELECT 1")
        print(f"SELECT 1: {result}")

        # Get version
        version = await conn.fetchval("SELECT version()")
        print(f"Version: {version}")

        # Get current database
        db = await conn.fetchval("SELECT current_database()")
        print(f"Database: {db}")

        await conn.close()

        return {"success": True, "data": {"version": version, "database": db}}
    except ImportError:
        print("Error: asyncpg package not installed. Run: pip install asyncpg")
        return {"success": False, "error": "asyncpg package not installed"}
    except Exception as e:
        print(f"Error: {e}")
        return {"success": False, "error": str(e)}


async def sample_operations() -> dict[str, Any]:
    """Perform sample PostgreSQL operations."""
    print("\n=== Sample PostgreSQL Operations ===\n")

    try:
        import asyncpg

        conn = await asyncpg.connect(**pg_config.get_connection_kwargs())

        # List schemas
        schemas = await conn.fetch("""
            SELECT schema_name
            FROM information_schema.schemata
            ORDER BY schema_name
        """)
        print("Schemas:")
        for schema in schemas[:10]:
            print(f"  - {schema['schema_name']}")

        # List tables in public schema
        tables = await conn.fetch("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = $1
            ORDER BY table_name
        """, pg_config.schema)
        print(f"\nTables in {pg_config.schema}:")
        for table in tables[:10]:
            print(f"  - {table['table_name']}")

        # Get database size
        size = await conn.fetchval("""
            SELECT pg_size_pretty(pg_database_size(current_database()))
        """)
        print(f"\nDatabase size: {size}")

        await conn.close()

        return {"success": True}
    except ImportError:
        print("Error: asyncpg package not installed. Run: pip install asyncpg")
        return {"success": False, "error": "asyncpg package not installed"}
    except Exception as e:
        print(f"Error: {e}")
        return {"success": False, "error": str(e)}


# ============================================================================
# Run Tests
# ============================================================================
async def main():
    """Run connection tests."""
    print("PostgreSQL Connection Test (Python Client Integration)")
    print("=" * 55)
    print(f"Host: {pg_config.host}:{pg_config.port}")
    print(f"Database: {pg_config.database}")
    print(f"User: {pg_config.user}")
    print(f"Schema: {pg_config.schema}")
    print(f"SSL: {pg_config.ssl_mode}")

    await health_check()

    # Uncomment to run additional tests:
    # await health_check_asyncpg()
    # await sample_operations()


if __name__ == "__main__":
    asyncio.run(main())
