
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple, TypeVar, Generic, Union
import os
import copy
import re
from .core import AppYamlConfig
from .domain import BaseResolveOptions, BaseResult, ResolutionSource

TOptions = TypeVar('TOptions', bound=BaseResolveOptions)
TResult = TypeVar('TResult', bound=BaseResult)

class ConfigResolver(ABC, Generic[TOptions, TResult]):
    """Abstract base class for retrieving configuration with env overwrites and fallbacks."""

    def __init__(self, config: Optional[AppYamlConfig] = None):
        self.config = config or AppYamlConfig.get_instance()

    # ========== Abstract Properties ==========

    @property
    @abstractmethod
    def root_key(self) -> str:
        """Root key in YAML config (e.g., 'providers', 'services', 'storage')."""
        pass

    @property
    @abstractmethod
    def meta_key_pattern(self) -> Dict[str, Any]:
        """
        Meta key pattern for env overwrite detection.
        Example: 
          {'type': 'grouped', 'keys': {'overwrite': '...', 'fallbacks': '...'}}
          {'type': 'per-property', 'regex': re.Pattern}
        """
        pass

    @property
    @abstractmethod
    def not_found_error(self) -> type:
        """Exception class to raise when item is not found."""
        pass

    @abstractmethod
    def build_result(
        self,
        name: str,
        config: Dict[str, Any],
        env_overwrites: List[str],
        resolution_sources: Dict[str, ResolutionSource],
        options: TOptions
    ) -> TResult:
        """Build the final result object."""
        pass

    # ========== Public API ==========

    def get(self, name: str, options: Optional[TOptions] = None) -> TResult:
        """Get a configuration item by name with full resolution."""
        opts = self.get_default_options(options)
        items = self.config.get(self.root_key) or {}
        item_raw = items.get(name)

        if not item_raw:
            raise self.not_found_error(name)

        # Deep copy to avoid mutation
        result = copy.deepcopy(item_raw)

        # Hook for subclass preprocessing (e.g., global merge)
        result = self.pre_process(result, opts)

        # Extract env meta based on pattern
        env_meta = self._extract_env_meta(result)

        # Apply env resolution
        env_overwrites, resolution_sources = self._apply_env_resolution(result, env_meta, opts)

        # Remove meta keys if configured
        if opts.remove_meta_keys:
            self._remove_meta_keys(result)

        return self.build_result(name, result, env_overwrites, resolution_sources, opts)

    def list(self) -> List[str]:
        """List all available item names."""
        items = self.config.get(self.root_key) or {}
        return list(items.keys())

    def has(self, name: str) -> bool:
        """Check if an item exists."""
        return name in self.list()

    # ========== Protected Hooks ==========

    def get_default_options(self, options: Optional[TOptions]) -> TOptions:
        """Override to provide default options."""
        return options or BaseResolveOptions()  # type: ignore

    def pre_process(self, config: Dict[str, Any], options: TOptions) -> Dict[str, Any]:
        """Override to modify config before env resolution (e.g. global merge)."""
        return config

    # ========== Shared Implementation ==========

    def _try_env_vars(self, env_vars: Union[str, List[str]]) -> Tuple[Optional[str], Optional[str]]:
        """Try environment variables in order, return first found value and var name."""
        vars_list = env_vars if isinstance(env_vars, list) else [env_vars]
        
        for env_var in vars_list:
            if not isinstance(env_var, str):
                continue
            value = os.environ.get(env_var)
            if value is not None:
                return value, env_var
                
        return None, None

    def _extract_env_meta(self, config: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Extract environment variable metadata based on the pattern."""
        pattern = self.meta_key_pattern
        result: Dict[str, Dict[str, Any]] = {}

        if pattern.get('type') == 'single':
            key = pattern['key']
            overwrites = config.get(key, {})

            if isinstance(overwrites, dict):
                for prop, env_spec in overwrites.items():
                    if prop not in result:
                        result[prop] = {}
                    result[prop]['primary'] = env_spec

        elif pattern.get('type') == 'grouped':
            # Pattern: overwrite_from_env / fallbacks_from_env
            overwrites = config.get(pattern['keys']['overwrite'], {})
            
            if isinstance(overwrites, dict):
                for prop, env_spec in overwrites.items():
                    if prop not in result:
                        result[prop] = {}
                    result[prop]['primary'] = env_spec

        elif pattern.get('type') == 'per-property':
            # Pattern: env_{prop}_key / env_{prop}_key_fallbacks
            regex = pattern['regex']
            for key, value in config.items():
                match = regex.match(key)
                if match:
                    base_prop = match.group(1)
                    # Check if suffix implies fallback
                    # Regex must be: ^env_(.+)_key(_fallbacks)?$
                    # Group 1 = base_prop
                    # Group 2 = _fallbacks (optional)
                    is_fallback = match.group(2) == '_fallbacks'

                    if base_prop:
                        if base_prop not in result:
                            result[base_prop] = {}

                        if is_fallback:
                            result[base_prop]['fallbacks'] = value
                        else:
                            result[base_prop]['primary'] = value

        return result

    def _apply_env_resolution(
        self,
        result: Dict[str, Any],
        env_meta: Dict[str, Dict[str, Any]],
        options: TOptions
    ) -> Tuple[List[str], Dict[str, ResolutionSource]]:
        """Apply environment variable resolution based on extracted metadata."""
        env_overwrites: List[str] = []
        resolution_sources: Dict[str, ResolutionSource] = {}

        for prop, meta in env_meta.items():
            # Only process if property is explicitly null/None in the config
            # Values set in YAML take precedence over ENV
            if result.get(prop) is not None:
                continue

            # Step 1: Try primary overwrite
            if options.apply_env_overwrites and 'primary' in meta:
                value, matched_var = self._try_env_vars(meta['primary'])
                if value is not None:
                    result[prop] = value
                    env_overwrites.append(prop)
                    resolution_sources[prop] = ResolutionSource(source='env', env_var=matched_var)
                    continue

        return env_overwrites, resolution_sources

    def _remove_meta_keys(self, result: Dict[str, Any]) -> None:
        """Remove metadata keys from the configuration result."""
        pattern = self.meta_key_pattern

        if pattern.get('type') == 'single':
            result.pop(pattern['key'], None)
        elif pattern.get('type') == 'grouped':
            result.pop(pattern['keys']['overwrite'], None)
            result.pop(pattern['keys']['fallbacks'], None)
        elif pattern.get('type') == 'per-property':
            regex = pattern['regex']
            # Find matching keys first to avoid runtime dict size change error
            keys_to_remove = [k for k in result.keys() if regex.match(k)]
            for key in keys_to_remove:
                del result[key]
