
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Union
from urllib.parse import quote, urlparse

from httpx import ConnectError, TimeoutException

from ..client import FetchClient
from ..config import ClientConfig
from ..types import FetchResponse, RequestOptions
from ..health.models import FetchStatus, FetchStatusResult


@dataclass
class ProviderClientOptions:
    timeout_seconds: float = 10.0
    endpoint_override: Optional[str] = None


@dataclass
class ConfigUsedInfo:
    base_url: str
    health_endpoint: str
    method: str
    timeout_seconds: float
    auth_type: Optional[str]
    auth_resolved: bool
    auth_header_present: bool
    is_placeholder: Optional[bool]
    proxy_url: Optional[str]
    proxy_resolved: bool
    headers_count: int


@dataclass
class FetchOptionUsedInfo:
    method: str
    url: str
    timeout_seconds: float
    headers: Dict[str, str]
    headers_count: int
    follow_redirects: bool
    proxy: Optional[str]
    verify_ssl: bool


class ProviderClient:
    """
    Central HTTP client factory for provider-based requests.
    Wraps FetchClient with runtime configuration handling.
    """

    def __init__(
        self,
        provider_name: str,
        runtime_config: Any,  # ComputeAllResult
        options: Optional[ProviderClientOptions] = None,
    ):
        self.provider_name = provider_name
        self.runtime_config = runtime_config
        self.options = options or ProviderClientOptions()
        
        self._client: Optional[FetchClient] = None
        
        # Pre-compute merged headers
        config = getattr(self.runtime_config, "config", None) or {}
        if not config.get("base_url"):
            raise ValueError(f"base_url is required in provider config for '{self.provider_name}'")
            
        pre_computed_headers = getattr(self.runtime_config, "headers", None) or {}
        config_headers = config.get("headers") or {}
        self._merged_headers = {**config_headers, **pre_computed_headers}

    def get_client(self) -> FetchClient:
        """Get the underlying FetchClient for custom requests."""
        if not self._client:
            self._client = self._create_client()
        return self._client

    async def request(self, options: RequestOptions) -> FetchResponse:
        """Make a request using this provider's configuration."""
        client = self.get_client()
        return await client.request(options)

    async def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> FetchResponse:
        """Convenience GET request."""
        client = self.get_client()
        return await client.get(url, params=params, headers=headers, timeout=timeout)

    async def post(
        self,
        url: str,
        data: Any = None,
        json: Any = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> FetchResponse:
        """Convenience POST request."""
        client = self.get_client()
        return await client.post(url, data=data, json=json, params=params, headers=headers, timeout=timeout)

    # Note: put, patch, delete are also available on FetchClient and can be exposed if needed.

    async def check_health(
        self,
        endpoint_override: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> FetchStatusResult:
        """Execute health check against the provider."""
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        start_time = time.perf_counter()

        # 1. Resolve endpoint
        try:
             health_endpoint = self._resolve_health_endpoint(endpoint_override)
        except ValueError as e:
             return self._config_error(str(e), timestamp)

        config = getattr(self.runtime_config, "config", None) or {}
        base_url = config.get("base_url", "")
        full_url = f"{base_url.rstrip('/')}/{health_endpoint.lstrip('/')}"
        
        method = self._resolve_method()
        timeout_sec = timeout if timeout is not None else self.options.timeout_seconds

        request_info = {
            "method": method,
            "url": full_url,
            "timeout_seconds": timeout_sec,
        }

        config_used = self._build_config_used(health_endpoint, method)
        fetch_option_used = self.get_fetch_option_used(method, full_url)

        try:
            client = self.get_client()
            # Ensure connection
            await client.connect()
            
            # Note: FetchClient.request handles timeout if passed in RequestOptions/builder
            # Logic mimic from client.get() wrapper
            from ..core.request import RequestBuilder
            opts = RequestBuilder(health_endpoint, method)
            if timeout_sec is not None:
                opts.timeout(timeout_sec)
            
            response = await client.request(opts.build())

            latency_ms = (time.perf_counter() - start_time) * 1000

            # Read body safely
            body_preview = ""
            try:
                data = response.data
                if data:
                    if isinstance(data, str):
                        body_preview = self._truncate(data)
                    else:
                        import json as json_lib
                        body_preview = self._truncate(json_lib.dumps(data))
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
                config_used=config_used.__dict__, # Convert dataclass to dict
                fetch_option_used=fetch_option_used.__dict__,
            )

        except TimeoutException as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return FetchStatusResult(
                provider_name=self.provider_name,
                status=FetchStatus.TIMEOUT,
                latency_ms=round(latency_ms, 2),
                timestamp=timestamp,
                request=request_info,
                config_used=config_used.__dict__,
                fetch_option_used=fetch_option_used.__dict__,
                error={"type": "TimeoutException", "message": str(e)},
            )

        except ConnectError as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return FetchStatusResult(
                provider_name=self.provider_name,
                status=FetchStatus.CONNECTION_ERROR,
                latency_ms=round(latency_ms, 2),
                timestamp=timestamp,
                request=request_info,
                config_used=config_used.__dict__,
                fetch_option_used=fetch_option_used.__dict__,
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
                config_used=config_used.__dict__,
                fetch_option_used=fetch_option_used.__dict__,
                error={"type": type(e).__name__, "message": str(e)},
            )
            
    def get_config_used(self) -> ConfigUsedInfo:
        """Get configuration info for diagnostics."""
        try:
             health_endpoint = self._resolve_health_endpoint()
             method = self._resolve_method()
             return self._build_config_used(health_endpoint, method)
        except ValueError:
             return self._build_config_used("unknown", "GET")

    def get_fetch_option_used(
        self,
        method: Optional[str] = None,
        full_url: Optional[str] = None
    ) -> FetchOptionUsedInfo:
        """Get fetch options with masked sensitive values."""
        m = method or self._resolve_method()
        config = getattr(self.runtime_config, "config", None) or {}
        u = full_url or config.get("base_url")
        return self._build_fetch_option_used(m, u, self._merged_headers)

    async def close(self) -> None:
        """Close the client connection."""
        if self._client:
            await self._client.close()

    # =========================================================================
    # Private Helpers
    # =========================================================================

    def _resolve_health_endpoint(self, override: Optional[str] = None) -> str:
        endpoint_src = override or self.options.endpoint_override
        if endpoint_src:
            return self._resolve_placeholders(endpoint_src)
            
        config = getattr(self.runtime_config, "config", None) or {}
        health_conf = config.get("health_endpoint")
        
        if health_conf:
             endpoint: str
             if isinstance(health_conf, dict):
                  endpoint = health_conf.get("path") or health_conf.get("endpoint")
                  if not endpoint:
                       raise ValueError(f"health_endpoint object missing 'path' in provider config for '{self.provider_name}'")
             else:
                  endpoint = str(health_conf)
             return self._resolve_placeholders(endpoint)
             
        raise ValueError(f"health_endpoint is required in provider config for '{self.provider_name}'")

    def _resolve_placeholders(self, endpoint: str) -> str:
        auth_config = getattr(self.runtime_config, "auth_config", None)
        config = getattr(self.runtime_config, "config", None) or {}

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
        config = getattr(self.runtime_config, "config", None) or {}
        
        health_conf = config.get("health_endpoint")
        if isinstance(health_conf, dict):
            m = health_conf.get("method")
            if m:
                return str(m).upper()
                
        m = config.get("method")
        if m:
            return str(m).upper()
            
        return "GET"
        
    def _create_client(self) -> FetchClient:
        config = getattr(self.runtime_config, "config", None) or {}
        
        client_config = ClientConfig(
            base_url=config.get("base_url", ""),
            headers=self._merged_headers,
            timeout=self.options.timeout_seconds,
        )
        return FetchClient.create(client_config)

    def _build_config_used(self, health_endpoint: str, method: str) -> ConfigUsedInfo:
        config = getattr(self.runtime_config, "config", None) or {}
        auth_config = getattr(self.runtime_config, "auth_config", None)
        proxy_config = getattr(self.runtime_config, "proxy_config", None)
        
        auth_type = None
        if auth_config:
            auth_type_val = getattr(auth_config, "type", None)
            if hasattr(auth_type_val, "value"):
                auth_type = auth_type_val.value
            else:
                try:
                     auth_type = str(auth_type_val)
                except:
                     auth_type = None

        has_auth_header = bool(
            self._merged_headers.get("Authorization") or
            self._merged_headers.get("authorization")
        )
        
        return ConfigUsedInfo(
            base_url=config.get("base_url"),
            health_endpoint=health_endpoint,
            method=method,
            timeout_seconds=self.options.timeout_seconds,
            auth_type=auth_type,
            auth_resolved=bool(auth_config and getattr(auth_config, "token", None)),
            auth_header_present=has_auth_header,
            is_placeholder=getattr(getattr(auth_config, "resolution", None), "is_placeholder", None) if auth_config else None,
            proxy_url=getattr(proxy_config, "proxy_url", None) if proxy_config else None,
            proxy_resolved=bool(proxy_config and getattr(proxy_config, "proxy_url", None)),
            headers_count=len(self._merged_headers),
        )

    def _mask_header_value(self, key: str, value: str) -> str:
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
    ) -> FetchOptionUsedInfo:
        config = getattr(self.runtime_config, "config", None) or {}
        proxy_config = getattr(self.runtime_config, "proxy_config", None)
        
        masked_headers = {
             k: self._mask_header_value(k, str(v))
             for k, v in merged_headers.items()
        }
        
        proxy_url = None
        if proxy_config:
             raw = getattr(proxy_config, "proxy_url", None)
             if raw:
                  try:
                       parsed = urlparse(raw)
                       if parsed.password:
                            proxy_url = raw.replace(parsed.password, "****")
                       else:
                            proxy_url = raw
                  except:
                       proxy_url = raw
                       
        return FetchOptionUsedInfo(
             method=method,
             url=full_url,
             timeout_seconds=self.options.timeout_seconds,
             headers=masked_headers,
             headers_count=len(merged_headers),
             follow_redirects=config.get("follow_redirects", True),
             proxy=proxy_url,
             verify_ssl=config.get("verify_ssl", True)
        )

    def _status_from_code(self, status_code: int) -> FetchStatus:
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
         # Need placeholder objects for dataclass strictness
         dummy_config_used = self._build_config_used("ERROR", "ERROR")
         dummy_fetch_opts = self.get_fetch_option_used("ERROR", "ERROR")
         
         # Convert to dicts because FetchStatusResult expects dicts for these fields if not refactored yet?
         # Wait, FetchStatusResult definition in models.py uses Dict or objects?
         # models.py says: config_used: Dict[str, Any]
         
         return FetchStatusResult(
            provider_name=self.provider_name,
            status=FetchStatus.CONFIG_ERROR,
            latency_ms=0,
            timestamp=timestamp,
            request={"method": "UNKNOWN", "url": "UNKNOWN"},
            config_used=dummy_config_used.__dict__,
            fetch_option_used=dummy_fetch_opts.__dict__,
            error={"type": "ConfigError", "message": message},
        )
    
    def _truncate(self, text: str, max_len: int = 500) -> str:
        if len(text) <= max_len:
            return text
        return text[:max_len] + "... (truncated)"
