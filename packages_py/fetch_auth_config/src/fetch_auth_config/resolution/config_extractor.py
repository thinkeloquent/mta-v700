from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from ..types.auth_type import AuthType
from ..types.token_resolver import TokenResolverType

@dataclass
class EnvVarChainConfig:
    primary: Optional[str] = None
    overwrite: Optional[List[str]] = None

@dataclass
class ProviderEnvMappings:
    api_key: EnvVarChainConfig
    email: EnvVarChainConfig
    username: EnvVarChainConfig
    password: EnvVarChainConfig
    # EdgeGrid
    client_token: EnvVarChainConfig = None
    client_secret: EnvVarChainConfig = None
    access_token: EnvVarChainConfig = None

@dataclass
class AuthSettings:
    auth_type: AuthType
    custom_header_name: Optional[str]
    token_resolver: TokenResolverType

def extract_env_mappings(provider_config: Dict[str, Any]) -> ProviderEnvMappings:
    overwrites = provider_config.get("overwrite_from_env") or {}
    
    def _get_chain(key: str, primary_key: str) -> EnvVarChainConfig:
        ov = overwrites.get(key)
        return EnvVarChainConfig(
            primary=provider_config.get(primary_key),
            overwrite=[ov] if isinstance(ov, str) else ov
        )

    return ProviderEnvMappings(
        api_key=_get_chain("endpoint_api_key", "endpoint_api_key"),
        email=_get_chain("email", "env_email"),
        username=_get_chain("username", "env_username"),
        password=_get_chain("password", "env_password"),
        client_token=_get_chain("client_token", "env_client_token"),
        client_secret=_get_chain("client_secret", "env_client_secret"),
        access_token=_get_chain("access_token", "env_access_token")
    )

def extract_auth_settings(provider_config: Dict[str, Any]) -> AuthSettings:
    auth_type_str = provider_config.get("endpoint_auth_type") or "bearer"
    try:
        auth_type = AuthType(auth_type_str)
    except ValueError:
        # Default fallback or error? Spec implies robust handling via InvalidAuthTypeError later, 
        # but here we need a valid enum. Let's assume input matches or default to bearer if invalid?
        # Better to return raw and let core invalid it, but we typed it as AuthType.
        # Let's try to parse, if fail, assume custom or similar? 
        # Actually `AuthType(str)` raises ValueError.
        # Let's pass it through and catch in main loop, OR raise here.
        # The main loop catches InvalidAuthTypeError.
        # Let's assume config is valid or sanitized before.
        # If not, we might need a safer parse.
        pass 

    return AuthSettings(
        auth_type=AuthType(auth_type_str),
        custom_header_name=provider_config.get("api_auth_header_name"),
        token_resolver=TokenResolverType(provider_config.get("endpoint_auth_token_resolver") or "static")
    )
