from .auth_type import AuthType

AUTH_TYPE_REQUIREMENTS = {
    AuthType.BASIC: {
        "required": ["username", "password"],
        "optional": [],
        "header_name": "Authorization"
    },
    AuthType.BASIC_EMAIL_TOKEN: {
        "required": ["email", "token"],
        "optional": [],
        "header_name": "Authorization"
    },
    AuthType.BASIC_TOKEN: {
        "required": ["username", "token"],
        "optional": [],
        "header_name": "Authorization"
    },
    AuthType.BASIC_EMAIL: {
        "required": ["email", "password"],
        "optional": [],
        "header_name": "Authorization"
    },
    AuthType.BEARER: {
        "required": ["token"],
        "optional": [],
        "header_name": "Authorization"
    },
    AuthType.BEARER_OAUTH: {
        "required": ["token"],
        "optional": [],
        "header_name": "Authorization"
    },
    AuthType.BEARER_JWT: {
        "required": ["token"],
        "optional": [],
        "header_name": "Authorization"
    },
    AuthType.BEARER_USERNAME_TOKEN: {
        "required": ["username", "token"],
        "optional": [],
        "header_name": "Authorization"
    },
    AuthType.BEARER_USERNAME_PASSWORD: {
        "required": ["username", "password"],
        "optional": [],
        "header_name": "Authorization"
    },
    AuthType.BEARER_EMAIL_TOKEN: {
        "required": ["email", "token"],
        "optional": [],
        "header_name": "Authorization"
    },
    AuthType.BEARER_EMAIL_PASSWORD: {
        "required": ["email", "password"],
        "optional": [],
        "header_name": "Authorization"
    },
    AuthType.X_API_KEY: {
        "required": ["token"],
        "optional": [],
        "header_name": "X-API-Key"
    },
    AuthType.CUSTOM: {
        "required": ["token", "header_name"],
        "optional": [],
        "header_name": None # dynamic
    },
    AuthType.CUSTOM_HEADER: {
        "required": ["token", "header_name"],
        "optional": [],
        "header_name": None # dynamic
    },
    AuthType.EDGEGRID: {
        "required": ["client_token", "client_secret", "access_token", "base_url"],
        "optional": ["headers_to_sign"],
        "header_name": "Authorization"
    },
    AuthType.NONE: {
        "required": [],
        "optional": [],
        "header_name": None
    }
}
