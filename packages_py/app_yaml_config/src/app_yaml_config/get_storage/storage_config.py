
import os
import copy
import re
from typing import Optional, List, Tuple, Any, Dict, Union
from ..core import AppYamlConfig
from ..validators import StorageNotFoundError
from .types import StorageResult, StorageOptions, ResolutionSource

class StorageConfig:
    def __init__(self, config: Optional[AppYamlConfig] = None):
        self.config = config or AppYamlConfig.get_instance()

    @staticmethod
    def _try_env_vars(env_vars: Union[str, List[str]]) -> Tuple[Optional[str], Optional[str]]:
        """Try environment variables in order, return first found value and var name."""
        vars_list = env_vars if isinstance(env_vars, list) else [env_vars]
        
        for env_var in vars_list:
            if not isinstance(env_var, str):
                continue
            value = os.environ.get(env_var)
            if value is not None:
                return value, env_var
                
        return None, None

    def _extract_base_property(self, meta_key: str) -> Optional[str]:
        """Extract base property from meta key like env_host_key -> host"""
        match = re.match(r'^env_(.+)_key(_fallbacks)?$', meta_key)
        return match.group(1) if match else None

    def _find_env_meta_keys(self, config: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Find all env meta keys and group by base property."""
        result: Dict[str, Dict[str, Any]] = {}

        for key, value in config.items():
            if key.startswith('env_') and key.endswith('_key') and not key.endswith('_key_fallbacks'):
                base_prop = self._extract_base_property(key)
                if base_prop:
                    if base_prop not in result:
                        result[base_prop] = {}
                    result[base_prop]['primary'] = value
            elif key.endswith('_key_fallbacks'):
                base_prop = self._extract_base_property(key)
                if base_prop:
                    if base_prop not in result:
                        result[base_prop] = {}
                    result[base_prop]['fallbacks'] = value

        return result

    def get(self, name: str, options: Optional[StorageOptions] = None) -> StorageResult:
        """Get a storage configuration by name."""
        options = options or StorageOptions()
        
        storages = self.config.get('storage') or {}
        storage_raw = storages.get(name)
        
        if not storage_raw:
            raise StorageNotFoundError(name)
            
        # Deep copy to avoid mutation
        result: Dict[str, Any] = copy.deepcopy(storage_raw)
        env_overwrites: List[str] = []
        resolution_sources: Dict[str, ResolutionSource] = {}
        
        # Find all env meta keys
        env_meta_keys = self._find_env_meta_keys(result)
        
        # Process each property with env configuration
        for base_prop, env_config in env_meta_keys.items():
            # Only process if the base property is None
            if result.get(base_prop) is not None:
                continue
                
            # Step 1: Try primary env key
            if options.apply_env_overwrites and 'primary' in env_config:
                value, env_var = self._try_env_vars(env_config['primary'])
                if value is not None:
                    result[base_prop] = value
                    env_overwrites.append(base_prop)
                    resolution_sources[base_prop] = {"source": "overwrite", "env_var": env_var}
                    continue
            
            # Step 2: Try fallback env keys
            if options.apply_fallbacks and 'fallbacks' in env_config:
                value, env_var = self._try_env_vars(env_config['fallbacks'])
                if value is not None:
                    result[base_prop] = value
                    env_overwrites.append(base_prop)
                    resolution_sources[base_prop] = {"source": "fallback", "env_var": env_var}

        # Remove meta keys from result
        if options.remove_meta_keys:
            keys_to_remove = [k for k in result.keys()
                             if k.startswith('env_') and (k.endswith('_key') or k.endswith('_key_fallbacks'))]
            for key in keys_to_remove:
                del result[key]
        
        return StorageResult(
            name=name,
            config=result,
            env_overwrites=env_overwrites,
            resolution_sources=resolution_sources
        )

    def list_storages(self) -> List[str]:
        """List all available storage names."""
        storages = self.config.get('storage') or {}
        return list(storages.keys())

    def has_storage(self, name: str) -> bool:
        """Check if a storage exists."""
        return name in self.list_storages()

def get_storage(
    name: str, 
    config: Optional[AppYamlConfig] = None, 
    options: Optional[StorageOptions] = None
) -> StorageResult:
    """Convenience function to get a storage."""
    sc = StorageConfig(config)
    return sc.get(name, options)
