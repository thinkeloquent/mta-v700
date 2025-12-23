"""Load AppYamlConfig at startup."""

from .app_yaml_config import AppYamlConfig
import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
config_dir = os.path.join(project_root, "common", "config")
app_env = os.getenv("APP_ENV", "dev").lower()
vault_file = os.getenv("VAULT_SECRET_FILE")

try:
    config_files = ["base.yml", f"server.{app_env}.yaml"]
    loaded = []
    not_loaded = []
    for f in config_files:
        path = os.path.join(config_dir, f)
        if os.path.exists(path):
            loaded.append(f)
        else:
            not_loaded.append(f)

    AppYamlConfig.initialize(
        files=["base.yml", "server.{APP_ENV}.yaml"],
        config_dir=config_dir,
        computed_definitions={
            "proxy_url": lambda c: c.get_nested("global", "network", "proxy_urls", app_env)
        }
    )
    config = AppYamlConfig.get_instance()
    
    # Register Factory Computed Definitions
    from yaml_config_factory import YamlConfigFactory
    factory = YamlConfigFactory(config)
    
    # helper to register
    def register_auth_keys(config_type: str, allowlist_key: str):
        allowed = config.get(allowlist_key, [])
        if isinstance(allowed, dict): # Handle dict structure if yaml is parsed that way, but list expected
             allowed = [] 
        # Actually in yaml: expose_yaml_config_compute_auth: { providers: [a,b] }
        # So we need to look deeper.
        
    expose_auth = config.get("expose_yaml_config_compute_auth", {})
    if expose_auth:
        for cat in ['providers', 'services', 'storages']:
            items = expose_auth.get(cat, [])
            for item in items:
                key = f"auth:{cat}.{item}"
                # Capture current item in lambda default arg
                config.register_computed(key, lambda c, p=f"{cat}.{item}": factory.compute(p))

    print(f"AppYamlConfig initialized.")
    if loaded: print(f"  Loaded: {', '.join(loaded)}")
    if not_loaded: print(f"  Not found: {', '.join(not_loaded)}")
    print(f"App Name: {config.get_nested('app', 'name')}")
    if vault_file: print(f"  Vault file: {vault_file}")
except FileNotFoundError as e:
    print(f"[FATAL] Config file missing: {e}")
    print(f"  APP_ENV={app_env}, config_dir={config_dir}")
    print(f"  Ensure base.yml and server.{app_env}.yaml exist in {config_dir}")
    sys.exit(1)
except Exception as e:
    print(f"[FATAL] Failed to initialize AppYamlConfig: {e}")
    sys.exit(1)
