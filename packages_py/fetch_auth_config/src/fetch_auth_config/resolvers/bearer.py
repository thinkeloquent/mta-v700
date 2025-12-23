from ..types.auth_config import AuthConfig, AuthResolutionMeta
from ..types.auth_type import AuthType
from ..types.token_resolver import TokenResolverType
from ..errors import MissingCredentialError
from ..resolution.config_extractor import ProviderEnvMappings
from ..resolution.env_resolver import resolve_env_var_chain

def resolve_bearer_auth(
    provider_name: str,
    env_mappings: ProviderEnvMappings,
    auth_type: AuthType
) -> AuthConfig:
    token_result = resolve_env_var_chain(
        primary=env_mappings.api_key.primary,
        overwrite=env_mappings.api_key.overwrite,
        fallbacks=env_mappings.api_key.fallbacks
    )

    if not token_result.value:
        raise MissingCredentialError(
            provider_name,
            'token',
            token_result.tried
        )

    return AuthConfig(
        type=auth_type,
        provider_name=provider_name,
        token=token_result.value,
        header_name="Authorization",
        resolution=AuthResolutionMeta(
            resolved_from={'token': token_result.source},
            token_resolver=TokenResolverType.STATIC,
            is_placeholder=False
        )
    )
