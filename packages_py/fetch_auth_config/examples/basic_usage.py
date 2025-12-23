"""
Basic usage examples for fetch_auth_config package.
"""
import os
from fetch_auth_config import fetch_auth_config, AuthType

def example1_resolve_bearer():
    print("\n--- Example 1: Resolve Bearer Token ---")
    
    # Simulate config from app.yaml
    provider_config = {
        "api_auth_type": "bearer",
        "env_api_key": "MY_API_TOKEN",
        "fallbacks_from_env": {
            "api_key": "FALLBACK_TOKEN"
        }
    }
    
    # 1. No Env Var set -> MissingCredentialError (if strict) or None handling
    # Here, we set the env var to show success
    os.environ["MY_API_TOKEN"] = "sk-12345-production"
    
    try:
        config = fetch_auth_config("my-provider", provider_config)
        print(f"Resolved Config: {config}")
        print(f"Token: {config.token}")
        print(f"Resolution Source: {config.resolution.resolved_from}")
    finally:
        del os.environ["MY_API_TOKEN"]

def example2_resolve_basic_auth():
    print("\n--- Example 2: Resolve Basic Auth ---")
    
    provider_config = {
        "api_auth_type": "basic",
        "env_username": "API_USER",
        "env_password": "API_PASSWORD"
    }
    
    os.environ["API_USER"] = "admin"
    os.environ["API_PASSWORD"] = "secret123"
    
    try:
        config = fetch_auth_config("basic-provider", provider_config)
        print(f"User: {config.username}")
        print(f"Pass: {config.password}") # Warning: sensitive
    finally:
        del os.environ["API_USER"]
        del os.environ["API_PASSWORD"]

def example3_custom_header():
    print("\n--- Example 3: Custom Header ---")
    
    provider_config = {
        "api_auth_type": "custom_header",
        "api_auth_header_name": "X-Custom-Auth",
        "env_api_key": "CUSTOM_KEY"
    }
    
    os.environ["CUSTOM_KEY"] = "custom-value-abc"
    
    try:
        config = fetch_auth_config("custom-svc", provider_config)
        print(f"Header: {config.header_name}: {config.token}")
    finally:
        del os.environ["CUSTOM_KEY"]

if __name__ == "__main__":
    example1_resolve_bearer()
    example2_resolve_basic_auth()
    example3_custom_header()
