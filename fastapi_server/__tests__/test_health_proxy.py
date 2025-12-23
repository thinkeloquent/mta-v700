
import os
import sys
import pytest
from fastapi.testclient import TestClient

# Define clean paths
project_root = "/Users/Shared/autoload/mta-v700"
pkg_py_path = os.path.join(project_root, "packages_py", "app_yaml_config", "src")

# Add to sys.path
sys.path.insert(0, pkg_py_path)
sys.path.insert(0, project_root)

# Mock environment
if not os.getenv("APP_ENV"):
    os.environ["APP_ENV"] = "dev"
os.environ["FIGMA_PROXY_URL"] = "http://figma-proxy:8080"

from fastapi import FastAPI
from fastapi_server.app.routes.healthz import app_yaml_config
import fastapi_server.app.load_app_config # Initialize config

def test_proxy_route():
    app = FastAPI()
    app.include_router(app_yaml_config.router)
    client = TestClient(app)

    # 1. Test Disabled Proxy (gemini_openai)
    print("Testing /provider/gemini_openai/proxy (Disabled)...")
    response = client.get("/healthz/admin/app-yaml-config/provider/gemini_openai/proxy")
    
    if response.status_code == 200:
        data = response.json()
        print(f"SUCCESS: Source={data['resolution']['source']}, Proxy={data['proxy_url']}")
        assert data['proxy_url'] is None
        assert data['resolution']['source'] == 'disabled'
    else:
        pytest.fail(f"FAILED: Status {response.status_code}, Body: {response.text}")

    # 2. Test Env Overwrite (figma)
    print("Testing /provider/figma/proxy (Env Overwrite)...")
    response = client.get("/healthz/admin/app-yaml-config/provider/figma/proxy")
    
    if response.status_code == 200:
        data = response.json()
        print(f"SUCCESS: Source={data['resolution']['source']}, Proxy={data['proxy_url']}")
        assert data['resolution']['source'] == 'env_overwrite'
        assert data['proxy_url'] == 'http://figma-proxy:8080'
    else:
        pytest.fail(f"FAILED: Status {response.status_code}, Body: {response.text}")

if __name__ == "__main__":
    try:
        test_proxy_route()
        print("ALL TESTS PASSED")
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
