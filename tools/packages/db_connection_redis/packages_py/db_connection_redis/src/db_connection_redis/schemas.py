from typing import Optional, Literal
from pydantic import BaseModel, Field

class RedisConfigValidator(BaseModel):
    """Validator for Redis configuration parameters."""
    host: str = Field(min_length=1)
    port: int = Field(ge=1, le=65535)
    username: Optional[str] = None
    password: Optional[str] = None
    db: int = Field(default=0, ge=0)
    unix_socket_path: Optional[str] = None
    use_ssl: bool = False
    ssl_cert_reqs: Literal["none", "optional", "required"] = "none"
    ssl_ca_certs: Optional[str] = None
    ssl_check_hostname: bool = False
    socket_timeout: float = Field(default=5.0, gt=0)
    socket_connect_timeout: float = Field(default=5.0, gt=0)
    retry_on_timeout: bool = False
    max_connections: Optional[int] = Field(default=None, gt=0)
    health_check_interval: float = Field(default=0, ge=0)
