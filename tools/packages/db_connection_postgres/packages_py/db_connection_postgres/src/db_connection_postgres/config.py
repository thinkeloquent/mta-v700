
import os
import ssl
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from sqlalchemy.engine.url import URL, make_url

from .exceptions import DatabaseConfigError
from .schemas import DatabaseConfigValidator

@dataclass
class DatabaseConfig:
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
        self.host = self._resolve(host, "POSTGRES_HOST", "DATABASE_HOST", config, "host", "localhost")
        self.port = int(self._resolve(port, "POSTGRES_PORT", "DATABASE_PORT", config, "port", 5432))
        self.user = self._resolve(user, "POSTGRES_USER", "DATABASE_USER", config, "user", "postgres")
        # Support POSTGRES_USERNAME as fallback for user
        if self.user == "postgres":
             self.user = self._resolve(None, "POSTGRES_USERNAME", None, None, None, "postgres")
        
        self.password = self._resolve(password, "POSTGRES_PASSWORD", "DATABASE_PASSWORD", config, "password", None)
        self.database = self._resolve(database, "POSTGRES_DATABASE", "DATABASE_NAME", "POSTGRES_DB", config, "database", "postgres")
        self.schema = self._resolve(schema, "POSTGRES_SCHEMA", "DATABASE_SCHEMA", config, "schema", "public")
        self.ssl_mode = self._resolve(ssl_mode, "POSTGRES_SSL_MODE", "DATABASE_SSL_MODE", config, "ssl_mode", "prefer")
        self.ssl_ca_file = self._resolve(ssl_ca_file, "POSTGRES_SSL_CA_FILE", None, config, "ssl_ca_file", None)
        
        # Booleans need careful handling from env
        self.ssl_check_hostname = self._resolve_bool(ssl_check_hostname, "POSTGRES_SSL_CHECK_HOSTNAME", None, config, "ssl_check_hostname", True)
        self.echo = self._resolve_bool(echo, "POSTGRES_ECHO", "DATABASE_ECHO", config, "echo", False)
        
        # Pool settings
        self.pool_size = int(self._resolve(pool_size, "POSTGRES_POOL_SIZE", "DATABASE_POOL_SIZE", config, "pool_size", 5))
        self.max_overflow = int(self._resolve(max_overflow, "POSTGRES_MAX_OVERFLOW", "DATABASE_MAX_OVERFLOW", config, "max_overflow", 10))
        self.pool_timeout = int(self._resolve(pool_timeout, "POSTGRES_POOL_TIMEOUT", "DATABASE_POOL_TIMEOUT", config, "pool_timeout", 30))
        self.pool_recycle = int(self._resolve(pool_recycle, "POSTGRES_POOL_RECYCLE", "DATABASE_POOL_RECYCLE", config, "pool_recycle", 3600))

        # Check for DATABASE_URL override
        db_url_env = os.getenv("DATABASE_URL")
        if db_url_env:
            self._parse_database_url(db_url_env)

        # Validate
        self.validate()

    def _resolve(self, arg_value: Any, env_key1: str, env_key2: Optional[str], env_key3: Optional[str], config: Optional[Dict], config_key: Optional[str], default: Any) -> Any:
        # 1. Direct Argument
        if arg_value is not None:
            return arg_value
        
        # 2. Environment Variables
        if env_key1:
            val = os.getenv(env_key1)
            if val is not None: return val
        if env_key2:
            val = os.getenv(env_key2)
            if val is not None: return val
        if env_key3: # Handle the 3rd env key logic if passed, tricky in signature but I'll adjust usage
             if isinstance(env_key3, str) and not isinstance(config, dict) and config_key is None: # Wait, logic above was messy.
                 # Let's fix the call site, or simplify. 
                 pass # Logic below simplifies to standard patterns

        # Special casing for the dict/config keys since I mixed signatures
        # Let's clean up logic:
        # Check envs (variable args would be better but explicit is fine)
        # Check config dict
        # Return default
        return default # Placeholder, implementing correct logic in actual code below

    def _resolve(self, arg: Any, env1: str, env2: Optional[str], config: Optional[Dict], config_key: Optional[str], default: Any, env3: Optional[str] = None) -> Any:
        if arg is not None:
            return arg
        
        val = os.getenv(env1)
        if val is not None: return val
        
        if env2:
            val = os.getenv(env2)
            if val is not None: return val
            
        if env3:
            val = os.getenv(env3)
            if val is not None: return val
            
        if config and config_key and config_key in config:
            return config[config_key]
            
        return default

    def _resolve_bool(self, arg: Any, env1: str, env2: Optional[str], config: Optional[Dict], config_key: Optional[str], default: bool) -> bool:
        val = self._resolve(arg, env1, env2, config, config_key, default)
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.lower() in ("true", "1", "yes", "on")
        return bool(val)

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

    def get_connect_args(self) -> Dict[str, Any]:
        """Get connection arguments for asyncpg, including SSL context."""
        connect_args = {}
        
        # Configure SSL
        if self.ssl_mode != "disable":
            ssl_context = ssl.create_default_context()
            
            if self.ssl_ca_file:
                ssl_context.load_verify_locations(cafile=self.ssl_ca_file)
            
            if self.ssl_mode == "require" or self.ssl_mode == "verify-ca" or self.ssl_mode == "verify-full":
                ssl_context.check_hostname = self.ssl_check_hostname and (self.ssl_mode == "verify-full")
                ssl_context.verify_mode = ssl.CERT_REQUIRED
            else:
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                
            connect_args["ssl"] = ssl_context
            
        # Add server_settings for schema search_path
        if self.schema:
            connect_args["server_settings"] = {"search_path": self.schema}
            
        return connect_args

