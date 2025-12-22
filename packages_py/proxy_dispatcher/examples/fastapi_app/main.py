"""
FastAPI example using proxy_dispatcher.
"""
import logging
from fastapi import FastAPI, Depends
from proxy_dispatcher import get_async_client, ProxyDispatcherFactory, FactoryConfig
from proxy_config import NetworkConfig
import httpx

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI()

# 1. Dependency Injection approach (Recommended)
# Create a global factory instance
# In a real app, you might load this from app.yaml via app-yaml-config
factory_config = FactoryConfig(
    default_environment="dev",
    proxy_urls={
        "dev": "http://dev-proxy:3128",
        "prod": "http://prod-proxy:3128"
    }
)
factory = ProxyDispatcherFactory(config=factory_config)

async def get_http_client():
    """Dependency that provides a configured async client."""
    # This will auto-detect environment (APP_ENV) or use default
    result = factory.get_proxy_dispatcher(async_client=True)
    async with result.client as client:
        yield client

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/proxy-test")
async def proxy_test(client: httpx.AsyncClient = Depends(get_http_client)):
    """Expected to use the proxy configured in the factory."""
    try:
        # Example request (would normally hit an external service)
        # For demo purposes we just show what would happen
        logger.info(f"Client headers: {client.headers}")
        return {
            "message": "Client created with proxy settings",
            "proxy_configured": True # We can't easily inspect the internal proxy mount in httpx public API
        }
    except Exception as e:
        return {"error": str(e)}

# 2. Simple Convenience Function approach (Quick scripts)
@app.get("/simple-proxy-test")
async def simple_proxy_test():
    """Uses the global default factory."""
    # This uses os.environ for configuration
    client = get_async_client()
    async with client as c:
        return {"message": "Created client from global factory"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
