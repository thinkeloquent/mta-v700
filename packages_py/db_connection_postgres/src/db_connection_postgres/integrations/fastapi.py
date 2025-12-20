from contextlib import asynccontextmanager
from typing import AsyncGenerator, Annotated

from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..session import get_db_manager, DatabaseManager
from ..config import DatabaseConfig

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides an async database session.
    """
    manager = get_db_manager()
    async with manager.async_session() as session:
        yield session

SessionDep = Annotated[AsyncSession, Depends(get_db)]

def create_db_lifespan(config: DatabaseConfig = None):
    """
    Create a lifespan context manager for FastAPI applications.
    Handles initializing and closing the database connection pool.
    """
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup
        manager = get_db_manager(config)
        # Verify connection on startup
        is_connected = await manager.test_connection()
        if not is_connected:
             # Log warning but don't crash app? Or crash?
             # Spec doesn't specify crash, but robust systems usually retry or fail fast.
             # We rely on manager logging error.
             pass
             
        yield
        
        # Shutdown
        await manager.dispose()
        
    return lifespan

async def init_db(config: DatabaseConfig = None) -> None:
    """Initialize the database manager (manual)."""
    get_db_manager(config)

async def close_db() -> None:
    """Close the database manager (manual)."""
    manager = get_db_manager()
    await manager.dispose()
