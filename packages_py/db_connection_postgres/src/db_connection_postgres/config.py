
import os
import ssl
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from sqlalchemy.engine.url import URL, make_url

from .exceptions import DatabaseConfigError
from .schemas import DatabaseConfigValidator
from .constants import (
    ENV_POSTGRES_HOST,
    ENV_POSTGRES_PORT,
    ENV_POSTGRES_USER,
    ENV_POSTGRES_USERNAME,
    ENV_POSTGRES_PASSWORD,
    ENV_POSTGRES_DB,
    ENV_POSTGRES_SCHEMA,
    ENV_POSTGRES_SSL_MODE,
    ENV_POSTGRES_SSL_CA_FILE,
    ENV_POSTGRES_SSL_CHECK_HOSTNAME,
    ENV_POSTGRES_ECHO,
    ENV_POSTGRES_POOL_SIZE,
    ENV_POSTGRES_MAX_OVERFLOW,
    ENV_POSTGRES_POOL_TIMEOUT,
    ENV_POSTGRES_POOL_RECYCLE,
)
from env_resolve.core import resolve, resolve_bool, resolve_int

@dataclass
class PostgresConfig:
    """
    Configuration for PostgreSQL connection.
    Resolves parameters from source of truth in order:
    1. Direct constructor arguments
    2. Environment variables
    3. Config dictionary
    4. Default values
    """
    host: str = field(default="localhost")
    port: int = field(default=5432)
    user: str = field(default="postgres")
    password: Optional[str] = field(default=None)
    database: str = field(default="postgres")
    schema: str = field(default="public")
    ssl_mode: str = field(default="prefer")
    ssl_ca_file: Optional[str] = field(default=None)
    ssl_check_hostname: bool = field(default=True)
    pool_size: int = field(default=5)
    max_overflow: int = field(default=10)
    pool_timeout: int = field(default=30)
    pool_recycle: int = field(default=3600)
    echo: bool = field(default=False)

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
        schema: Optional[str] = None,
        ssl_mode: Optional[str] = None,
        ssl_ca_file: Optional[str] = None,
        ssl_check_hostname: Optional[bool] = None,
        pool_size: Optional[int] = None,
        max_overflow: Optional[int] = None,
        pool_timeout: Optional[int] = None,
        pool_recycle: Optional[int] = None,
        echo: Optional[bool] = None
    ):
        # Resolve values
        self.host = resolve(host, ENV_POSTGRES_HOST, config, "host", "localhost")
        self.port = resolve_int(port, ENV_POSTGRES_PORT, config, "port", 5432)
        self.user = resolve(user, ENV_POSTGRES_USER, config, "user", "postgres")
        # Support POSTGRES_USERNAME as fallback for user
        if self.user == "postgres":
             self.user = resolve(None, ENV_POSTGRES_USERNAME, None, None, "postgres")
        
        self.password = resolve(password, ENV_POSTGRES_PASSWORD, config, "password", None)
        self.database = resolve(database, ENV_POSTGRES_DB, config, "database", "postgres")
        self.schema = resolve(schema, ENV_POSTGRES_SCHEMA, config, "schema", "public")
        # Check multiple env var names for SSL mode (POSTGRES_SSL_MODE, POSTGRES_SSLMODE, DATABASE_SSL_MODE)
        self.ssl_mode = resolve(ssl_mode, ENV_POSTGRES_SSL_MODE, config, "ssl_mode", "prefer")
        # Handle boolean-like values: true/false -> require/disable
        if self.ssl_mode in ("true", "1", "yes", "on"):
            self.ssl_mode = "require"
        elif self.ssl_mode in ("false", "0", "no", "off"):
            self.ssl_mode = "disable"
        self.ssl_ca_file = resolve(ssl_ca_file, ENV_POSTGRES_SSL_CA_FILE, config, "ssl_ca_file", None)
        
        # Booleans need careful handling from env
        self.ssl_check_hostname = resolve_bool(ssl_check_hostname, ENV_POSTGRES_SSL_CHECK_HOSTNAME, config, "ssl_check_hostname", True)
        self.echo = resolve_bool(echo, ENV_POSTGRES_ECHO, config, "echo", False)
        
        # Pool settings
        self.pool_size = resolve_int(pool_size, ENV_POSTGRES_POOL_SIZE, config, "pool_size", 5)
        self.max_overflow = resolve_int(max_overflow, ENV_POSTGRES_MAX_OVERFLOW, config, "max_overflow", 10)
        self.pool_timeout = resolve_int(pool_timeout, ENV_POSTGRES_POOL_TIMEOUT, config, "pool_timeout", 30)
        self.pool_recycle = resolve_int(pool_recycle, ENV_POSTGRES_POOL_RECYCLE, config, "pool_recycle", 3600)

        # Check for DATABASE_URL override
        db_url_env = os.getenv("DATABASE_URL")
        if db_url_env:
            self._parse_database_url(db_url_env)

        # Validate
        self.validate()

    def _parse_database_url(self, url: str) -> None:
        """Parse DATABASE_URL and override config."""
        try:
            u = make_url(url)
            self.host = u.host or self.host
            self.port = u.port or self.port
            self.user = u.username or self.user
            self.password = u.password or self.password
            self.database = u.database or self.database
            # Extract query params if needed
        except Exception as e:
            raise DatabaseConfigError(f"Invalid DATABASE_URL: {e}")

    def validate(self) -> None:
        """Validate configuration using Pydantic."""
        try:
            DatabaseConfigValidator(**self.__dict__)
        except Exception as e:
            raise DatabaseConfigError(f"Configuration validation failed: {str(e)}")

    def get_dsn(self) -> str:
        """Get DSN string."""
        return str(self.get_async_url())

    def get_async_url(self) -> URL:
        """Return SQLAlchemy URL for asyncpg."""
        return URL.create(
            drivername="postgresql+asyncpg",
            username=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.database,
        )

    def get_sync_url(self) -> URL:
        """Return SQLAlchemy URL for psycopg2."""
        return URL.create(
            drivername="postgresql+psycopg2",
            username=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.database,
        )

    def get_connection_kwargs(self) -> Dict[str, Any]:
        """Get connection arguments for asyncpg, including SSL context."""
        connect_args = {}
        
        # Configure SSL
        if self.ssl_mode != "disable":
            ssl_context = ssl.create_default_context()
            
            if self.ssl_ca_file:
                ssl_context.load_verify_locations(cafile=self.ssl_ca_file)
            
            # Per PostgreSQL SSL modes:
            # - require: encrypt but don't verify certificate
            # - verify-ca: encrypt and verify CA signature
            # - verify-full: encrypt, verify CA, and verify hostname
            if self.ssl_mode in ("verify-ca", "verify-full"):
                ssl_context.check_hostname = self.ssl_check_hostname and (self.ssl_mode == "verify-full")
                ssl_context.verify_mode = ssl.CERT_REQUIRED
            else:
                # "require", "allow", "prefer" - encrypt without cert verification
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                
            connect_args["ssl"] = ssl_context
            
        connect_args["user"] = self.user
        connect_args["password"] = self.password
        connect_args["host"] = self.host
        connect_args["port"] = self.port
        connect_args["database"] = self.database

        # Add server_settings for schema search_path
        if self.schema:
            connect_args["server_settings"] = {"search_path": self.schema}
            
        return connect_args

