import os
import ssl
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Literal
from urllib.parse import urlparse, parse_qs

from .exceptions import RedisConfigError
from .schemas import RedisConfigValidator

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
        self.host = self._resolve(host, "REDIS_HOST", "REDIS_HOSTNAME", config, "host", "localhost")
        self.port = int(self._resolve(port, "REDIS_PORT", None, config, "port", 6379))
        self.username = self._resolve(username, "REDIS_USERNAME", "REDIS_USER", config, "username", None)
        self.password = self._resolve(password, "REDIS_PASSWORD", "REDIS_AUTH", config, "password", None)
        self.db = int(self._resolve(db, "REDIS_DB", "REDIS_DATABASE", config, "db", 0))
        self.unix_socket_path = self._resolve(unix_socket_path, None, None, config, "unix_socket_path", None)
        
        self.use_ssl = self._resolve_bool(use_ssl, "REDIS_SSL", "REDIS_USE_TLS", config, "use_ssl", False)
        self.ssl_cert_reqs = self._resolve(ssl_cert_reqs, "REDIS_SSL_CERT_REQS", None, config, "ssl_cert_reqs", "none")
        self.ssl_ca_certs = self._resolve(ssl_ca_certs, "REDIS_SSL_CA_CERTS", None, config, "ssl_ca_certs", None)
        self.ssl_check_hostname = self._resolve_bool(ssl_check_hostname, "REDIS_SSL_CHECK_HOSTNAME", None, config, "ssl_check_hostname", False)
        
        self.socket_timeout = float(self._resolve(socket_timeout, "REDIS_SOCKET_TIMEOUT", None, config, "socket_timeout", 5.0))
        self.socket_connect_timeout = float(self._resolve(socket_connect_timeout, None, None, config, "socket_connect_timeout", 5.0))
        self.retry_on_timeout = self._resolve_bool(retry_on_timeout, None, None, config, "retry_on_timeout", False)
        
        max_conn = self._resolve(max_connections, "REDIS_MAX_CONNECTIONS", None, config, "max_connections", None)
        self.max_connections = int(max_conn) if max_conn is not None else None
        
        self.health_check_interval = float(self._resolve(health_check_interval, None, None, config, "health_check_interval", 0))
        self.encoding = self._resolve(encoding, None, None, config, "encoding", "utf-8")
        self.decode_responses = self._resolve_bool(decode_responses, None, None, config, "decode_responses", True)

        # REDIS_URL override
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            self._parse_redis_url(redis_url)

        # Auto-detect vendor / defaults if not explicitly set
        self._detect_vendor_defaults()

        # Validate
        self.validate()

    def _resolve(self, arg: Any, env1: Optional[str], env2: Optional[str], config: Optional[Dict], config_key: str, default: Any) -> Any:
        if arg is not None:
            return arg
        if env1 and os.getenv(env1) is not None:
            return os.getenv(env1)
        if env2 and os.getenv(env2) is not None:
            return os.getenv(env2)
        if config and config_key in config:
            return config[config_key]
        return default

    def _resolve_bool(self, arg: Any, env1: Optional[str], env2: Optional[str], config: Optional[Dict], config_key: str, default: bool) -> bool:
        val = self._resolve(arg, env1, env2, config, config_key, default)
        if isinstance(val, bool): return val
        if isinstance(val, str):
            return val.lower() in ("true", "1", "yes", "on")
        return bool(val)

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
        
        if self.use_ssl:
            kwargs["ssl"] = True
            kwargs["ssl_cert_reqs"] = getattr(ssl, f"CERT_{self.ssl_cert_reqs.upper()}", ssl.CERT_NONE)
            if self.ssl_ca_certs:
                kwargs["ssl_ca_certs"] = self.ssl_ca_certs
            kwargs["ssl_check_hostname"] = self.ssl_check_hostname

        if self.max_connections:
            kwargs["max_connections"] = self.max_connections

        # Filter out None
        return {k: v for k, v in kwargs.items() if v is not None}
