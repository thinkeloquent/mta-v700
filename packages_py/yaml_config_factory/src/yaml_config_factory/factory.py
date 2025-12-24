
import logging
from dataclasses import dataclass, field
from typing import Literal, Union, Dict, Any, Optional, Callable
from app_yaml_config import (
    AppYamlConfig,
    resolve_provider_proxy,
    ProxyResolutionResult,
    get_provider,
    get_service,
    get_storage
)
from fetch_auth_config import fetch_auth_config, AuthConfig
from fetch_auth_encoding import encode_auth


logger = logging.getLogger(__name__)


ConfigPath = Literal['providers', 'services', 'storages']


@dataclass
class NetworkConfig:
    default_environment: str = "dev"
    proxy_urls: Dict[str, Optional[str]] = field(default_factory=dict)
    ca_bundle: Optional[str] = None
    cert: Optional[str] = None
    cert_verify: bool = False
    agent_proxy: Optional[Dict[str, Optional[str]]] = None


@dataclass
class ComputeOptions:
    include_headers: bool = False
    include_proxy: bool = False
    include_network: bool = False
    include_config: bool = False
    suppress_auth_errors: bool = False
    environment: Optional[str] = None


@dataclass
class ComputeResult:
    config_type: ConfigPath
    config_name: str
    auth_config: Optional[AuthConfig] = None
    auth_error: Optional[Exception] = None
    headers: Optional[Dict[str, str]] = None
    proxy_config: Optional[ProxyResolutionResult] = None
    network_config: Optional[NetworkConfig] = None
    config: Optional[Dict[str, Any]] = None


