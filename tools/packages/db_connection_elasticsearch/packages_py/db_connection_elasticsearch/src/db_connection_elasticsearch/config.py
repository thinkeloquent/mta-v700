import os
import base64
import json
import logging
import ssl
from typing import Any, Dict, Optional, Tuple, Union
from dataclasses import dataclass, field

from .constants import (
    VENDOR_ON_PREM,
    VENDOR_ELASTIC_CLOUD,
    VENDOR_ELASTIC_TRANSPORT,
    VENDOR_DIGITAL_OCEAN,
    VALID_VENDORS,
    VENDOR_DEFAULT_PORTS,
    TLS_PORTS,
)

logger = logging.getLogger(__name__)

class ElasticsearchConfigError(ValueError):
    """Invalid configuration values."""
    pass

@dataclass
class ElasticsearchConfig:
    """Elasticsearch configuration with multi-source resolution."""
    vendor_type: str = VENDOR_ON_PREM
    host: str = "localhost"
    port: int = 9200
    scheme: str = "https"
    cloud_id: Optional[str] = None
    api_key: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    api_auth_type: Optional[str] = None
    use_tls: bool = False
    verify_certs: bool = False
    ssl_show_warn: bool = False
    ca_certs: Optional[str] = None
    client_cert: Optional[str] = None
    client_key: Optional[str] = None
    index: Optional[str] = None
    verify_cluster_connection: bool = False
    request_timeout: float = 30.0
    connect_timeout: float = 10.0
    max_retries: int = 3
    retry_on_timeout: bool = True

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        vendor_type: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        scheme: Optional[str] = None,
        cloud_id: Optional[str] = None,
        api_key: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        api_auth_type: Optional[str] = None,
        use_tls: Optional[bool] = None,
        verify_certs: Optional[bool] = None,
        ssl_show_warn: Optional[bool] = None,
        ca_certs: Optional[str] = None,
        client_cert: Optional[str] = None,
        client_key: Optional[str] = None,
        index: Optional[str] = None,
        verify_cluster_connection: Optional[bool] = None,
        request_timeout: Optional[float] = None,
        connect_timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        retry_on_timeout: Optional[bool] = None,
    ):
        # 1. Initialize with defaults or provided args
        self.vendor_type = vendor_type
        self.host = host
        self.port = port
        self.scheme = scheme
        self.cloud_id = cloud_id
        self.api_key = api_key
        self.username = username
        self.password = password
        self.api_auth_type = api_auth_type
        self.use_tls = use_tls
        self.verify_certs = verify_certs
        self.ssl_show_warn = ssl_show_warn
        self.ca_certs = ca_certs
        self.client_cert = client_cert
        self.client_key = client_key
        self.index = index
        self.verify_cluster_connection = verify_cluster_connection
        self.request_timeout = request_timeout
        self.connect_timeout = connect_timeout
        self.max_retries = max_retries
        self.retry_on_timeout = retry_on_timeout

        # 2. Merge dictionary config if provided (overrides defaults, overridden by explicit args?
        # Usually config dict is lower priority than explicit args for the same field, but higher than defaults)
        # Implementing Priority: Args > Env > Config Dict > Defaults
        # But here logic is tricky. Let's simplify:
        # We start with empty/None, fill from Env, then Config, then Args.
        
        # Actually, let's use a helper to resolve values
        self._resolve_configuration(config)
        
        # 3. Post-resolution validation
        self._validate()

    def _resolve_configuration(self, config_dict: Optional[Dict[str, Any]]) -> None:
        """Resolve configuration from multiple sources."""
        
        # Helper to get value from sources
        def get_val(field_name: str, arg_val: Any, default: Any, target_type: type = str) -> Any:
            # 1. Argument
            if arg_val is not None:
                return arg_val
            
            # 2. Env Var
            env_key = f"ELASTIC_DB_{field_name.upper()}"
            env_val = os.getenv(env_key)
            if env_val is not None:
                if target_type == bool:
                    return env_val.lower() in ('true', '1', 'yes')
                if target_type == int:
                    try:
                        return int(env_val)
                    except ValueError:
                        pass
                if target_type == float:
                    try:
                        return float(env_val)
                    except ValueError:
                        pass
                return env_val
                
            # 3. Config Dict
            if config_dict and field_name in config_dict:
                return config_dict[field_name]
                
            # 4. Default
            return default

        self.vendor_type = get_val("vendor_type", self.vendor_type, VENDOR_ON_PREM)
        self.host = get_val("host", self.host, "localhost")
        self.port = get_val("port", self.port, 9200, int)
        self.scheme = get_val("scheme", self.scheme, "https")
        self.cloud_id = get_val("cloud_id", self.cloud_id, None)
        self.api_key = get_val("api_key", self.api_key, None)
        self.username = get_val("username", self.username, None)
        # Password can come from ELASTIC_DB_PASSWORD or ELASTIC_DB_ACCESS_KEY (DigitalOcean uses ACCESS_KEY)
        self.password = get_val("password", self.password, None)
        if self.password is None:
            self.password = os.getenv("ELASTIC_DB_ACCESS_KEY")
        self.api_auth_type = get_val("api_auth_type", self.api_auth_type, None)
        self.use_tls = get_val("use_tls", self.use_tls, False, bool)
        self.verify_certs = get_val("verify_certs", self.verify_certs, False, bool)
        self.ssl_show_warn = get_val("ssl_show_warn", self.ssl_show_warn, False, bool)
        self.ca_certs = get_val("ca_certs", self.ca_certs, None)
        self.client_cert = get_val("client_cert", self.client_cert, None)
        self.client_key = get_val("client_key", self.client_key, None)
        self.index = get_val("index", self.index, None)
        self.verify_cluster_connection = get_val("verify_cluster_connection", self.verify_cluster_connection, False, bool)
        self.request_timeout = get_val("request_timeout", self.request_timeout, 30.0, float)
        self.connect_timeout = get_val("connect_timeout", self.connect_timeout, 10.0, float)
        self.max_retries = get_val("max_retries", self.max_retries, 3, int)
        self.retry_on_timeout = get_val("retry_on_timeout", self.retry_on_timeout, True, bool)

        # Auto-detect logic
        self._detect_vendor()
        
    def _detect_vendor(self) -> None:
        """Auto-detect vendor type based on config."""
        if self.cloud_id:
            self.vendor_type = VENDOR_ELASTIC_CLOUD
        elif self.host and (
            "ondigitalocean.com" in self.host or
            "digitaloceanspaces" in self.host or
            self.port == 25060
        ):
            self.vendor_type = VENDOR_DIGITAL_OCEAN
        elif self.vendor_type not in VALID_VENDORS:
            # Default fallback if not detected clearly, though validation catches this later
            pass
    
    def _validate(self) -> None:
        """Validate configuration."""
        if self.vendor_type not in VALID_VENDORS:
            raise ElasticsearchConfigError(f"Invalid vendor_type: {self.vendor_type}. Must be one of {VALID_VENDORS}")
        
        if self.port < 1 or self.port > 65535:
            raise ElasticsearchConfigError("Port must be between 1 and 65535")

    def parse_cloud_id(self) -> Tuple[str, Optional[str]]:
        """Parse Elastic Cloud ID to extract hosts."""
        if not self.cloud_id:
             raise ElasticsearchConfigError("cloud_id is not set")
        
        try:
            # Format is usually 'Deployment_Name:base64(...)'
            if ":" in self.cloud_id:
                _, cloud_id_b64 = self.cloud_id.split(":", 1)
            else:
                cloud_id_b64 = self.cloud_id
                
            decoded = base64.b64decode(cloud_id_b64).decode("utf-8")
            parts = decoded.split("$")
            
            # parts[0] is often empty or host suffix?
            # Standard format: host_identifier$es_id$kibana_id
            # Wait, let's check standard impl.
            # Example: "monorail:dXMtY2VudHJhbDEuZ2NwLmNsb3VkLmVzLmlvOjQ0MyQ0ZmE4OD..."
            # Decoded: "us-central1.gcp.cloud.es.io:443$4fa88...$..."
            # So: domain_and_port $ es_uuid $ kibana_uuid
            
            if len(parts) < 2:
                 raise ElasticsearchConfigError("Invalid Cloud ID format")
            
            domain_port = parts[0]
            if ":" in domain_port:
                domain, port = domain_port.rsplit(":", 1)
            else:
                 domain = domain_port
            
            es_uuid = parts[1]
            es_host = f"{es_uuid}.{domain}"
            
            kibana_host = None
            if len(parts) > 2 and parts[2]:
                kibana_uuid = parts[2]
                kibana_host = f"{kibana_uuid}.{domain}"
                
            return es_host, kibana_host
            
        except Exception as e:
            logger.error(f"Failed to parse cloud_id: {e}")
            raise ElasticsearchConfigError(f"Failed to parse cloud_id: {e}")

    def get_api_key(self) -> Optional[str]:
        """Get API key."""
        return self.api_key

    def get_base_url(self) -> str:
        """Get base URL."""
        if self.vendor_type == VENDOR_ELASTIC_CLOUD and self.cloud_id:
            # Cloud uses cloud_id, usually clients handle it.
            # But if we need a URL:
             es_host, _ = self.parse_cloud_id()
             return f"https://{es_host}:443"
        
        host = self.host if self.host else "localhost"
        return f"{self.scheme}://{host}:{self.port}"

    def get_url_with_index(self) -> str:
        """Get URL inclusive of index."""
        base = self.get_base_url()
        if self.index:
            return f"{base}/{self.index}"
        return base

    def get_ssl_config(self) -> Dict[str, Any]:
        """Get SSL configuration for client (elasticsearch-py 8.x)."""
        ssl_config = {}
        # Note: elasticsearch-py 8.x infers SSL from URL scheme (https://)
        # No 'use_ssl' parameter needed
        if self.use_tls or self.scheme == 'https':
            ssl_config['verify_certs'] = self.verify_certs
            ssl_config['ssl_show_warn'] = self.ssl_show_warn

            if self.ca_certs:
                ssl_config['ca_certs'] = self.ca_certs

            if self.client_cert:
                ssl_config['client_cert'] = self.client_cert

            if self.client_key:
                ssl_config['client_key'] = self.client_key

        return ssl_config

    def get_connection_kwargs(self) -> Dict[str, Any]:
        """Get connection options for AsyncElasticsearch."""
        kwargs: Dict[str, Any] = {
            "request_timeout": self.request_timeout,
            "max_retries": self.max_retries,
            "retry_on_timeout": self.retry_on_timeout,
        }

        # Authentication
        # DigitalOcean OpenSearch uses basic auth, not API keys
        if self.vendor_type == VENDOR_DIGITAL_OCEAN:
            if self.username and self.password:
                kwargs["basic_auth"] = (self.username, self.password)
        elif self.api_key:
            # Elasticsearch Cloud API key auth
            kwargs["api_key"] = self.api_key
        elif self.username and self.password:
            kwargs["basic_auth"] = (self.username, self.password)

        # SSL
        kwargs.update(self.get_ssl_config())

        # Vendor Specifics
        if self.vendor_type == VENDOR_ELASTIC_CLOUD and self.cloud_id:
            kwargs["cloud_id"] = self.cloud_id
        else:
            kwargs["hosts"] = [self.get_base_url()]

        return kwargs

    def get_transport_kwargs(self) -> Dict[str, Any]:
         """Get transport kwargs."""
         # Similar to connection kwargs but specifically for Transport layer checks if needed.
         return self.get_connection_kwargs()

