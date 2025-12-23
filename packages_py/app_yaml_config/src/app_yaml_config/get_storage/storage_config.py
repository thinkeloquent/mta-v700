
import re
import logging
from typing import Dict, Any, List, Optional
from ..config_resolver import ConfigResolver
from ..validators import StorageNotFoundError
from .types import StorageResult, StorageOptions, ResolutionSource

logger = logging.getLogger(__name__)

class StorageConfig(ConfigResolver[StorageOptions, StorageResult]):
    """Helper class to retrieve storage configurations."""
    
    def __init__(self, config: Optional['AppYamlConfig'] = None):
        from ..core import AppYamlConfig
        super().__init__(config)

    @property
    def root_key(self) -> str:
        return 'storage'

    @property
    def meta_key_pattern(self) -> Dict[str, Any]:
        return {
            'type': 'single',
            'key': 'overwrite_from_env'
        }

    @property
    def not_found_error(self) -> type:
        return StorageNotFoundError

    def get_default_options(self, options: Optional[StorageOptions]) -> StorageOptions:
        return options or StorageOptions()

    def get(self, name: str, options: Optional[StorageOptions] = None) -> StorageResult:
        logger.debug(f"Getting storage config for: {name}")
        result = super().get(name, options)
        logger.debug(f"Resolved storage config for {name}. Env overwrites: {result.env_overwrites}")
        return result

    def build_result(
        self,
        name: str,
        config: Dict[str, Any],
        env_overwrites: List[str],
        resolution_sources: Dict[str, ResolutionSource],
        options: StorageOptions
    ) -> StorageResult:
        return StorageResult(
            name=name,
            config=config,
            env_overwrites=env_overwrites,
            resolution_sources=resolution_sources
        )

    # Alias for backward compatibility
    def list_storages(self) -> List[str]:
        return self.list()

    def has_storage(self, name: str) -> bool:
        return self.has(name)

def get_storage(
    name: str, 
    config: Optional['AppYamlConfig'] = None, 
    options: Optional[StorageOptions] = None
) -> StorageResult:
    """Convenience function to get a storage."""
    sc = StorageConfig(config)
    return sc.get(name, options)
