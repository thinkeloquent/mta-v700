import asyncio
import os
import sys
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from sqlalchemy import URL

load_dotenv()

def get_db_url_object():
    """Build URL object from components."""
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = int(os.getenv("POSTGRES_PORT", "5432"))
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    dbname = os.getenv("POSTGRES_DB", "postgres")

    # Ensure host is valid
    if not host: 
        host = "localhost"

    return URL.create(
        drivername="postgresql+asyncpg",
        username=user,
        password=password,
        host=host,
        port=port,
        database=dbname,
    )

async def main():
    print("="*60)
    print("SQLAlchemy + asyncpg Connection Test (Enhanced with Pooling)")
    print("="*60)

    # Always build from components to ensure validity
    url_obj = get_db_url_object()
    url_str = url_obj.render_as_string(hide_password=False)

    print(f"Config:")
    print(f"  Target URL: {url_str.replace(os.getenv('POSTGRES_PASSWORD', 'postgres'), '***')}")
    print(f"  Host: {url_obj.host}:{url_obj.port}")

    # ---------------------------------------------------------
    # Test: Pooled Connection
    # ---------------------------------------------------------
    print("\n[Test Pool] Explicit String Construction + Pooling Config")
    try:
        engine = create_async_engine(
            url_str,
            connect_args={"ssl": "disable"},
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True
        )
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            print(f"  SUCCESS: Connected via Pool!")
            
            # Print pool status if available
            print(f"  Pool Status: {engine.pool.status()}")
            
        await engine.dispose()
    except Exception as e:
        print(f"  FAILURE: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
