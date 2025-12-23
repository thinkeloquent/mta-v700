"""Core business logic for AppYamlConfig."""

import os
import yaml
import logging
from typing import List, Dict, Any, Optional, Union
from copy import deepcopy
from deepmerge import always_merger
from .domain import LoadResult, ComputedDefinition
from .validators import (
    ConfigNotInitializedError, 
    ConfigAlreadyInitializedError,
    ComputedKeyNotFoundError,
    CircularDependencyError,
    ValidationError
)

logger = logging.getLogger(__name__)

class AppYamlConfig:
    """Singleton configuration loader.
    
    Loads YAML files at startup, merges them, and provides immutable access.
    """
    _instance: Optional['AppYamlConfig'] = None
    _initialized: bool = False
    _data: Dict[str, Any] = {}
    _computed_definitions: Dict[str, ComputedDefinition] = {}
    _computed_cache: Dict[str, Any] = {}
    _load_result: Optional[LoadResult] = None
    _computing_stack: List[str] = []

    def __new__(cls) -> 'AppYamlConfig':
        if cls._instance is None:
            cls._instance = super(AppYamlConfig, cls).__new__(cls)
            cls._instance._initialized = False
            cls._instance._data = {}
            cls._instance._computed_definitions = {}
            cls._instance._computed_cache = {}
            cls._instance._computing_stack = []
        return cls._instance

    @classmethod
    def initialize(
        cls, 
        files: List[str], 
        config_dir: Optional[str] = None, 
        app_env: Optional[str] = None,
        computed_definitions: Optional[Dict[str, ComputedDefinition]] = None
    ) -> 'AppYamlConfig':
        """Initialize the singleton configuration."""
        instance = cls()
        
        if instance._initialized:
            logger.warning("AppYamlConfig already initialized. Returning existing instance.")
            return instance

        # Setup
        result = LoadResult()
        
        # Resolve APP_ENV
        env = (app_env or os.getenv('APP_ENV', 'dev')).lower()
        result.app_env = env

        merged_data = {}
        
        # Resolve files
        files_to_load = []
        for file_path in files:
            # 1. Substitute {APP_ENV}
            resolved_name = file_path.replace("{APP_ENV}", env)
            
            # 2. Resolve relative to config_dir
            if config_dir and not os.path.isabs(resolved_name):
                resolved_path = os.path.join(config_dir, resolved_name)
            else:
                resolved_path = os.path.abspath(resolved_name)

            # 3. Check for env-specific override pattern: name.yaml -> name.{env}.yaml
            # Only applying this logic if the filename doesn't already contain the env
            # (simple heuristic based on spec requirement FR-003)
            # Actually spec says: "Check if env-specific version exists... use it; else use base"
            # This implies if we ask for "server.yaml", we check "server.dev.yaml" first.
            
            base, ext = os.path.splitext(resolved_path)
            env_specific_path = f"{base}.{env}{ext}"
            
            final_path = resolved_path
            if os.path.exists(env_specific_path):
                final_path = env_specific_path
            elif os.path.exists(resolved_path):
                final_path = resolved_path
            else:
                # Fatal: config missing
                msg = f"Config file not found: {resolved_path} (checked {env_specific_path} as well)"
                logger.error(msg)
                # Per spec: Fatal error on ANY load failure
                raise FileNotFoundError(msg) # Or exit? Spec says "SystemExit(1)"

            files_to_load.append(final_path)

        # Load and Merge
        for file_path in files_to_load:
            try:
                with open(file_path, 'r') as f:
                    file_data = yaml.safe_load(f) or {}
                    
                # Deep merge
                # deepmerge library 'always_merger' merges dicts, but for lists?
                # Spec says: "Arrays replaced (not concatenated)"
                # The 'always_merger' default strategy for lists is 'merge' (concatenate) usually?
                # Wait, 'deep_merge' spec says: target[key] = source[key] # Replace (including arrays)
                # So we need a merger that replaces lists.
                
                # Custom merge application manually or use library with config?
                # We can do manually for better control adhering to spec.
                merged_data = cls._deep_merge(merged_data, file_data)
                
                result.files_loaded.append(file_path)
                result.merge_order.append(file_path)
                
            except yaml.YAMLError as e:
                msg = f"YAML parsing error in {file_path}: {e}"
                logger.error(msg)
                raise ValidationError(msg)
            except Exception as e:
                msg = f"Error loading {file_path}: {e}"
                logger.error(msg)
                raise e

        # Commit state
        instance._data = merged_data
        instance._computed_definitions = computed_definitions or {}
        instance._computed_cache = {}
        instance._load_result = result
        instance._initialized = True
        
        logger.info(f"AppYamlConfig initialized. Loaded: {len(result.files_loaded)} files.")
        return instance

    @classmethod
    def get_instance(cls) -> 'AppYamlConfig':
        """Get the initialized singleton instance."""
        if cls._instance is None or not cls._instance._initialized:
            raise ConfigNotInitializedError("AppYamlConfig not initialized. Call initialize() first.")
        return cls._instance

    @staticmethod
    def _deep_merge(target: Dict, source: Dict) -> Dict:
        """Recursive deep merge that replaces arrays."""
        for key, value in source.items():
            if (
                key in target 
                and isinstance(target[key], dict) 
                and isinstance(value, dict)
            ):
                AppYamlConfig._deep_merge(target[key], value)
            else:
                target[key] = value
        return target

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def get_nested(self, *keys: str, default: Any = None) -> Any:
        current = self._data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current

    def get_computed(self, key: str) -> Any:
        if not self._initialized:
             raise ConfigNotInitializedError("Not initialized")
             
        if key not in self._computed_definitions:
            raise ComputedKeyNotFoundError(f"Computed value '{key}' not defined")
            
        if key in self._computed_cache:
            return self._computed_cache[key]
            
        if key in self._computing_stack:
            raise CircularDependencyError(f"Circular dependency detected for '{key}': {self._computing_stack}")
            
        self._computing_stack.append(key)
        try:
            definition = self._computed_definitions[key]
            # Pass strict instance typed as 'AppYamlConfig'
            val = definition(self)
            self._computed_cache[key] = val
            return val
        finally:
            self._computing_stack.pop()

    def get_all(self) -> Dict[str, Any]:
        return deepcopy(self._data)

    def is_initialized(self) -> bool:
        return self._initialized

    def get_load_result(self) -> Optional[LoadResult]:
        return self._load_result

    def register_computed(self, key: str, definition: ComputedDefinition) -> None:
        """Register a computed definition after initialization.
        
        Useful for factory-generated definitions that depend on the config being loaded first
        to determine which keys to expose.
        """
        if not self._initialized:
             raise ConfigNotInitializedError("Not initialized")
        
        if key in self._computed_definitions:
            logger.warning(f"Overwriting existing computed definition for '{key}'")
            
        self._computed_definitions[key] = definition


    # Forbidden methods (No-op or raise)
    def reset(self): raise NotImplementedError("Immutable config")
    def clear(self): raise NotImplementedError("Immutable config")
    def set(self, k, v): raise NotImplementedError("Immutable config")
    def update(self, d): raise NotImplementedError("Immutable config")
    
    # Internal reset for testing ONLY
    def _reset_for_testing(self):
        self._initialized = False
        self._data = {}
        self._computed_definitions = {}
        self._computed_cache = {}
        self._load_result = None
        self._computing_stack = []
