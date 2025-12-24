"""
Core HTTP client implementation based on httpx.
"""
import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, Optional, Union

import httpx

from ..config import ClientConfig, resolve_config, ResolvedConfig
from ..auth.auth_handler import create_auth_handler, AuthHandler
from ..types import FetchResponse, RequestContext, RequestOptions

logger = logging.getLogger(__name__)

# Constants
LOG_PREFIX = "[FetchClient]"

def _format_body(body: Any) -> str:
    """
    Format body for logging safeguards against binary data.
    """
    if body is None:
        return "<empty>"
    if isinstance(body, (bytes, bytearray)):
        return f"<binary data: {len(body)} bytes>"
    if isinstance(body, str):
        try:
            # Try to pretty print if it looks like JSON
            if body.strip().startswith(("{", "[")):
                 return json.dumps(json.loads(body), indent=2)
        except json.JSONDecodeError:
            pass
        # Truncate long strings
        if len(body) > 5000:
             return body[:5000] + "... (truncated)"
        return body
    if isinstance(body, dict):
        return json.dumps(body, indent=2)
    return str(body)

class BaseClient:
    """
    Base HTTP client wrapping httpx.AsyncClient.
    """
    def __init__(self, config: ClientConfig):
        self._config_raw = config
        self._config: ResolvedConfig = resolve_config(config)
        self._client: Optional[httpx.AsyncClient] = config.httpx_client
        self._auth_handler: Optional[AuthHandler] = None
        
        if self._config.auth:
            self._auth_handler = create_auth_handler(self._config.auth)

        # Flag to track if we own the client (created it)
        self._own_client = self._client is None

    async def connect(self) -> None:
        """Initialize the client if needed."""
        if self._client:
            return

        # Create httpx client
        timeout = httpx.Timeout(
            connect=self._config.timeout.connect,
            read=self._config.timeout.read,
            write=self._config.timeout.write,
            pool=self._config.timeout.pool
        )
        
        self._client = httpx.AsyncClient(
            base_url=self._config.base_url,
            timeout=timeout,
            headers=self._config.headers,
            # Force HTTP/1.1 for broad compatibility unless specified otherwise contextually
            # But httpx defaults are usually fine.
            follow_redirects=True, 
        )
    
    async def close(self) -> None:
        """Close the client if we own it."""
        if self._own_client and self._client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "BaseClient":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    async def request(self, options: RequestOptions) -> FetchResponse:
        """Execute a request."""
        if not self._client:
            await self.connect()
            
        assert self._client is not None
        
        # Prepare URL
        url = options.get("url", "")
        method = options.get("method", "GET")
        
        # Prepare Headers
        headers = options.get("headers", {}).copy()
        
        # Add content type if JSON is present and header missing
        if "json" in options and "Content-Type" not in headers:
            headers["Content-Type"] = "application/json"

        # Prepare Body
        data = options.get("data")
        json_body = options.get("json")
        
        # Resolve Auth
        if self._auth_handler:
            context: RequestContext = {
                "method": method,
                "url": f"{self._config.base_url}/{url}".rstrip("/"), # approx full URL
                "headers": headers,
                "body": json_body if json_body is not None else data
            }
            auth_headers = self._auth_handler.get_header(context)
            if auth_headers:
                headers.update(auth_headers)

        # Logging
        logger.debug(f"{LOG_PREFIX} Request: {method} {url}")
        
        try:
            response = await self._client.request(
                method=method,
                url=url,
                headers=headers,
                params=options.get("params"),
                content=data,
                json=json_body,
            )
            
            # Response handling
            res_data = None
            try:
                res_data = response.json()
            except json.JSONDecodeError:
                res_data = response.text
                
            return FetchResponse(
                status=response.status_code,
                status_text=response.reason_phrase,
                headers=dict(response.headers),
                url=str(response.url),
                data=res_data,
                ok=response.is_success
            )
            
        except httpx.RequestError as e:
            logger.error(f"{LOG_PREFIX} Request failed: {e}")
            raise e

