
from typing import Any, Optional

from ..health.models import FetchStatus, FetchStatusResult


class FetchStatusChecker:
    """Check fetch connectivity to a provider using runtime config."""

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
        # Defer import to avoid circular dependency
        from ..provider.provider_client import ProviderClient

        # Wrap instantiation in try/except because validation happens in constructor
        try:
            provider = ProviderClient(
                self.provider_name,
                self.runtime_config,
                options=None, # will use defaults or I should construct it
            )
            # Re-set options to match passed args (constructor defaults might differ?)
            # ProviderClient options: timeout_seconds=10.0.
            # We should pass them.
            provider.options.timeout_seconds = self.timeout_seconds
            provider.options.endpoint_override = self.endpoint_override

            try:
                return await provider.check_health()
            finally:
                await provider.close()

        except Exception as e:
            # Maintain backward compatibility
            from datetime import datetime, timezone
            timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            
            # Dummy empty objects for response
            empty_req = {"method": "UNKNOWN", "url": "UNKNOWN", "timeout_seconds": 0}
            empty_config = {
                "base_url": getattr(getattr(self.runtime_config, "config", None) or {}, "base_url", ""),
                "health_endpoint": "UNKNOWN",
                "method": "UNKNOWN",
                "timeout_seconds": 0,
                "auth_type": None,
                "auth_resolved": False,
                "auth_header_present": False,
                "is_placeholder": None,
                "proxy_url": None,
                "proxy_resolved": False,
                "headers_count": 0
            }
            empty_opts = {
                "method": "UNKNOWN",
                "url": "UNKNOWN",
                "timeout_seconds": 0,
                "headers": {},
                "headers_count": 0,
                "follow_redirects": False,
                "proxy": None,
                "verify_ssl": False
            }

            return FetchStatusResult(
                provider_name=self.provider_name,
                status=FetchStatus.CONFIG_ERROR,
                latency_ms=0,
                timestamp=timestamp,
                request=empty_req,
                config_used=empty_config,
                fetch_option_used=empty_opts,
                error={"type": "ConfigError", "message": str(e)},
            )
