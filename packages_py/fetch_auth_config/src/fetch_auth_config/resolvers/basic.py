from ..types.auth_config import AuthConfig, AuthResolutionMeta
from ..types.auth_type import AuthType
from ..types.token_resolver import TokenResolverType
from ..errors import MissingCredentialError
from ..resolution.config_extractor import ProviderEnvMappings
from ..resolution.env_resolver import resolve_env_var_chain

def resolve_basic_auth(
    provider_name: str,
    env_mappings: ProviderEnvMappings,
    auth_type: AuthType
) -> AuthConfig:
    resolved_from = {}
    
    # Username/Email resolution
    username = None
    email = None
    
    if auth_type in [AuthType.BASIC, AuthType.BASIC_TOKEN, AuthType.BASIC_EMAIL, AuthType.BASIC_EMAIL_TOKEN]:
        # Needs username or email
        if auth_type in [AuthType.BASIC_EMAIL, AuthType.BASIC_EMAIL_TOKEN]:
             res = resolve_env_var_chain(primary=env_mappings.email.primary, overwrite=env_mappings.email.overwrite)
             if not res.value: raise MissingCredentialError(provider_name, 'email', res.tried)
             email = res.value
             resolved_from['email'] = res.source
        else:
             res = resolve_env_var_chain(primary=env_mappings.username.primary, overwrite=env_mappings.username.overwrite)
             if not res.value: raise MissingCredentialError(provider_name, 'username', res.tried)
             username = res.value
             resolved_from['username'] = res.source

    # Password/Token resolution
    password = None
    token = None
    
    if auth_type in [AuthType.BASIC, AuthType.BASIC_EMAIL]:
        res = resolve_env_var_chain(primary=env_mappings.password.primary, overwrite=env_mappings.password.overwrite)
        if not res.value: raise MissingCredentialError(provider_name, 'password', res.tried)
        password = res.value
        resolved_from['password'] = res.source
    elif auth_type in [AuthType.BASIC_TOKEN, AuthType.BASIC_EMAIL_TOKEN]:
        res = resolve_env_var_chain(primary=env_mappings.api_key.primary, overwrite=env_mappings.api_key.overwrite)
        if not res.value: raise MissingCredentialError(provider_name, 'token', res.tried)
        token = res.value
        resolved_from['token'] = res.source

    return AuthConfig(
        type=auth_type,
        provider_name=provider_name,
        username=username,
        email=email,
        password=password,
        token=token,
        header_name="Authorization",
        resolution=AuthResolutionMeta(
            resolved_from=resolved_from,
            token_resolver=TokenResolverType.STATIC,
            is_placeholder=False
        )
    )
