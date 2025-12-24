"""
Tests for FetchClient.
"""
import pytest
import respx
from fetch_client.client import FetchClient
from fetch_client.config import ClientConfig

@pytest.mark.asyncio
async def test_fetch_client_factory():
    config = ClientConfig(base_url="https://example.com")
    client = FetchClient.create(config)
    assert isinstance(client, FetchClient)

@pytest.mark.asyncio
async def test_fetch_client_get():
    config = ClientConfig(base_url="https://example.com")
    async with FetchClient(config) as client:
        with respx.mock(base_url="https://example.com") as mock:
            mock.get("/test").respond(200, json={"a": 1})
            
            res = await client.get("/test", params={"q": "foo"})
            assert res.status == 200
            assert res.data == {"a": 1}

@pytest.mark.asyncio
async def test_fetch_client_post():
    config = ClientConfig(base_url="https://example.com")
    async with FetchClient(config) as client:
        with respx.mock(base_url="https://example.com") as mock:
            route = mock.post("/items").respond(201, json={"id": 123})
            
            res = await client.post("/items", json={"name": "item1"})
            assert res.status == 201
            assert res.data == {"id": 123}
            
            # Verify payload
            request = route.calls.last.request
            import json
            assert json.loads(request.read()) == {"name": "item1"}

@pytest.mark.asyncio
async def test_fetch_client_stream():
    # Basic stream test
    config = ClientConfig(base_url="https://example.com")
    async with FetchClient(config) as client:
        with respx.mock(base_url="https://example.com") as mock:
            # Simulate SSE stream
            mock.get("/stream").respond(200, content=b"data: hello\n\ndata: world\n\n")
            
            events = []
            async for event in client.stream("/stream"):
                events.append(event)
            
            assert len(events) == 2
            assert events[0].data == "hello"
            assert events[1].data == "world"
