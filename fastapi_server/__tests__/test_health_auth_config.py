
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
os.environ["GEMINI_API_KEY"] = "mock_gemini_key"
os.environ["CONFLUENCE_API_TOKEN"] = "mock_confluence_token"
os.environ["CONFLUENCE_EMAIL"] = "mock@example.com"
os.environ["REDIS_HOST"] = "localhost"

from fastapi import FastAPI
from fastapi_server.app.routes.healthz import app_yaml_config
import fastapi_server.app.load_app_config # Initialize config

def test_auth_config_routes():
    app = FastAPI()
    app.include_router(app_yaml_config.router)
    client = TestClient(app)

    # 1. Test Provider (gemini_openai)
    print("Testing /healthz/admin/app-yaml-config/provider/gemini_openai/auth_config...")
    response = client.get("/healthz/admin/app-yaml-config/provider/gemini_openai/auth_config")
    
    if response.status_code == 200:
        data = response.json()
        print(f"SUCCESS: Provider Auth Type: {data.get('auth_type')}")
        assert "credentials" in data
    elif response.status_code == 404:
        print("SUCCESS: Provider not found (Access Allowed).")
    else:
        pytest.fail(f"FAILED: Status {response.status_code}, Body: {response.text}")

    # 2. Test Provider (confluence)
    print("Testing /healthz/admin/app-yaml-config/provider/confluence/auth_config...")
    response = client.get("/healthz/admin/app-yaml-config/provider/confluence/auth_config")
    if response.status_code != 200:
        pytest.fail(f"FAILED: Status {response.status_code}, Body: {response.text}")
    print(f"SUCCESS: Service Auth Type: {response.json().get('auth_type')}")


    # 4. Test Forbidden
    print("Testing /healthz/admin/app-yaml-config/provider/forbidden_provider/auth_config...")
    response = client.get("/healthz/admin/app-yaml-config/provider/forbidden_provider/auth_config")
    assert response.status_code == 403
    print("SUCCESS: 403 verified.")

if __name__ == "__main__":
    # If run directly
    try:
        test_auth_config_routes()
        print("ALL TESTS PASSED")
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
