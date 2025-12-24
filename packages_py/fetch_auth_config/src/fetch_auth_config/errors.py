from typing import List

class AuthConfigError(Exception):
    """Base exception for auth config resolution errors."""
    pass

class MissingCredentialError(AuthConfigError):
    def __init__(self, provider_name: str, credential_name: str, env_vars_tried: List[str]):
        msg = f"Missing credential '{credential_name}' for provider '{provider_name}'. Tried env vars: {', '.join(env_vars_tried)}"
        super().__init__(msg)
        self.provider_name = provider_name
        self.credential_name = credential_name
        self.env_vars_tried = env_vars_tried

class InvalidAuthTypeError(AuthConfigError):
    def __init__(self, provider_name: str, auth_type: str):
        msg = f"Invalid auth type '{auth_type}' for provider '{provider_name}'"
        super().__init__(msg)
        self.provider_name = provider_name
        self.auth_type = auth_type

class ProviderNotFoundError(AuthConfigError):
    pass

class ComputeFunctionNotFoundError(AuthConfigError):
    def __init__(self, provider_name: str, resolver_type: str):
        msg = f"No {resolver_type} compute function registered for provider '{provider_name}'"
        super().__init__(msg)
        self.provider_name = provider_name
        self.resolver_type = resolver_type

class ComputeFunctionError(AuthConfigError):
    def __init__(self, provider_name: str, cause: Exception):
        msg = f"Compute function failed for provider '{provider_name}': {str(cause)}"
        super().__init__(msg)
        self.provider_name = provider_name
        self.cause = cause
