"""
Tests for BaseClient.
"""
import httpx
import pytest
import respx
from fetch_client.config import ClientConfig, AuthConfig
from fetch_client.core.base_client import BaseClient, _format_body

@pytest.mark.asyncio
async def test_base_client_lifecycle():
    config = ClientConfig(base_url="https://example.com")
    async with BaseClient(config) as client:
        assert client._client is not None
        # Should be open
        assert not client._client.is_closed
    
    # Should be closed after exit
    assert client._client is None  # Reference cleared

@pytest.mark.asyncio
async def test_base_client_request_simple():
    config = ClientConfig(base_url="https://example.com")
    async with BaseClient(config) as client:
        with respx.mock(base_url="https://example.com") as mock:
            mock.get("/test").respond(200, json={"foo": "bar"})
            
            response = await client.request({"method": "GET", "url": "/test"})
            
            assert response.status == 200
            assert response.data == {"foo": "bar"}
            assert response.ok is True

@pytest.mark.asyncio
async def test_base_client_auth_injection():
    config = ClientConfig(
        base_url="https://example.com",
        auth=AuthConfig(type="x-api-key", raw_api_key="secret")
    )
    async with BaseClient(config) as client:
        with respx.mock(base_url="https://example.com") as mock:
            route = mock.get("/test").respond(200)
            
            await client.request({"method": "GET", "url": "/test"})
            
            # Verify header was sent
            assert route.calls.last.request.headers["x-api-key"] == "secret"

def test_format_body_safety():
    # String
    assert _format_body("hello") == "hello"
    
    # JSON String
    assert _format_body('{"a": 1}') == '{\n  "a": 1\n}'
    
    # Binary
    assert _format_body(b"1234") == "<binary data: 4 bytes>"
    
    # Truncation
    long_str = "a" * 6000
    formatted = _format_body(long_str)
    assert len(formatted) < 6000
    assert "... (truncated)" in formatted
