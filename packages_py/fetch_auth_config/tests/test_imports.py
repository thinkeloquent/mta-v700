from fetch_auth_config import fetch_auth_config, AuthType, AuthConfig

def test_imports():
    assert AuthType is not None
    assert AuthConfig is not None
    assert fetch_auth_config is not None

def test_auth_type_values():
    assert AuthType.BASIC == 'basic'
    assert AuthType.BEARER == 'bearer'
