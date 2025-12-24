"""
High-level FetchClient implementation.
"""
from typing import Any, AsyncGenerator, Dict, Optional, Union

from .config import ClientConfig, AuthConfig
from .core.base_client import BaseClient
from .core.request import RequestBuilder
from .types import FetchResponse, RequestOptions, StreamOptions, SSEEvent

class FetchClient(BaseClient):
    """
    High-level HTTP client with convenience methods.
    """

    @classmethod
    def create(cls, config: ClientConfig) -> "FetchClient":
        """Factory method to create a client."""
        return cls(config)

    async def get(
        self, 
        url: str, 
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None
    ) -> FetchResponse:
        """Execute GET request."""
        opts = (
            RequestBuilder(url, "GET")
            .params(params or {})
            .headers(headers or {})
        )
        if timeout is not None:
            opts.timeout(timeout)
        return await self.request(opts.build())

    async def post(
        self, 
        url: str, 
        data: Any = None,
        json: Any = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None
    ) -> FetchResponse:
        """Execute POST request."""
        opts = (
            RequestBuilder(url, "POST")
            .params(params or {})
            .headers(headers or {})
        )
        if json is not None:
            opts.json(json)
        if data is not None:
            opts.data(data)
        if timeout is not None:
            opts.timeout(timeout)
        return await self.request(opts.build())

    async def put(
        self, 
        url: str, 
        data: Any = None,
        json: Any = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None
    ) -> FetchResponse:
        """Execute PUT request."""
        opts = (
            RequestBuilder(url, "PUT")
            .params(params or {})
            .headers(headers or {})
        )
        if json is not None:
            opts.json(json)
        if data is not None:
            opts.data(data)
        if timeout is not None:
            opts.timeout(timeout)
        return await self.request(opts.build())

    async def patch(
        self, 
        url: str, 
        data: Any = None,
        json: Any = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None
    ) -> FetchResponse:
        """Execute PATCH request."""
        opts = (
            RequestBuilder(url, "PATCH")
            .params(params or {})
            .headers(headers or {})
        )
        if json is not None:
            opts.json(json)
        if data is not None:
            opts.data(data)
        if timeout is not None:
            opts.timeout(timeout)
        return await self.request(opts.build())

    async def delete(
        self, 
        url: str, 
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None
    ) -> FetchResponse:
        """Execute DELETE request."""
        opts = (
            RequestBuilder(url, "DELETE")
            .params(params or {})
            .headers(headers or {})
        )
        if timeout is not None:
            opts.timeout(timeout)
        return await self.request(opts.build())

    # Streaming support (Placeholder for detailed implementation if needed, 
    # but basic generator structure can be here or in BaseClient. 
    # For now, relying on BaseClient request)
    # Note: BaseClient.request currently returns FetchResponse with data loaded.
    # To support streaming, we might need a dedicated stream method in BaseClient or flag.
    
    async def stream(
        self,
        url: str,
        method: str = "GET",
        json: Any = None,
        data: Any = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None
    ) -> AsyncGenerator[SSEEvent, None]:
        """
        Stream Server-Sent Events (SSE).
        NOTE: This requires BaseClient to support scanning/yielding logic.
        Since BaseClient uses httpx.request (not stream), we need to check if 
        we expose client.stream from httpx.
        """
        # Ensure client is connected
        if not self._client:
            await self.connect()
            
        assert self._client is not None
        
        # Build request manually or via builder
        # We need raw stream
        headers_dict = headers or {}
        headers_dict["Accept"] = "text/event-stream"
        
        # Auth injection ( reusing logic from BaseClient? )
        # Ideally BaseClient should expose a 'build_request' or 'prepare_request' method 
        # so we can reuse auth logic, then call client.stream()
        
        # For this phase, if BaseClient doesn't expose it, we duplicate auth logic 
        # OR refactor BaseClient. Ideally refactor.
        # But BaseClient._auth_handler is available.
        # Let's duplicate auth logic here for simplicity unless complex.
        
        full_url = f"{self._config.base_url}/{url}".rstrip("/")
        
        if self._auth_handler:
            context = {
                "method": method,
                "url": full_url,
                "headers": headers_dict,
                "body": json if json is not None else data
            }
            auth_headers = self._auth_handler.get_header(context)
            if auth_headers:
                headers_dict.update(auth_headers)

        async with self._client.stream(
            method=method,
            url=url, # httpx uses base_url so relative is fine
            headers=headers_dict,
            params=params,
            json=json,
            content=data,
            timeout=timeout or self._config.timeout.read
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    yield SSEEvent(data=line[6:])
                # Basic SSE parsing, can be improved.
