
import asyncio
import os
import sys
from unittest.mock import MagicMock

# Assuming running from package root, add src to path if not installed
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
# Add sibling packages for dependencies (dev/monorepo context)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../fetch_auth_config/src')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../fetch_auth_encoding/src')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../app_yaml_config/src')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../runtime_template_resolver/src')))

from yaml_config_factory import YamlConfigFactory, ComputeOptions, ContextComputeRegistry
from fetch_auth_config import AuthConfig, AuthType

async def main():
    print("Starting overwrite_from_context example (Python)...")

    # 1. Register a custom function for context resolution
    @ContextComputeRegistry.register_request('get_tenant_token')
    def get_tenant_token(context, request=None):
        tenant_id = request.get('query', {}).get('tenant_id', 'default-tenant')
        return f"token-for-{tenant_id}"

    # 2. Mock AppYamlConfig
    mock_app_config = MagicMock()
    mock_app_config.get_load_result.return_value.app_env = 'dev'
    mock_app_config.get_all.return_value = {}
    
    # Mock app_config._deep_merge because ProviderConfig uses it
    def mock_deep_merge(base, overlay):
        base.update(overlay)
        return base
    mock_app_config._deep_merge.side_effect = mock_deep_merge
    
    # Mock mocks for fetch/encode
    mock_fetch_auth = MagicMock()
    mock_fetch_auth.return_value = asyncio.Future()
    mock_fetch_auth.return_value.set_result(AuthConfig(type=AuthType.NONE, provider_name="test", resolution=None))
    
    mock_encode_auth = MagicMock()

    # Define the raw config with overwrite_from_context
    raw_config = {
        "base_url": "http://original.com",
        "api_key": "default-key",
        "headers": {
            "X-Custom": "original"
        },
        "overwrite_from_context": {
            "base_url": "{{env.API_URL_OVERRIDE}}",
            "api_key": "{{fn:get_tenant_token}}",
            "headers": {
                "X-Custom": "custom-{{request.query.region}}"
            }
        }
    }

    mock_app_config.get_nested.return_value = raw_config
    
    # Helper to return raw_config for get_provider logic
    def get_side_effect(key, default=None):
        if key == "providers":
            return {"test_provider": raw_config}
        return default
    mock_app_config.get.side_effect = get_side_effect

    # 4. Setup Environment and Request Context (BEFORE factory init)
    os.environ["API_URL_OVERRIDE"] = "http://overwritten-url.com"

    # 3. Setup Factory
    factory = YamlConfigFactory(mock_app_config, mock_fetch_auth, mock_encode_auth)
    
    request = {
        "query": {
            "tenant_id": "acme-corp",
            "region": "us-east"
        }
    }

    # 5. Compute Configuration
    result = await factory.compute('providers.test_provider', ComputeOptions(include_config=True, resolve_templates=True), request)

    # 6. Output Result
    print("\nComputed Configuration:")
    print(result.config)

    # Expected Output:
    # {
    #   'base_url': 'http://overwritten-url.com',
    #   'api_key': 'token-for-acme-corp',
    #   'headers': {'X-Custom': 'custom-us-east'}
    # }

if __name__ == "__main__":
    asyncio.run(main())
