
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
    
    # Test computed routes
    print("Testing /healthz/admin/app-yaml-config/compute/proxy_url (Allowed)...")
    response = client.get("/healthz/admin/app-yaml-config/compute/proxy_url")
    if response.status_code != 200:
        print(f"FAILED: Status {response.status_code}, Body: {response.text}")
        sys.exit(1)
    
    # Test provider routes
    print("Testing /healthz/admin/app-yaml-config/provider/gemini_openai (Allowed)...")
    # Note: gemini_openai might not exist in base/server.dev.yaml so it might return 404 if not configured,
    # but access control check happens first. If it's 404, it means access allowed but not found.
    # If 403, it means access denied.
    response = client.get("/healthz/admin/app-yaml-config/provider/gemini_openai")
    
    # If gemini_openai is configured in server.dev.yaml, checks should pass.
    # If not, we might get 404, which is acceptable for "route works, provider is missing".
    # BUT we want to verify 200 if possible.
    # Assuming gemini_openai IS in server.dev.yaml based on specs.
    
    if response.status_code == 200:
        print("SUCCESS: Retrieved provider config.")
    elif response.status_code == 404:
        print("SUCCESS: Provider not found (Access Allowed).")
    else:
        print(f"FAILED: Status {response.status_code}, Body: {response.text}")
        sys.exit(1)

    print("Testing /healthz/admin/app-yaml-config/provider/forbidden (Forbidden)...")
    response = client.get("/healthz/admin/app-yaml-config/provider/forbidden")
    if response.status_code != 403:
         print(f"FAILED: Expected 403, got {response.status_code}")
         sys.exit(1)
    print("SUCCESS: 403 handling verified for provider.")
    
    # Test list providers
    print("Testing /healthz/admin/app-yaml-config/providers...")
    response = client.get("/healthz/admin/app-yaml-config/providers")
    if response.status_code != 200:
        print(f"FAILED: Status {response.status_code}, Body: {response.text}")
        sys.exit(1)
    
    providers = response.json()
    print(f"SUCCESS: Got providers list: {providers}")
    if not isinstance(providers, list):
        print("FAILED: Response is not a list")
        sys.exit(1)

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
