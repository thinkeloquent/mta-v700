"""
Tests for config and auth handlers.
"""
import base64
import pytest
from pydantic import ValidationError, SecretStr
from fetch_client.config import AuthConfig, ClientConfig, resolve_config
from fetch_client.auth.auth_handler import create_auth_handler, AuthHandler, CustomAuthHandler

def test_auth_config_validation_basic():
    """Test basic auth validation."""
    # Valid
    config = AuthConfig(type="basic", username="user", password=SecretStr("pass"))
    assert config.type == "basic"
    
    # Invalid (missing password)
    with pytest.raises(ValidationError) as exc:
        AuthConfig(type="basic", username="user")
    assert "Basic auth requires 'username' and 'password'" in str(exc.value)

def test_auth_config_validation_bearer_complex():
    """Test complex bearer validation."""
    # Valid
    config = AuthConfig(type="bearer_username_token", username="user", raw_api_key=SecretStr("key"))
    assert config.type == "bearer_username_token"
    
    # Invalid (missing key)
    with pytest.raises(ValidationError) as exc:
        AuthConfig(type="bearer_username_token", username="user")
    assert "bearer_username_token requires 'username' and 'raw_api_key'" in str(exc.value)

def test_auth_config_api_key_computation():
    """Test that api_key property correctly computes base64 values."""
    # Basic
    config = AuthConfig(type="basic", username="user", password=SecretStr("pass"))
    expected = base64.b64encode(b"user:pass").decode()
    assert config.api_key == expected
    
    # Bearer complex
    config = AuthConfig(type="bearer_username_token", username="user", raw_api_key=SecretStr("token"))
    expected = base64.b64encode(b"user:token").decode()
    assert config.api_key == expected

def test_create_auth_handler_basic():
    """Test factory creates correct handler for basic auth."""
    config = AuthConfig(type="basic", username="user", password=SecretStr("pass"))
    handler = create_auth_handler(config)
    
    assert isinstance(handler, CustomAuthHandler)
    # Check header generation
    # Context is not used for static creds in this mocked scenario
    headers = handler.get_header({}) 
    assert headers["Authorization"] == f"Basic {config.api_key}"

def test_create_auth_handler_bearer_complex():
    """Test factory creates correct handler for complex bearer."""
    config = AuthConfig(type="bearer_username_token", username="user", raw_api_key=SecretStr("token"))
    handler = create_auth_handler(config)
    
    assert isinstance(handler, CustomAuthHandler)
    headers = handler.get_header({})
    assert headers["Authorization"] == f"Bearer {config.api_key}"

def test_create_auth_handler_simple_bearer():
    """Test factory for simple bearer."""
    config = AuthConfig(type="bearer", raw_api_key=SecretStr("token"))
    handler = create_auth_handler(config)
    
    # Depending on implementation, might return BearerAuthHandler or CustomAuthHandler
    # But effectively verification passes if header is correct
    headers = handler.get_header({})
    assert headers["Authorization"] == "Bearer token"

def test_client_config_resolve():
    """Test resolution of client config."""
    config = ClientConfig(base_url="https://api.example.com", auth=AuthConfig(type="x-api-key", raw_api_key=SecretStr("key")))
    resolved = resolve_config(config)
    
    assert resolved.base_url == "https://api.example.com"
    assert resolved.timeout.connect == 5.0
    assert resolved.serializer is not None
