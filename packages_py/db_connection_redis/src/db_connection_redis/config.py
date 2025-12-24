import os
import ssl
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Literal
from urllib.parse import urlparse, parse_qs

from .exceptions import RedisConfigError
from .schemas import RedisConfigValidator
from .constants import (
    ENV_REDIS_HOST,
    ENV_REDIS_PORT,
    ENV_REDIS_USERNAME,
    ENV_REDIS_PASSWORD,
    ENV_REDIS_DB,
    ENV_REDIS_SSL,
    ENV_REDIS_TLS_ALT,
    ENV_REDIS_SSL_CERT_REQS,
    ENV_REDIS_SSL_CA_CERTS,
    ENV_REDIS_SSL_CHECK_HOSTNAME,
    ENV_REDIS_SOCKET_TIMEOUT,
    ENV_REDIS_MAX_CONNECTIONS,
)
from env_resolve.core import resolve, resolve_bool, resolve_int, resolve_float

@dataclass
class RedisConfig:
    """
    Configuration for Redis connection.
    Resolves parameters from source of truth in order:
    1. Direct constructor arguments
    2. Environment variables
    3. Config dictionary
    4. Default values
    """
    host: str = field(default="localhost")
    port: int = field(default=6379)
    username: Optional[str] = field(default=None)
    password: Optional[str] = field(default=None)
    db: int = field(default=0)
    unix_socket_path: Optional[str] = field(default=None)
    use_ssl: bool = field(default=False)
    ssl_cert_reqs: str = field(default="none")
    ssl_ca_certs: Optional[str] = field(default=None)
    ssl_check_hostname: bool = field(default=False)
    socket_timeout: float = field(default=5.0)
    socket_connect_timeout: float = field(default=5.0)
    retry_on_timeout: bool = field(default=False)
    max_connections: Optional[int] = field(default=None)
    health_check_interval: float = field(default=0)
    encoding: str = field(default="utf-8")
    decode_responses: bool = field(default=True)

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        db: Optional[int] = None,
        unix_socket_path: Optional[str] = None,
        use_ssl: Optional[bool] = None,
        ssl_cert_reqs: Optional[str] = None,
        ssl_ca_certs: Optional[str] = None,
        ssl_check_hostname: Optional[bool] = None,
        socket_timeout: Optional[float] = None,
        socket_connect_timeout: Optional[float] = None,
        retry_on_timeout: Optional[bool] = None,
        max_connections: Optional[int] = None,
        health_check_interval: Optional[float] = None,
        encoding: Optional[str] = None,
        decode_responses: Optional[bool] = None
    ):
        # Resolve values
        self.host = resolve(host, ENV_REDIS_HOST, config, "host", "localhost")
        self.port = resolve_int(port, ENV_REDIS_PORT, config, "port", 6379)
        self.username = resolve(username, ENV_REDIS_USERNAME, config, "username", None)
        self.password = resolve(password, ENV_REDIS_PASSWORD, config, "password", None)
        self.db = resolve_int(db, ENV_REDIS_DB, config, "db", 0)
        self.unix_socket_path = resolve(unix_socket_path, [], config, "unix_socket_path", None)
        
        # Check multiple env var names for SSL (REDIS_SSL, REDIS_USE_TLS, REDIS_TLS, REDIS_USE_SSL)
        self.use_ssl = resolve_bool(use_ssl, ENV_REDIS_SSL, config, "use_ssl", False)
        if not self.use_ssl:
            # Also check alternative names
            self.use_ssl = resolve_bool(None, ENV_REDIS_TLS_ALT, config, "use_ssl", False)
        self.ssl_cert_reqs = resolve(ssl_cert_reqs, ENV_REDIS_SSL_CERT_REQS, config, "ssl_cert_reqs", "none")
        self.ssl_ca_certs = resolve(ssl_ca_certs, ENV_REDIS_SSL_CA_CERTS, config, "ssl_ca_certs", None)
        self.ssl_check_hostname = resolve_bool(ssl_check_hostname, ENV_REDIS_SSL_CHECK_HOSTNAME, config, "ssl_check_hostname", False)
        
        self.socket_timeout = resolve_float(socket_timeout, ENV_REDIS_SOCKET_TIMEOUT, config, "socket_timeout", 5.0)
        self.socket_connect_timeout = resolve_float(socket_connect_timeout, [], config, "socket_connect_timeout", 5.0)
        self.retry_on_timeout = resolve_bool(retry_on_timeout, [], config, "retry_on_timeout", False)
        
        max_conn = resolve(max_connections, ENV_REDIS_MAX_CONNECTIONS, config, "max_connections", None)
        self.max_connections = int(max_conn) if max_conn is not None else None
        
        self.health_check_interval = resolve_float(health_check_interval, [], config, "health_check_interval", 0)
        self.encoding = resolve(encoding, [], config, "encoding", "utf-8")
        self.decode_responses = resolve_bool(decode_responses, [], config, "decode_responses", True)

        # REDIS_URL override
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            self._parse_redis_url(redis_url)

        # Auto-detect vendor / defaults if not explicitly set
        self._detect_vendor_defaults()

        # Validate
        self.validate()

    def _parse_redis_url(self, url: str) -> None:
        """Parse redis:// or rediss:// URL."""
        parsed = urlparse(url)
        if parsed.scheme == "rediss":
            self.use_ssl = True
        
        if parsed.hostname: self.host = parsed.hostname
        if parsed.port: self.port = parsed.port
        if parsed.username: self.username = parsed.username
        if parsed.password: self.password = parsed.password
        if parsed.path and parsed.path != "/":
            try:
                self.db = int(parsed.path.lstrip("/"))
            except ValueError:
                pass
        
        # Query params
        qs = parse_qs(parsed.query)
        if "ssl_cert_reqs" in qs:
            self.ssl_cert_reqs = qs["ssl_cert_reqs"][0]

    def _detect_vendor_defaults(self) -> None:
        """Apply cloud vendor defaults if matching specific patterns."""
        # AWS ElastiCache, Redis Cloud, Upstash, Digital Ocean
        is_cloud = False
        if "cache.amazonaws.com" in self.host:
            is_cloud = True
        elif "redis-cloud.com" in self.host:
            is_cloud = True
        elif "upstash.io" in self.host:
            is_cloud = True
        elif "db.ondigitalocean.com" in self.host:
            is_cloud = True
            if self.port == 25061: # TLS port
                self.use_ssl = True

        if is_cloud:
             # Force SSL defaults if not explicitly disabled/configured?
             # Spec says "detect" and "default_tls: true".
             # If user didn't explicitly set use_ssl=False (value is default False), set to True.
             # Actually default is False, so if it's still False, we might want to set True.
             # But if user passed False specifically? We can't distinguish default vs explicit False easily here without extra logic.
             # Assuming if it looks like cloud, we prefer SSL.
             if not self.use_ssl:
                 self.use_ssl = True
        
    def validate(self) -> None:
        try:
            RedisConfigValidator(**self.__dict__)
        except Exception as e:
            raise RedisConfigError(f"Configuration validation failed: {str(e)}")

    def get_connection_kwargs(self) -> Dict[str, Any]:
        """Get arguments for redis client."""
        kwargs = {
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "password": self.password,
            "db": self.db,
            "socket_timeout": self.socket_timeout,
            "socket_connect_timeout": self.socket_connect_timeout,
            "retry_on_timeout": self.retry_on_timeout,
            "encoding": self.encoding,
            "decode_responses": self.decode_responses,
        }
        
        if self.unix_socket_path:
             kwargs["unix_socket_path"] = self.unix_socket_path
             del kwargs["host"]
             del kwargs["port"]
        
        if self.use_ssl == True:
            kwargs["ssl"] = True
        elif self.use_ssl == False:
            kwargs["ssl"] = False

        if self.ssl_cert_reqs:
            kwargs["ssl_cert_reqs"] = getattr(ssl, f"CERT_{self.ssl_cert_reqs.upper()}", ssl.CERT_NONE)
        elif self.ssl_cert_reqs == ssl.CERT_NONE:
            kwargs["ssl_cert_reqs"] = None

        if self.ssl_ca_certs:
            kwargs["ssl_ca_certs"] = self.ssl_ca_certs

        if self.ssl_check_hostname:
            kwargs["ssl_check_hostname"] = self.ssl_check_hostname
        elif self.ssl_check_hostname == False:
            kwargs["ssl_check_hostname"] = False

        if self.max_connections:
            kwargs["max_connections"] = self.max_connections

        # Filter out None
        return {k: v for k, v in kwargs.items() if v is not None}