class YamlConfigFactory:
    """Factory for computing fully resolved runtime configuration."""

    def __init__(
        self,
        config: AppYamlConfig,
        fetch_auth_config_fn: Callable = fetch_auth_config,
        encode_auth_fn: Callable = encode_auth
    ):
        self._config = config
        self._fetch_auth_config_fn = fetch_auth_config_fn
        self._encode_auth_fn = encode_auth_fn

    async def compute(
        self,
        path: str,
        options: Optional[ComputeOptions] = None,
        request: Any = None
    ) -> ComputeResult:
        """
        Compute comprehensive runtime configuration.
        """
        opts = options or ComputeOptions()
        logger.debug(f"compute: Starting path={path} options={opts}")

        try:
            config_type, config_name = self._parse_path(path)

            # 1. Auth Resolution
            auth_result = {}
            auth_error = None
            
            try:
                auth_result = await self._compute_auth_internal(config_type, config_name, opts.include_headers, request)
            except Exception as e:
                if opts.suppress_auth_errors:
                    logger.error(f"compute: Auth resolution failed but suppressed: {e}")
                    auth_error = e
                else:
                    raise e
            
            result = ComputeResult(
                config_type=config_type,
                config_name=config_name,
                auth_config=auth_result.get('auth_config'),
                headers=auth_result.get('headers'),
                auth_error=auth_error
            )

            # 2. Proxy Resolution
            if opts.include_proxy:
                logger.debug("compute: Resolving proxy")
                result.proxy_config = self.compute_proxy(path, opts.environment)

            # 3. Network Configuration
            if opts.include_network:
                logger.debug("compute: Resolving network config")
                result.network_config = self.compute_network()

            # 4. Raw Config
            if opts.include_config:
                logger.debug("compute: Retrieving raw config")
                result.config = self.compute_config(path)

            logger.debug(f"compute: Completed type={config_type} name={config_name}")
            return result

        except Exception as e:
            logger.error(f"compute failed path={path} error={str(e)}", exc_info=True)
            raise e

    def compute_proxy(self, path: str, environment: Optional[str] = None) -> ProxyResolutionResult:
        """Compute proxy configuration."""
        logger.debug(f"compute_proxy: Starting path={path} env={environment}")
        
        config_type, config_name = self._parse_path(path)
        
        # Get raw config with meta keys intact
        raw_config = self._get_raw_config(config_type, config_name, remove_meta_keys=False)
        global_config = self._config.get('global') or {}
        
        load_result = self._config.get_load_result()
        app_env = environment or (load_result.app_env if load_result else 'dev')
        
        result = resolve_provider_proxy(config_name, raw_config, global_config, app_env)
        
        logger.debug(f"compute_proxy: Completed source={result.source} url={result.proxy_url}")
        return result

    def compute_network(self) -> NetworkConfig:
        """Compute network configuration."""
        logger.debug("compute_network: Starting")
        
        global_config = self._config.get('global') or {}
        network = global_config.get('network') or {}
        
        agent_proxy_dict = None
        if network.get('agent_proxy'):
            agent_proxy_dict = {
                'http_proxy': network['agent_proxy'].get('http_proxy'),
                'https_proxy': network['agent_proxy'].get('https_proxy')
            }

        result = NetworkConfig(
            default_environment=network.get('default_environment', 'dev'),
            proxy_urls=network.get('proxy_urls', {}),
            ca_bundle=network.get('ca_bundle'),
            cert=network.get('cert'),
            cert_verify=network.get('cert_verify', False),
            agent_proxy=agent_proxy_dict
        )
        
        logger.debug("compute_network: Completed")
        return result

    def compute_config(self, path: str) -> Dict[str, Any]:
        """Get fully resolved configuration with env vars applied."""
        logger.debug(f"compute_config: Starting path={path}")
        config_type, config_name = self._parse_path(path)

        # Use the appropriate resolver for env var resolution
        if config_type == 'providers':
            result = get_provider(config_name, self._config)
            return result.config
        elif config_type == 'services':
            result = get_service(config_name, self._config)
            return result.config
        elif config_type == 'storage':
            result = get_storage(config_name, self._config)
            return result.config
        else:
            # Fallback to raw config
            return self._get_raw_config(config_type, config_name, remove_meta_keys=True)

    async def compute_all(
        self,
        path: str,
        environment: Optional[str] = None,
        request: Any = None
    ) -> ComputeResult:
        """Convenience method to get all configuration aspects."""
        return await self.compute(path, ComputeOptions(
            include_headers=True,
            include_proxy=True,
            include_network=True,
            include_config=True,
            suppress_auth_errors=True,
            environment=environment
        ), request)

    # =========================================================================
    # Internal Helpers
    # =========================================================================

    def _parse_path(self, path: str) -> tuple[str, str]:
        if not path:
            raise ValueError("Path cannot be empty")

        parts = path.split('.')
        if len(parts) != 2:
            raise ValueError(f"Invalid path format '{path}'. Expected 'type.name' (e.g. providers.anthropic)")

        config_type, config_name = parts[0], parts[1]

        if config_type not in ['providers', 'services', 'storages']:
            raise ValueError(f"Invalid config type '{config_type}'. Must be providers, services, or storages.")
        
        # Backward compatibility / Schema mapping
        # Config has 'storage' root key, whilst path logic uses 'storages' plural convention
        if config_type == 'storages':
            config_type = 'storage'

        return config_type, config_name

    def _get_raw_config(self, config_type: str, config_name: str, remove_meta_keys: bool) -> Dict[str, Any]:
        # Access raw config using public API logic
        raw = self._config.get_nested(config_type, config_name)

        if raw is None:
            raise ValueError(f"Configuration not found for '{config_type}.{config_name}'")

        if remove_meta_keys:
            # Shallow copy to remove meta keys safely
            clean = raw.copy()
            clean.pop('overwrite_from_env', None)
            clean.pop('fallbacks_from_env', None)
            return clean

        return raw

    async def _compute_auth_internal(
        self,
        config_type: str,
        config_name: str,
        include_headers: bool = False,
        request: Any = None
    ) -> Dict[str, Any]:
        logger.debug(f"compute_auth_internal type={config_type} name={config_name}")
        
        raw_config = self._get_raw_config(config_type, config_name, remove_meta_keys=False)
        
        auth_config = await self._fetch_auth_config_fn(config_name, raw_config, request)
        
        result = {"auth_config": auth_config}

        if include_headers:
            creds = {}
            if auth_config.username: creds['username'] = auth_config.username
            if auth_config.password: creds['password'] = auth_config.password
            if auth_config.email: creds['email'] = auth_config.email
            if auth_config.token: creds['token'] = auth_config.token
            if auth_config.header_name: creds['header_key'] = auth_config.header_name
            if auth_config.header_value: creds['header_value'] = auth_config.header_value

            headers = self._encode_auth_fn(
                auth_config.type.value if hasattr(auth_config.type, 'value') else str(auth_config.type), 
                **creds
            )
            result['headers'] = headers

        return result
