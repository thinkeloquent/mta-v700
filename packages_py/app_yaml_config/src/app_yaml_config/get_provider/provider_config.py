
import os
import copy
from typing import Dict, Any, List, Optional
from .types import ProviderOptions, ProviderResult
from ..validators import ProviderNotFoundError

class ProviderConfig:
    """Helper class to retrieve and merge provider configurations."""

    def __init__(self, config: Optional['AppYamlConfig'] = None):
        from ..core import AppYamlConfig
        self.config = config or AppYamlConfig.get_instance()

    def get(self, name: str, options: Optional[ProviderOptions] = None) -> ProviderResult:
        """
        Get a merged provider configuration by name.
        
        Args:
            name: The name of the provider to retrieve.
            options: Options for merging and env overwrites.
            
        Returns:
            ProviderResult containing the merged config and metadata.
            
        Raises:
            ProviderNotFoundError: If the provider is not defined.
        """
        options = options or ProviderOptions()

        providers = self.config.get('providers') or {}
        provider_raw = providers.get(name)

        if not provider_raw:
            raise ProviderNotFoundError(name)

        result: Dict[str, Any] = {}
        env_overwrites: List[str] = []

        # Step 1: Merge global as base (deep copy)
        if options.merge_global:
            global_config = self.config.get('global') or {}
            result = copy.deepcopy(global_config)

        # Step 2: Deep merge provider config (provider wins)
        # We need access to _deep_merge from the config instance or implement it here.
        # Accessing protected method _deep_merge from AppYamlConfig is acceptable within the package.
        result = self.config._deep_merge(result, copy.deepcopy(provider_raw))

        # Step 3: Apply env overwrites
        if options.apply_env_overwrites and 'overwrite_from_env' in result:
            overwrites = result.get('overwrite_from_env', {})
            
            # overwrite_from_env might be None if defined as key but empty in yaml?
            # Safely handle if it's a dict
            if isinstance(overwrites, dict):
                for key, env_var_name in overwrites.items():
                    # Only overwrite if current value is null/None via explicit config or merge
                    if result.get(key) is None:
                        env_value = os.environ.get(env_var_name)
                        if env_value is not None:
                            result[key] = env_value
                            env_overwrites.append(key)

            # Remove overwrite_from_env from result (internal meta)
            if 'overwrite_from_env' in result:
                del result['overwrite_from_env']

        return ProviderResult(
            name=name,
            config=result,
            env_overwrites=env_overwrites,
            global_merged=options.merge_global
        )

    def list_providers(self) -> List[str]:
        """List all available provider names."""
        providers = self.config.get('providers') or {}
        return list(providers.keys())

    def has_provider(self, name: str) -> bool:
        """Check if a provider exists."""
        return name in self.list_providers()

def get_provider(
    name: str, 
    config: Optional['AppYamlConfig'] = None, 
    options: Optional[ProviderOptions] = None
) -> ProviderResult:
    """
    Convenience function to get a provider configuration.
    
    Args:
        name: Name of the provider.
        config: Optional AppYamlConfig instance.
        options: Optional ProviderOptions.
        
    Returns:
        ProviderResult.
    """
    pc = ProviderConfig(config)
    return pc.get(name, options)
