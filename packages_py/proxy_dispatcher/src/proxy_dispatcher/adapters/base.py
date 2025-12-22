"""
Abstract base adapter for HTTP libraries.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from ..models import DispatcherResult, ProxyConfig

class BaseAdapter(ABC):
    """Abstract interface for HTTP library adapters."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the adapter (e.g., 'httpx', 'requests')."""
        pass

    @abstractmethod
    def supports_sync(self) -> bool:
        """Whether the adapter supports synchronous clients."""
        pass

    @abstractmethod
    def supports_async(self) -> bool:
        """Whether the adapter supports asynchronous clients."""
        pass

    @abstractmethod
    def create_sync_client(self, config: ProxyConfig) -> DispatcherResult:
        """Create a configured synchronous client."""
        pass

    @abstractmethod
    def create_async_client(self, config: ProxyConfig) -> DispatcherResult:
        """Create a configured asynchronous client."""
        pass
    
    @abstractmethod
    def get_proxy_dict(self, config: ProxyConfig) -> Dict[str, Any]:
        """Get request kwargs for the client."""
        pass
