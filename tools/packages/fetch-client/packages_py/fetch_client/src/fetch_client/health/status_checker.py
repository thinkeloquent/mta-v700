"""
Fetch Status Checker Implementation.
"""
import time
from typing import Optional, Any, Dict
import httpx

from fetch_client.client import FetchClient
from fetch_client.config import AuthConfig as FetchAuthConfig, ClientConfig

from .models import FetchStatus, FetchStatusResult

class FetchStatusChecker:
    """Check fetch connectivity to a provider using runtime config."""

    # Default health endpoints for provider types
    DEFAULT_ENDPOINTS = {
        "gemini_openai": "/models",
        "openai": "/models",
        "anthropic": "/models",
        "github": "/user",
        "default": "/",
    }

    def __init__(
        self,
        provider_name: str,
        runtime_config: Any,  # ComputeAllResult
        timeout_seconds: float = 10.0,
        endpoint_override: Optional[str] = None,
    ):
        self.provider_name = provider_name
        self.runtime_config = runtime_config
        self.timeout_seconds = timeout_seconds
        self.endpoint_override = endpoint_override

    async def check(self) -> FetchStatusResult:
        """Execute health check and return result."""
        from datetime import datetime, timezone

        timestamp = datetime.now(timezone.utc).isoformat()
        start_time = time.perf_counter()

        # Validate config
        if not self.runtime_config.config.get("base_url"):
            return self._config_error("base_url is required", timestamp)

        health_endpoint = self._resolve_health_endpoint()
        base_url = self.runtime_config.config.get("base_url")
        # Ensure clean url construction
        full_url = f"{base_url.rstrip('/')}/{health_endpoint.lstrip('/')}"

        request_info = {
            "method": "GET",
            "url": full_url,
            "timeout_seconds": self.timeout_seconds,
        }

        config_used = self._build_config_used(health_endpoint)

        client = None
        try:
            client = self._create_client()
            response = await client.get(
                health_endpoint,
                params=None # Could allow params override if needed
            )
            latency_ms = (time.perf_counter() - start_time) * 1000

            return FetchStatusResult(
                provider_name=self.provider_name,
                status=self._status_from_code(response.status),
                latency_ms=round(latency_ms, 2),
                timestamp=timestamp,
                request=request_info,
                response={
                    "status_code": response.status,
                    "status_text": response.status_text,
                    "content_type": response.headers.get("content-type"),
                    "body_preview": self._truncate(str(response.data)),
                },
                config_used=config_used,
            )

        except httpx.TimeoutException as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return FetchStatusResult(
                provider_name=self.provider_name,
                status=FetchStatus.TIMEOUT,
                latency_ms=round(latency_ms, 2),
                timestamp=timestamp,
                request=request_info,
                config_used=config_used,
                error={"type": "TimeoutException", "message": str(e)},
            )

        except httpx.ConnectError as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return FetchStatusResult(
                provider_name=self.provider_name,
                status=FetchStatus.CONNECTION_ERROR,
                latency_ms=round(latency_ms, 2),
                timestamp=timestamp,
                request=request_info,
                config_used=config_used,
                error={"type": "ConnectError", "message": str(e)},
            )

        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return FetchStatusResult(
                provider_name=self.provider_name,
                status=FetchStatus.ERROR,
                latency_ms=round(latency_ms, 2),
                timestamp=timestamp,
                request=request_info,
                config_used=config_used,
                error={
                    "type": type(e).__name__,
                    "message": str(e),
                },
            )
        finally:
            if client:
                await client.close()

    def _resolve_health_endpoint(self) -> str:
        """Resolve the health endpoint to use."""
        if self.endpoint_override:
            return self.endpoint_override
        if self.runtime_config.config.get("health_endpoint"):
            return self.runtime_config.config["health_endpoint"]
        return self.DEFAULT_ENDPOINTS.get(
            self.provider_name,
            self.DEFAULT_ENDPOINTS["default"]
        )

    def _create_client(self) -> FetchClient:
        """Create fetch client from runtime config."""
        
        auth_config = None
        if self.runtime_config.auth_config:
            auth_config = self._convert_auth_config(self.runtime_config.auth_config)

        # Build ClientConfig
        config = ClientConfig(
            base_url=self.runtime_config.config["base_url"],
            auth=auth_config,
            headers=self.runtime_config.config.get("headers", {}),
            timeout=self.timeout_seconds,
        )
        return FetchClient.create(config)

    def _convert_auth_config(self, auth: Any) -> FetchAuthConfig:
        """Convert yaml_config AuthConfig to fetch_client AuthConfig."""
        # Note: 'auth' here is config_loader.AuthConfig or similar, containing resolved secrets.
        # We handle Pydantic models or plain objects.
        
        type_val = auth.type.value if hasattr(auth.type, 'value') else auth.type
        
        return FetchAuthConfig(
            type=type_val,
            raw_api_key=auth.token,
            username=auth.username,
            password=auth.password,
            email=auth.email,
            header_name=auth.header_name,
        )

    def _build_config_used(self, health_endpoint: str) -> Dict[str, Any]:
        """Build safe config summary."""
        auth = self.runtime_config.auth_config
        
        auth_type_str = None
        if auth:
            auth_type_str = auth.type.value if hasattr(auth.type, 'value') else str(auth.type)

        return {
            "base_url": self.runtime_config.config.get("base_url"),
            "health_endpoint": health_endpoint,
            "auth_type": auth_type_str,
            "auth_resolved": bool(auth and auth.token),
            "is_placeholder": auth.resolution.is_placeholder if auth and auth.resolution else None,
            "proxy_url": self.runtime_config.proxy_config.proxy_url if self.runtime_config.proxy_config else None,
            "headers_count": len(self.runtime_config.config.get("headers", {})),
        }

    def _status_from_code(self, status_code: int) -> FetchStatus:
        """Map HTTP status code to FetchStatus."""
        if 200 <= status_code < 300:
            return FetchStatus.CONNECTED
        elif status_code in (401, 403):
            return FetchStatus.UNAUTHORIZED
        elif 400 <= status_code < 500:
            return FetchStatus.CLIENT_ERROR
        elif status_code >= 500:
            return FetchStatus.SERVER_ERROR
        return FetchStatus.ERROR

    def _config_error(self, message: str, timestamp: str) -> FetchStatusResult:
        """Create config error result."""
        return FetchStatusResult(
            provider_name=self.provider_name,
            status=FetchStatus.CONFIG_ERROR,
            latency_ms=0,
            timestamp=timestamp,
            error={"type": "ConfigError", "message": message},
        )

    @staticmethod
    def _truncate(text: str, max_len: int = 500) -> str:
        """Truncate text for preview."""
        if len(text) <= max_len:
            return text
        return text[:max_len] + "... (truncated)"
