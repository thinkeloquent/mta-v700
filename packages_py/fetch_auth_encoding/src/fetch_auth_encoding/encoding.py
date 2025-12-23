import base64
from typing import Dict, Optional, Any, List

# --- Sensitive Data Property Helpers (Inlined) ---

USERNAME_KEYS = ['username', 'user', 'login', 'id', 'email', 'user_id', 'userId']
PASSWORD_KEYS = ['password', 'pwd', 'pass', 'secret', 'token', 'credential', 'access_token', 'accessToken']
API_KEY_KEYS = ['api_key', 'apiKey', 'access_key', 'accessKey', 'auth_token', 'authToken', 'token', 'rawApiKey', 'raw_api_key', 'key']

def _get_value_from_keys(obj: Any, keys: List[str]) -> Any:
    """Generic getter to find a value in an object (dict or object) based on a list of potential keys."""
    if obj is None:
        return None
        
    if isinstance(obj, dict):
        for key in keys:
            if key in obj:
                return obj[key]
                
    for key in keys:
        if hasattr(obj, key):
            val = getattr(obj, key)
            if val is not None:
                return val
    return None

def get_username(obj: Any) -> Any:
    return _get_value_from_keys(obj, USERNAME_KEYS)

def get_password(obj: Any) -> Any:
    return _get_value_from_keys(obj, PASSWORD_KEYS)

def get_api_key(obj: Any) -> Any:
    return _get_value_from_keys(obj, API_KEY_KEYS)

def _base64_encode(text: str) -> str:
    """Encodes a string to base64."""
    return base64.b64encode(text.encode("utf-8")).decode("utf-8")

def encode_auth(auth_type: str, **kwargs: Any) -> Dict[str, str]:
    """
    Encodes authentication credentials into HTTP headers based on the auth type.
    
    Args:
        auth_type: The type of authentication (e.g., 'basic', 'bearer', 'x-api-key').
        **kwargs: credentials like username, password, email, token, header_key, header_value.
        
    Returns:
        A dictionary containing the HTTP headers.
    """
    auth_type = auth_type.lower()
    
    # Extract common credentials using the utility library
    username = get_username(kwargs)
    password = get_password(kwargs)
    api_token_value = get_api_key(kwargs) or kwargs.get("token")
    
    # --- Basic Auth Family ---
    if auth_type == "basic":
        user_part = username
        secret_part = password or api_token_value
        
        if not user_part or not secret_part:
            raise ValueError("Basic auth requires username/email and password/token")
            
        credentials = f"{user_part}:{secret_part}"
        return {"Authorization": f"Basic {_base64_encode(credentials)}"}

    if auth_type == "basic_email_token":
        if not username or not (password or api_token_value): 
            raise ValueError("basic_email_token requires email and token")
        return {"Authorization": f"Basic {_base64_encode(f'{username}:{password or api_token_value}')}"}

    if auth_type == "basic_token":
        if not username or not (password or api_token_value): 
            raise ValueError("basic_token requires username and token")
        return {"Authorization": f"Basic {_base64_encode(f'{username}:{password or api_token_value}')}"}

    if auth_type == "basic_email":
        if not username or not password: 
            raise ValueError("basic_email requires email and password")
        return {"Authorization": f"Basic {_base64_encode(f'{username}:{password}')}"}

    # --- Bearer Auth Family ---
    
    if auth_type in ["bearer", "bearer_oauth", "bearer_jwt"]:
        val = api_token_value or password
        if not val: 
            raise ValueError(f"{auth_type} requires token")
        return {"Authorization": f"Bearer {val}"}

    if auth_type == "bearer_username_token":
        if not username or not (password or api_token_value): 
            raise ValueError("bearer_username_token requires username and token")
        return {"Authorization": f"Bearer {_base64_encode(f'{username}:{password or api_token_value}')}"}

    if auth_type == "bearer_username_password":
        if not username or not password: 
            raise ValueError("bearer_username_password requires username and password")
        return {"Authorization": f"Bearer {_base64_encode(f'{username}:{password}')}"}

    if auth_type == "bearer_email_token":
        if not username or not (password or api_token_value): 
            raise ValueError("bearer_email_token requires email and token")
        return {"Authorization": f"Bearer {_base64_encode(f'{username}:{password or api_token_value}')}"}

    if auth_type == "bearer_email_password":
        if not username or not password: 
            raise ValueError("bearer_email_password requires email and password")
        return {"Authorization": f"Bearer {_base64_encode(f'{username}:{password}')}"}

    # --- Custom/API Key ---

    if auth_type == "x-api-key":
        # Format: X-API-Key: <raw_api_key>
        val = api_token_value or kwargs.get("value")
        if not val: 
            raise ValueError("x-api-key requires token/value")
        return {"X-API-Key": val}

    if auth_type in ["custom", "custom_header"]:
        key = kwargs.get("header_key")
        val = kwargs.get("header_value") or api_token_value or kwargs.get("value")
        if not key: 
            raise ValueError(f"{auth_type} requires header_key")
        return {key: val or ""}

    # --- HMAC (Stub) ---
    if auth_type == "hmac":
        raise NotImplementedError("HMAC auth not yet fully implemented")

    if auth_type == "none":
        return {}

    raise ValueError(f"Unsupported auth type: {auth_type}")

