
import os
import copy
from typing import Optional, List, Tuple, Any, Dict, Union
from ..core import AppYamlConfig
from ..validators import ServiceNotFoundError
from .types import ServiceResult, ServiceOptions, ResolutionSource

class ServiceConfig:
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

    def get(self, name: str, options: Optional[ServiceOptions] = None) -> ServiceResult:
        """Get a service configuration by name."""
        options = options or ServiceOptions()
        
        services = self.config.get('services') or {}
        service_raw = services.get(name)
        
        if not service_raw:
            raise ServiceNotFoundError(name)
            
        # Deep copy to avoid mutation
        result: Dict[str, Any] = copy.deepcopy(service_raw)
        env_overwrites: List[str] = []
        resolution_sources: Dict[str, ResolutionSource] = {}
        
        # Extract meta keys
        overwrite_from_env = result.get('overwrite_from_env', {})
        fallbacks_from_env = result.get('fallbacks_from_env', {})
        
        # Step 1: Apply overwrite_from_env
        if options.apply_env_overwrites and isinstance(overwrite_from_env, dict):
            for key, env_var_spec in overwrite_from_env.items():
                if result.get(key) is None:
                    value, env_var = self._try_env_vars(env_var_spec)
                    if value is not None:
                        result[key] = value
                        env_overwrites.append(key)
                        resolution_sources[key] = {"source": "overwrite", "env_var": env_var}

        # Step 2: Apply fallbacks_from_env (only if still null)
        if options.apply_fallbacks and isinstance(fallbacks_from_env, dict):
             for key, env_var_spec in fallbacks_from_env.items():
                if result.get(key) is None:
                    value, env_var = self._try_env_vars(env_var_spec)
                    if value is not None:
                        result[key] = value
                        env_overwrites.append(key)
                        resolution_sources[key] = {"source": "fallback", "env_var": env_var}
        
        # Remove meta keys from result
        result.pop('overwrite_from_env', None)
        result.pop('fallbacks_from_env', None)
        
        return ServiceResult(
            name=name,
            config=result,
            env_overwrites=env_overwrites,
            resolution_sources=resolution_sources
        )

    def list_services(self) -> List[str]:
        """List all available service names."""
        services = self.config.get('services') or {}
        return list(services.keys())

    def has_service(self, name: str) -> bool:
        """Check if a service exists."""
        return name in self.list_services()

def get_service(
    name: str, 
    config: Optional[AppYamlConfig] = None, 
    options: Optional[ServiceOptions] = None
) -> ServiceResult:
    """Convenience function to get a service."""
    sc = ServiceConfig(config)
    return sc.get(name, options)
