"""
Fetch Status Checker Implementation.
"""
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from urllib.parse import quote

from httpx import TimeoutException, ConnectError

from ..client import FetchClient
from ..config import ClientConfig
from .models import FetchStatus, FetchStatusResult


class FetchStatusChecker:
    """Check fetch connectivity to a provider using runtime config."""

    def __init__(
        self,
        provider_name: str,
        runtime_config: Any,  # ComputeAllResult from YamlConfigFactory
        timeout_seconds: float = 10.0,
        endpoint_override: Optional[str] = None,
    ):
        self.provider_name = provider_name
        self.runtime_config = runtime_config
        self.timeout_seconds = timeout_seconds
        self.endpoint_override = endpoint_override

    async def check(self) -> FetchStatusResult:
        """Execute health check and return result."""
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        start_time = time.perf_counter()

        # Validate config
        config = getattr(self.runtime_config, "config", None) or {}
        if not config.get("base_url"):
            return self._config_error("base_url is required", timestamp)

        health_endpoint = self._resolve_health_endpoint()
        base_url = config.get("base_url", "")

        # Build full URL for display
        full_url = f"{base_url.rstrip('/')}/{health_endpoint.lstrip('/')}"

        method = self._resolve_method()
        request_info = {
            "method": method,
            "url": full_url,
            "timeout_seconds": self.timeout_seconds,
        }

        config_used = self._build_config_used(health_endpoint, method)

        # Build fetch_option_used before making request
        config = getattr(self.runtime_config, "config", None) or {}
        pre_computed_headers = getattr(self.runtime_config, "headers", None) or {}
        config_headers = config.get("headers") or {}
        merged_headers = {**config_headers, **pre_computed_headers}

        fetch_option_used = self._build_fetch_option_used(
            method=method,
            full_url=full_url,
            merged_headers=merged_headers,
        )

        client: Optional[FetchClient] = None

        try:
            client = self._create_client()
            await client.connect()
            response = await client.request(method, health_endpoint)

            latency_ms = (time.perf_counter() - start_time) * 1000

            # Read body safely
            body_preview = ""
            try:
                data = response.data
                if data:
                    if isinstance(data, str):
                        body_preview = self._truncate(data)
                    else:
                        import json
                        body_preview = self._truncate(json.dumps(data))
            except Exception:
                body_preview = "[Unable to read body]"

            return FetchStatusResult(
                provider_name=self.provider_name,
                status=self._status_from_code(response.status),
                latency_ms=round(latency_ms, 2),
                timestamp=timestamp,
                request=request_info,
                response={
                    "status_code": response.status,
                    "status_text": response.status_text or "",
                    "content_type": response.headers.get("content-type", ""),
                    "body_preview": body_preview,
                },
                config_used=config_used,
                fetch_option_used=fetch_option_used,
            )

        except TimeoutException as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return FetchStatusResult(
                provider_name=self.provider_name,
                status=FetchStatus.TIMEOUT,
                latency_ms=round(latency_ms, 2),
                timestamp=timestamp,
                request=request_info,
                config_used=config_used,
                error={
                    "type": "TimeoutException",
                    "message": str(e),
                },
            )

        except ConnectError as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return FetchStatusResult(
                provider_name=self.provider_name,
                status=FetchStatus.CONNECTION_ERROR,
                latency_ms=round(latency_ms, 2),
                timestamp=timestamp,
                request=request_info,
                config_used=config_used,
                error={
                    "type": "ConnectError",
                    "message": str(e),
                },
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
                fetch_option_used=fetch_option_used,
                error={
                    "type": type(e).__name__,
                    "message": str(e),
                },
            )

        finally:
            if client:
                try:
                    await client.close()
                except Exception:
                    pass

    def _resolve_health_endpoint(self) -> str:
        """Resolve the health check endpoint."""
        endpoint: str
        if self.endpoint_override:
            endpoint = self.endpoint_override
        elif self.runtime_config.config.get("health_endpoint"):
            health_conf = self.runtime_config.config["health_endpoint"]
            if isinstance(health_conf, dict):
                # If dict, expect 'path' or 'endpoint' key
                endpoint = health_conf.get("path") or health_conf.get("endpoint")
                if not endpoint:
                     raise ValueError(f"health_endpoint object missing 'path' in provider config for '{self.provider_name}'")
            else:
                endpoint = str(health_conf)
        else:
            raise ValueError(
                f"health_endpoint is required in provider config for '{self.provider_name}'"
            )

        # Replace placeholders
        return self._resolve_placeholders(endpoint)

    def _resolve_placeholders(self, endpoint: str) -> str:
        """Replace placeholders like :username with actual values."""
        auth_config = getattr(self.runtime_config, "auth_config", None)
        config = getattr(self.runtime_config, "config", None) or {}

        # Build replacement map
        replacements = {
            ":username": getattr(auth_config, "username", None) or config.get("username"),
            ":email": getattr(auth_config, "email", None) or config.get("email"),
            ":user": getattr(auth_config, "username", None) or config.get("username"),
        }

        result = endpoint
        for placeholder, value in replacements.items():
            if value and placeholder in result:
                result = result.replace(placeholder, quote(str(value), safe=""))

        return result

    def _resolve_method(self) -> str:
        """Resolve HTTP method from config, default to GET."""
        config = getattr(self.runtime_config, "config", None) or {}

        # Check health_endpoint config for method
        health_endpoint_config = config.get("health_endpoint")
        if isinstance(health_endpoint_config, dict):
            method = health_endpoint_config.get("method")
            if method:
                return str(method).upper()

        # Fallback to top-level method
        method = config.get("method")
        if method:
            return str(method).upper()

        return "GET"

    def _create_client(self) -> FetchClient:
        """Create FetchClient with pre-computed headers from YamlConfigFactory."""
        config = getattr(self.runtime_config, "config", None) or {}

        # Use pre-computed headers from YamlConfigFactory which includes properly
        # encoded Authorization header via encode_auth (handles basic, bearer, etc.)
        pre_computed_headers = getattr(self.runtime_config, "headers", None) or {}
        config_headers = config.get("headers") or {}

        # Merge: pre-computed auth headers take precedence
        merged_headers = {
            **config_headers,
            **pre_computed_headers,
        }

        client_config = ClientConfig(
            base_url=config.get("base_url", ""),
            # Do NOT pass auth config - we're using pre-computed headers instead
            headers=merged_headers,
            timeout=self.timeout_seconds,
        )

        return FetchClient.create(client_config)

    def _build_config_used(self, health_endpoint: str, method: str) -> Dict[str, Any]:
        """Build config_used info for response."""
        config = getattr(self.runtime_config, "config", None) or {}
        auth_config = getattr(self.runtime_config, "auth_config", None)
        proxy_config = getattr(self.runtime_config, "proxy_config", None)
        pre_computed_headers = getattr(self.runtime_config, "headers", None) or {}

        auth_type = None
        if auth_config:
            auth_type_val = getattr(auth_config, "type", None)
            if hasattr(auth_type_val, "value"):
                auth_type = auth_type_val.value
            else:
                auth_type = auth_type_val

        has_auth_header = bool(
            pre_computed_headers.get("Authorization") or
            pre_computed_headers.get("authorization")
        )

        return {
            "base_url": config.get("base_url"),
            "health_endpoint": health_endpoint,
            "method": method,
            "timeout_seconds": self.timeout_seconds,
            "auth_type": auth_type,
            "auth_resolved": bool(auth_config and getattr(auth_config, "token", None)),
            "auth_header_present": has_auth_header,
            "is_placeholder": getattr(
                getattr(auth_config, "resolution", None),
                "is_placeholder",
                None
            ) if auth_config else None,
            "proxy_url": getattr(proxy_config, "proxy_url", None) if proxy_config else None,
            "proxy_resolved": bool(proxy_config and getattr(proxy_config, "proxy_url", None)),
            "headers_count": len(pre_computed_headers),
        }

    def _status_from_code(self, status_code: int) -> FetchStatus:
        """Convert HTTP status code to FetchStatus."""
        if 200 <= status_code < 300:
            return FetchStatus.CONNECTED
        if status_code in (401, 403):
            return FetchStatus.UNAUTHORIZED
        if 400 <= status_code < 500:
            return FetchStatus.CLIENT_ERROR
        if status_code >= 500:
            return FetchStatus.SERVER_ERROR
        return FetchStatus.ERROR

    def _config_error(self, message: str, timestamp: str) -> FetchStatusResult:
        """Return a config error result."""
        return FetchStatusResult(
            provider_name=self.provider_name,
            status=FetchStatus.CONFIG_ERROR,
            latency_ms=0,
            timestamp=timestamp,
            error={"type": "ConfigError", "message": message},
        )

    def _truncate(self, text: str, max_len: int = 500) -> str:
        """Truncate text to max length."""
        if len(text) <= max_len:
            return text
        return text[:max_len] + "... (truncated)"

    def _mask_header_value(self, key: str, value: str) -> str:
        """Mask sensitive header values for security."""
        sensitive_keys = {"authorization", "x-api-key", "api-key", "token", "secret"}
        if key.lower() in sensitive_keys:
            if len(value) <= 20:
                return "****"
            return f"{value[:20]}..."
        return value

    def _build_fetch_option_used(
        self,
        method: str,
        full_url: str,
        merged_headers: Dict[str, str],
    ) -> Dict[str, Any]:
        """Build fetch_option_used info for response.

        Records the actual options passed to the HTTP client.
        """
        config = getattr(self.runtime_config, "config", None) or {}
        proxy_config = getattr(self.runtime_config, "proxy_config", None)

        # Mask sensitive headers
        masked_headers = {
            k: self._mask_header_value(k, str(v))
            for k, v in merged_headers.items()
        }

        # Get proxy URL and mask it
        proxy_url = None
        if proxy_config:
            raw_proxy = getattr(proxy_config, "proxy_url", None)
            if raw_proxy:
                # Mask credentials in proxy URL if present
                from urllib.parse import urlparse
                parsed = urlparse(raw_proxy)
                if parsed.password:
                    proxy_url = raw_proxy.replace(parsed.password, "****")
                else:
                    proxy_url = raw_proxy

        return {
            "method": method,
            "url": full_url,
            "timeout_seconds": self.timeout_seconds,
            "headers": masked_headers,
            "headers_count": len(merged_headers),
            "follow_redirects": config.get("follow_redirects", True),
            "proxy": proxy_url,
            "verify_ssl": config.get("verify_ssl", True),
        }
