from fastapi import APIRouter
from app_yaml_config import AppYamlConfig
from proxy_dispatcher import get_proxy_dispatcher, FactoryConfig, ProxyDispatcherFactory
from proxy_config import NetworkConfig

router = APIRouter()

@router.get("/healthz/fetch-proxy-dispatcher")
async def fetch_proxy_dispatcher():
    """
    Health check that verifies the proxy dispatcher configuration
    by resolving the proxy URL for the current environment as defined in app.yaml.
    """
    # 1. Get singleton config
    config = AppYamlConfig.get_instance()
    
    # 2. Get network config (raw dict access as per AppYamlConfig pattern)
    # The user specified global.network.proxy_urls[{{APP_ENV}}]
    # AppYamlConfig usually merges 'global' into the root or we access it via 'global' key
    # Let's inspect how access usually works. Based on valid config, 'global' is a top level key.
    
    global_config = config.get("global", {})
    network_config = global_config.get("network", {})
    
    # 3. Use ProxyDispatcher to resolve
    # We reconstruct the FactoryConfig/NetworkConfig from the raw yaml data
    # to test if proxy_dispatcher resolves it correctly.
    
    # Map raw config to FactoryConfig
    factory_config = FactoryConfig(
        default_environment=network_config.get("default_environment"),
        proxy_urls=network_config.get("proxy_urls"),
        agent_proxy=network_config.get("agent_proxy"),
        ca_bundle=network_config.get("ca_bundle"),
        cert=network_config.get("cert"),
        cert_verify=network_config.get("cert_verify")
    )
    
    # Create factory
    factory = ProxyDispatcherFactory(config=factory_config)
    
    # Get dispatcher result
    result = factory.get_proxy_dispatcher()
    
    return {
        "status": "ok",
        "resolved_proxy_url": result.config.proxy_url,
        "config_source": {
            "default_environment": factory_config.default_environment,
            "proxy_urls_keys": list(factory_config.proxy_urls.keys()) if factory_config.proxy_urls else [],
            "current_env_proxy": factory_config.proxy_urls.get(result.config.proxy_url) if factory_config.proxy_urls else None # corrected
        },
        "dispatcher_config": result.config
    }
