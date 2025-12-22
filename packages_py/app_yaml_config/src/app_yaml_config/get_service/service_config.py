
from typing import Dict, Any, List, Optional
import logging
from ..config_resolver import ConfigResolver
from ..validators import ServiceNotFoundError
from .types import ServiceResult, ServiceOptions, ResolutionSource

logger = logging.getLogger(__name__)

class ServiceConfig(ConfigResolver[ServiceOptions, ServiceResult]):
    """Helper class to retrieve service configurations."""
    
    def __init__(self, config: Optional['AppYamlConfig'] = None):
        from ..core import AppYamlConfig
        super().__init__(config)

    @property
    def root_key(self) -> str:
        return 'services'

    @property
    def meta_key_pattern(self) -> Dict[str, Any]:
        return {
            'type': 'grouped', 
            'keys': {'overwrite': 'overwrite_from_env', 'fallbacks': 'fallbacks_from_env'}
        }

    @property
    def not_found_error(self) -> type:
        return ServiceNotFoundError

    def get_default_options(self, options: Optional[ServiceOptions]) -> ServiceOptions:
        return options or ServiceOptions()

    def get(self, name: str, options: Optional[ServiceOptions] = None) -> ServiceResult:
        logger.debug(f"Getting service config for: {name}")
        result = super().get(name, options)
        logger.debug(f"Resolved service config for {name}. Config keys: {list(result.config.keys())}")
        return result

    def build_result(
        self,
        name: str,
        config: Dict[str, Any],
        env_overwrites: List[str],
        resolution_sources: Dict[str, ResolutionSource],
        options: ServiceOptions
    ) -> ServiceResult:
        return ServiceResult(
            name=name,
            config=config,
            env_overwrites=env_overwrites,
            resolution_sources=resolution_sources
        )

    # Alias for backward compatibility
    def list_services(self) -> List[str]:
        return self.list()

    def has_service(self, name: str) -> bool:
        return self.has(name)

def get_service(
    name: str, 
    config: Optional['AppYamlConfig'] = None, 
    options: Optional[ServiceOptions] = None
) -> ServiceResult:
    """Convenience function to get a service."""
    sc = ServiceConfig(config)
    return sc.get(name, options)
