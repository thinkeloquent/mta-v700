
import os
import copy
from typing import Dict, Any, List, Optional, Tuple, Union
from .types import ProviderOptions, ProviderResult, ResolutionSource
from ..validators import ProviderNotFoundError

class ProviderConfig:
    """Helper class to retrieve and merge provider configurations."""

    def __init__(self, config: Optional['AppYamlConfig'] = None):
        from ..core import AppYamlConfig
        self.config = config or AppYamlConfig.get_instance()

    @staticmethod
    def _try_env_vars(env_vars: List[str]) -> Tuple[Optional[str], Optional[str]]:
        """
        Try a list of environment variables and return the first one found.
        
        Args:
            env_vars: List of environment variable names to check.
            
        Returns:
            Tuple of (value, matched_var_name). (None, None) if none found.
        """
        for var_name in env_vars:
            val = os.environ.get(var_name)
            if val is not None:
                return val, var_name
        return None, None

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
        resolution_sources: Dict[str, ResolutionSource] = {}

        # Step 1: Merge global as base (deep copy)
        if options.merge_global:
            global_config = self.config.get('global') or {}
            result = copy.deepcopy(global_config)

        # Step 2: Deep merge provider config (provider wins)
        # We need access to _deep_merge from the config instance
        result = self.config._deep_merge(result, copy.deepcopy(provider_raw))

        # Step 3: Apply env overwrites and fallbacks
        if options.apply_env_overwrites:
            # Determine effective overwrite/fallback maps (runtime > yaml)
            yaml_overwrite = result.get('overwrite_from_env', {})
            yaml_fallbacks = result.get('fallbacks_from_env', {})
            
            runtime_overwrite = options.overwrite_from_env
            runtime_fallbacks = options.fallbacks_from_env
            
            # Use runtime options if provided, otherwise YAML
            overwrite_map = runtime_overwrite if runtime_overwrite is not None else yaml_overwrite
            fallbacks_map = runtime_fallbacks if runtime_fallbacks is not None else yaml_fallbacks

            # 3a. Process Overwrites
            if overwrite_map and isinstance(overwrite_map, dict):
                for key, env_spec in overwrite_map.items():
                    # Only overwrite if current value is null/None
                    if result.get(key) is None:
                        # Ensure env_spec is a list
                        env_vars = [env_spec] if isinstance(env_spec, str) else env_spec
                        val, matched_var = self._try_env_vars(env_vars)
                        
                        if val is not None:
                            result[key] = val
                            env_overwrites.append(key)
                            resolution_sources[key] = {"source": "overwrite", "env_var": matched_var}

            # 3b. Process Fallbacks (only if value still None)
            if fallbacks_map and isinstance(fallbacks_map, dict):
                for key, env_spec in fallbacks_map.items():
                    if result.get(key) is None:
                         # Ensure env_spec is a list
                        env_vars = [env_spec] if isinstance(env_spec, str) else env_spec
                        val, matched_var = self._try_env_vars(env_vars)
                        
                        if val is not None:
                            result[key] = val
                            env_overwrites.append(key)
                            resolution_sources[key] = {"source": "fallback", "env_var": matched_var}

            # Cleanup metadata keys from result
            if 'overwrite_from_env' in result:
                del result['overwrite_from_env']
            if 'fallbacks_from_env' in result:
                del result['fallbacks_from_env']

        return ProviderResult(
            name=name,
            config=result,
            env_overwrites=env_overwrites,
            global_merged=options.merge_global,
            resolution_sources=resolution_sources
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
