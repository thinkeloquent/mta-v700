from typing import Literal, Union, Dict, Any, Optional
from app_yaml_config import AppYamlConfig
from fetch_auth_config import fetch_auth_config, AuthConfig
from fetch_auth_encoding import encode_auth

ConfigPath = Literal['providers', 'services', 'storages']

class YamlConfigFactory:
    """Factory for computing auth-resolved config from YamlConfig paths."""

    def __init__(
        self,
        config: AppYamlConfig,
        fetch_auth_config_fn=fetch_auth_config,
        encode_auth_fn=encode_auth
    ):
        self._config = config
        self._fetch_auth_config = fetch_auth_config_fn
        self._encode_auth = encode_auth_fn

    def compute(
        self,
        path: str,  # e.g., 'providers.anthropic', 'services.confluence'
        include_headers: bool = False
    ) -> Dict[str, Any]:
        """
        Compute auth-resolved config for a given path.

        Args:
            path: Dot-notation path like 'providers.anthropic'
            include_headers: If True, include encoded Authorization headers

        Returns:
            Dict with resolved auth config + optional headers
        """
        # 1. Parse Path
        parts = path.split('.')
        if len(parts) != 2:
            raise ValueError(f"Invalid path format '{path}'. Expected 'type.name' (e.g. providers.anthropic)")
        
        config_type, config_name = parts[0], parts[1]
        
        if config_type not in ['providers', 'services', 'storages']:
            raise ValueError(f"Invalid config type '{config_type}'. Must be providers, services, or storages.")

        # 2. Retrieve Raw Config from AppYamlConfig
        # AppYamlConfig usually exposes getters like get_provider_config(name)
        # We need generic access or map types to methods.
        raw_config = None
        
        # Access internal config structure directly via generic getter if available, 
        # or map to specific methods.
        # Assuming AppYamlConfig has a way to get raw dict for these.
        # Use get_nested if available, or assume structure matches 'providers', 'services' keys in yaml.
        
        # HACK: Using get_nested or get() assuming the root structure mirrors the yaml
        raw_config = self._config.get_nested(config_type, config_name)
        
        if not raw_config:
             # Try accessing via specific typed getters if direct access fails?
             # But fetching raw config dict is safer for fetch_auth_config which expects a dict.
             raise ValueError(f"Configuration not found for '{path}'")

        # 3. Resolve Auth
        auth_config: AuthConfig = self._fetch_auth_config(config_name, raw_config)
        
        result = {
            "auth_config": auth_config
        }
        
        # 4. Encode Headers (Optional)
        if include_headers:
            # Prepare kwargs for encode_auth based on resolved config
            creds = {}
            if auth_config.username: creds['username'] = auth_config.username
            if auth_config.password: creds['password'] = auth_config.password
            if auth_config.email: creds['email'] = auth_config.email
            if auth_config.token: creds['token'] = auth_config.token
            if auth_config.header_name: creds['header_key'] = auth_config.header_name
            if auth_config.header_value: creds['header_value'] = auth_config.header_value
            
            # Pass everything else too if needed
            
            headers = self._encode_auth(auth_config.type, **creds)
            result['headers'] = headers
            
        return result
