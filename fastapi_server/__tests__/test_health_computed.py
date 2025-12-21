
import os
import sys
import asyncio

# Define clean paths
project_root = "/Users/Shared/autoload/mta-v700"
pkg_py_path = os.path.join(project_root, "packages_py", "app_yaml_config", "src")

# Add to sys.path
sys.path.insert(0, pkg_py_path)
sys.path.insert(0, project_root)

# Mock environment
if not os.getenv("APP_ENV"):
    os.environ["APP_ENV"] = "dev"

try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from fastapi_server.app.load_app_config import AppYamlConfig
    from fastapi_server.app.routes.healthz import app_yaml_config
    
    # Initialize config
    config = AppYamlConfig.get_instance()
    
    # Setup app and router
    app = FastAPI()
    app.include_router(app_yaml_config.router)
    
    client = TestClient(app)
    
    # Test valid key (allowed)
    print("Testing /healthz/admin/app-yaml-config/compute/proxy_url (Allowed)...")
    response = client.get("/healthz/admin/app-yaml-config/compute/proxy_url")
    if response.status_code != 200:
        print(f"FAILED: Status {response.status_code}, Body: {response.text}")
        sys.exit(1)
    print(f"SUCCESS: Got proxy_url = {response.json()['value']}")
    
    # Test forbidden key
    print("Testing /healthz/admin/app-yaml-config/compute/forbidden_key (Forbidden)...")
    response = client.get("/healthz/admin/app-yaml-config/compute/forbidden_key")
    if response.status_code != 403:
        print(f"FAILED: Expected 403, got {response.status_code}")
        sys.exit(1)
        
    print("SUCCESS: 403 handling verified.")
    
except Exception as e:
    import traceback
    traceback.print_exc()
    sys.exit(1)
