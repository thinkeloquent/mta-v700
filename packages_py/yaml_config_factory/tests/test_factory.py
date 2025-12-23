import pytest
from yaml_config_factory import YamlConfigFactory
from app_yaml_config import AppYamlConfig

class MockAppYamlConfig:
    def get_nested(self, config_type, config_name):
        if config_type == "providers" and config_name == "test_provider":
            return {
                "api_auth_type": "bearer",
                "env_api_key": "TEST_KEY"
            }
        return None

def test_compute_valid_path():
    config = MockAppYamlConfig()
    factory = YamlConfigFactory(config)
    
    # Mocking fetch_auth_config effectively by relying on its actual implementation 
    # but we need to control the inputs. 
    # Since we can't easily mock imports inside the factory module without patching,
    # we can pass mock functions to the constructor if we redesign factory dependency injection,
    # OR we just rely on fetch_auth_config working (integration test style) but we need to set env vars.
    # The factory accepts fn arguments!
    
    mock_auth_config = object() # just a marker
    
    def mock_fetch(name, conf):
        assert name == "test_provider"
        assert conf["api_auth_type"] == "bearer"
        # Return a dummy object with required attribs to pass the rest of logic if needed
        class DummyAuth:
            type = "bearer"
            username = None
            password = None
            email = None
            token = "resolved-token"
            header_name = "Authorization"
            header_value = "Bearer resolved-token" # simplistic
        return DummyAuth()

    factory = YamlConfigFactory(config, fetch_auth_config_fn=mock_fetch)
    
    result = factory.compute("providers.test_provider")
    assert "auth_config" in result
    assert result["auth_config"].token == "resolved-token"

def test_compute_invalid_path():
    config = MockAppYamlConfig()
    factory = YamlConfigFactory(config)
    
    with pytest.raises(ValueError, match="Invalid path format"):
        factory.compute("invalid")
        
    with pytest.raises(ValueError, match="Invalid config type"):
        factory.compute("invalid.name")

def test_include_headers():
    config = MockAppYamlConfig()
    
    def mock_fetch(name, conf):
        class DummyAuth:
            type = "bearer"
            username = None
            password = None
            email = None
            token = "xyz"
            header_name = None
            header_value = None
        return DummyAuth()

    def mock_encode(auth_type, **kwargs):
        return {"Authorization": "Bearer xyz"}

    factory = YamlConfigFactory(config, fetch_auth_config_fn=mock_fetch, encode_auth_fn=mock_encode)
    result = factory.compute("providers.test_provider", include_headers=True)
    
    assert "headers" in result
    assert result["headers"]["Authorization"] == "Bearer xyz"
