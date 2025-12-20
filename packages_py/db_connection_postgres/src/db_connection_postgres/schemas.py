from typing import Optional, Literal
from pydantic import BaseModel, Field

class DatabaseConfigValidator(BaseModel):
    """Validator for database configuration parameters."""
    host: str = Field(min_length=1)
    port: int = Field(ge=1, le=65535)
    user: str = Field(min_length=1)
    password: Optional[str] = None
    database: str = Field(min_length=1)
    ssl_mode: Literal["disable", "allow", "prefer", "require", "verify-ca", "verify-full"] = "prefer"
    pool_size: int = Field(default=5, ge=1)
    max_overflow: int = Field(default=10, ge=0)
    pool_timeout: int = Field(default=30, ge=0)
    pool_recycle: int = Field(default=3600, ge=0)
    echo: bool = False
