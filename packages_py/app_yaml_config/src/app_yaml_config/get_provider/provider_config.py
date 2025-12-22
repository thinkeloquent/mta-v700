
import copy
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from ..config_resolver import ConfigResolver
from ..domain import ResolutionSource, BaseResolveOptions, BaseResult
from ..validators import ProviderNotFoundError

logger = logging.getLogger(__name__)

@dataclass
class ProviderOptions(BaseResolveOptions):
    """Options for retrieving provider configuration."""
    merge_global: bool = True
    overwrite_from_env: Optional[Dict[str, Any]] = None
    fallbacks_from_env: Optional[Dict[str, Any]] = None

@dataclass
class ProviderResult(BaseResult):
    """Result of a provider configuration retrieval."""
    global_merged: bool = True

class ProviderConfig(ConfigResolver[ProviderOptions, ProviderResult]):
    """Helper class to retrieve and merge provider configurations."""

    @property
    def root_key(self) -> str:
        return 'providers'

    @property
    def meta_key_pattern(self) -> Dict[str, Any]:
        return {
            'type': 'grouped', 
            'keys': {'overwrite': 'overwrite_from_env', 'fallbacks': 'fallbacks_from_env'}
        }

    @property
    def not_found_error(self) -> type:
        return ProviderNotFoundError

    def get_default_options(self, options: Optional[ProviderOptions]) -> ProviderOptions:
        return options or ProviderOptions()

    def pre_process(self, config: Dict[str, Any], options: ProviderOptions) -> Dict[str, Any]:
        # Merge global config if requested
        if options.merge_global:
            global_config = self.config.get('global') or {}
            # Deep copy global config to avoid mutation
            base = copy.deepcopy(global_config)
            # Use internal _deep_merge from core
            return self.config._deep_merge(base, config)
        return config

    def _extract_env_meta(self, config: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        # Override to support runtime overwrites from options
        # Note: This is tricky because base class relies on config content.
        # But ProviderConfig supports passing overrides in options.
        # However, the base class signature for _extract_env_meta only checks config.
        # We need to handle this. The cleanest way is to merge the runtime options 
        # into the config object TEMPORARILY or just handle it in this override.
        
        # Let's use the base implementation first
        meta = super()._extract_env_meta(config)
        
        # We don't have access to options here easily unless we change the signature 
        # or store options. But wait, ConfigResolver is stateless per request except for config ref.
        # The get() method calls extract_env_meta.
        
        # Actually, in the original implementation, runtime options took precedence.
        # To support this in the new structure without changing base signature too much,
        # we might need to rely on the fact that we can't easily access options here.
        
        # Alternative: We can modify the `config` object in `pre_process` to include 
        # the runtime options as keys if they aren't there? No, that modifies data.
        
        # Let's check `get` method loop in base class. It calls `_extract_env_meta(result)`.
        # If we want to support runtime options `overwrite_from_env`, we should probably 
        # inject them into `result` during `pre_process` IF they are provided?
        # But `pre_process` has access to options.
        
        return meta

    def get(self, name: str, options: Optional[ProviderOptions] = None) -> ProviderResult:
        # We need to handle the runtime options logic which is specific to ProviderConfig.
        # The base `get` might not be flexible enough if we strictly follow it.
        # However, we can override `get` or `_extract_env_meta` if we store options temporarily 
        # OR we can inject the runtime options into the config dict in `pre_process`.
        
        # Let's inject into config in pre_process.
        logger.debug(f"Getting provider config for: {name}")
        result = super().get(name, options)
        logger.debug(f"Resolved provider config for {name}. Env overwrites: {result.env_overwrites}")
        return result

    def pre_process(self, config: Dict[str, Any], options: ProviderOptions) -> Dict[str, Any]:
        # 1. Merge global
        if options.merge_global:
            global_config = self.config.get('global') or {}
            base = copy.deepcopy(global_config)
            config = self.config._deep_merge(base, config)

        # 2. Inject runtime env specs if provided (override what's in YAML)
        if options.overwrite_from_env is not None:
            logger.debug(f"Injecting runtime overwrite_from_env for provider: {options.overwrite_from_env}")
            config['overwrite_from_env'] = options.overwrite_from_env
            
        if options.fallbacks_from_env is not None:
            logger.debug(f"Injecting runtime fallbacks_from_env for provider: {options.fallbacks_from_env}")
            config['fallbacks_from_env'] = options.fallbacks_from_env
            
        return config

    def build_result(
        self,
        name: str,
        config: Dict[str, Any],
        env_overwrites: List[str],
        resolution_sources: Dict[str, ResolutionSource],
        options: ProviderOptions
    ) -> ProviderResult:
        return ProviderResult(
            name=name,
            config=config,
            env_overwrites=env_overwrites,
            resolution_sources=resolution_sources,
            global_merged=options.merge_global
        )

    # Convenience methods kept for backward compatibility if needed, 
    # but base class has list() and has() which match the public API requirement.
    # The original had list_providers() and has_provider(). 
    # We should alias them for backward compatibility.

    def list_providers(self) -> List[str]:
        return self.list()

    def has_provider(self, name: str) -> bool:
        return self.has(name)

def get_provider(
    name: str, 
    config: Optional['AppYamlConfig'] = None, 
    options: Optional[ProviderOptions] = None
) -> ProviderResult:
    """Convenience function to get a provider."""
    pc = ProviderConfig(config)
    return pc.get(name, options)
