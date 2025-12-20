import logging
try:
    import asyncpg
except ImportError:
    asyncpg = None

from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine

from .config import DatabaseConfig
from .exceptions import DatabaseImportError

logger = logging.getLogger(__name__)

async def get_async_postgres_pool(config: DatabaseConfig) -> "asyncpg.Pool":
    """
    Create and return an asyncpg connection pool.
    """
    if asyncpg is None:
        raise DatabaseImportError("asyncpg is not installed")
        
    dsn = str(config.get_async_url().render_as_string(hide_password=False)).replace("+asyncpg", "")
    # Note: connect_args might contain ssl context which asyncpg needs differently if resolving URL manually,
    # but here we can pass params directly or use the DSN.
    # The config.get_connect_args() returns SSL context for SQLAlchemy. 
    # For raw asyncpg pool, we need to adapt.
    
    ssl_ctx = config.get_connect_args().get("ssl")
    
    logger.info(f"Creating asyncpg pool for host={config.host} port={config.port} db={config.database}")
    
    return await asyncpg.create_pool(
        user=config.user,
        password=config.password,
        host=config.host,
        port=config.port,
        database=config.database,
        min_size=config.pool_size,
        max_size=config.pool_size + config.max_overflow,
        timeout=config.pool_timeout,
        ssl=ssl_ctx
    )

def get_async_sqlalchemy_engine(config: DatabaseConfig) -> AsyncEngine:
    """
    Create and return a SQLAlchemy AsyncEngine.
    """
    url = config.get_async_url()
    connect_args = config.get_connect_args()
    
    logger.info(f"Creating SQLAlchemy AsyncEngine for {url.render_as_string(hide_password=True)}")
    
    return create_async_engine(
        url,
        echo=config.echo,
        pool_size=config.pool_size,
        max_overflow=config.max_overflow,
        pool_timeout=config.pool_timeout,
        pool_recycle=config.pool_recycle,
        connect_args=connect_args,
    )
