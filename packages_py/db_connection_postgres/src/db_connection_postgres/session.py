import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional, Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, AsyncEngine
from sqlalchemy import text

from .config import PostgresConfig
from .client import get_async_sqlalchemy_engine
from .exceptions import DatabaseConnectionError

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Manages database connection and session lifecycle.
    """
    
    def __init__(self, config: Optional[PostgresConfig] = None, base: Optional[Any] = None):
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker[AsyncSession]] = None
        
        self.config = config or PostgresConfig()
        
    @property
    def engine(self) -> AsyncEngine:
        """Lazy load engine."""
        if self._engine is None:
            self._engine = get_async_sqlalchemy_engine(self.config)
        return self._engine
        
    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Lazy load session factory."""
        if self._session_factory is None:
            self._session_factory = async_sessionmaker(
                bind=self.engine,
                expire_on_commit=False,
                class_=AsyncSession
            )
        return self._session_factory

    @asynccontextmanager
    async def async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Async context manager provided a transactional session.
        Commits on success, rolls back on error, closes on exit.
        """
        session = self.session_factory()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Session rollback due to exception: {e}")
            raise
        finally:
            await session.close()
            
    async def test_connection(self) -> bool:
        """Test connectivity by executing SELECT 1."""
        try:
            async with self.async_session() as session:
                await session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    async def dispose(self) -> None:
        """Dispose of the connection pool."""
        if self._engine:
            await self._engine.dispose()
            self._engine = None

_db_manager: Optional[DatabaseManager] = None

def get_db_manager(config: Optional[PostgresConfig] = None) -> DatabaseManager:
    """Get or create the global DatabaseManager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager(config)
    return _db_manager

def reset_db_manager() -> None:
    """Reset global manager (useful for tests)."""
    global _db_manager
    _db_manager = None
