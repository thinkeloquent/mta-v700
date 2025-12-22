
import pytest
import os
from unittest.mock import patch, MagicMock
from app_yaml_config import AppYamlConfig, get_service, ServiceConfig, ServiceNotFoundError

@pytest.fixture
def config_instance():
    """Mock the AppYamlConfig singleton."""
    mock_instance = MagicMock(spec=AppYamlConfig)
    
    # Mock get methods
    mock_instance.get.return_value = {}
    
    # Patch the singleton accessor
    with patch.object(AppYamlConfig, 'get_instance', return_value=mock_instance):
        yield mock_instance

def setup_mock_data(mock_instance, data):
    """Helper to set up mock return values."""
    def side_effect(key, default=None):
        return data.get(key, default)
    mock_instance.get.side_effect = side_effect

# TC-013-001: Basic service retrieval
def test_basic_service_retrieval(config_instance):
    data = {
        "services": {
            "test_service": {
                "api_version": "v1",
                "headers": {"X-Test": "true"}
            }
        }
    }
    setup_mock_data(config_instance, data)
    
    result = get_service("test_service")
    
    assert result.name == "test_service"
    assert result.config["api_version"] == "v1"
    assert result.config["headers"]["X-Test"] == "true"
    assert result.env_overwrites == []
    assert result.resolution_sources == {}

# TC-013-002: Unknown service throws error
def test_unknown_service_error(config_instance):
    setup_mock_data(config_instance, {"services": {}})
    
    with pytest.raises(ServiceNotFoundError):
        get_service("unknown_service")

# TC-013-003: List services
def test_list_services(config_instance):
    data = {
        "services": {
            "service_a": {},
            "service_b": {}
        }
    }
    setup_mock_data(config_instance, data)
    
    sc = ServiceConfig()
    services = sc.list_services()
    
    assert len(services) == 2
    assert "service_a" in services
    assert "service_b" in services

# TC-013-004/005: Has service
def test_has_service(config_instance):
    data = {
        "services": {
            "existing": {}
        }
    }
    setup_mock_data(config_instance, data)
    
    sc = ServiceConfig()
    assert sc.has_service("existing") is True
    assert sc.has_service("missing") is False

# TC-013-010/011: Single string overwrite
def test_single_string_overwrite(config_instance):
    data = {
        "services": {
            "test_service": {
                "key": None,
                "overwrite_from_env": {
                    "key": "TEST_VAR"
                }
            }
        }
    }
    setup_mock_data(config_instance, data)
    
    # Case 1: Found
    with patch.dict(os.environ, {"TEST_VAR": "env_value"}):
        result = get_service("test_service")
        assert result.config["key"] == "env_value"
        assert result.env_overwrites == ["key"]
        assert result.resolution_sources["key"]["source"] == "overwrite"
        assert result.resolution_sources["key"]["env_var"] == "TEST_VAR"

    # Case 2: Not found
    with patch.dict(os.environ):
        if "TEST_VAR" in os.environ: del os.environ["TEST_VAR"]
        result = get_service("test_service")
        assert result.config["key"] is None
        assert result.env_overwrites == []

# TC-013-012/013/014: Array overwrite
def test_array_overwrite(config_instance):
    data = {
        "services": {
            "test_service": {
                "key": None,
                "overwrite_from_env": {
                    "key": ["VAR1", "VAR2"]
                }
            }
        }
    }
    setup_mock_data(config_instance, data)
    
    # Case 1: First found
    with patch.dict(os.environ, {"VAR1": "val1", "VAR2": "val2"}):
        result = get_service("test_service")
        assert result.config["key"] == "val1"
        assert result.resolution_sources["key"]["env_var"] == "VAR1"

    # Case 2: Second found
    with patch.dict(os.environ, {"VAR2": "val2"}):
        with patch.dict(os.environ):
            if "VAR1" in os.environ: del os.environ["VAR1"]
            result = get_service("test_service")
            assert result.config["key"] == "val2"
            assert result.resolution_sources["key"]["env_var"] == "VAR2"

# TC-013-020: Fallback used
def test_fallback_usage(config_instance):
    data = {
        "services": {
            "test_service": {
                "key": None,
                "overwrite_from_env": {
                    "key": "PRIMARY"
                },
                "fallbacks_from_env": {
                    "key": ["FB1", "FB2"]
                }
            }
        }
    }
    setup_mock_data(config_instance, data)
    
    # Primary not set, FB1 set
    with patch.dict(os.environ, {"FB1": "fb_val"}):
        with patch.dict(os.environ):
            if "PRIMARY" in os.environ: del os.environ["PRIMARY"]
            
            result = get_service("test_service")
            assert result.config["key"] == "fb_val"
            assert result.resolution_sources["key"]["source"] == "fallback"
            assert result.resolution_sources["key"]["env_var"] == "FB1"

# TC-013-042: Meta keys removed
def test_meta_keys_removed(config_instance):
    data = {
        "services": {
            "test_service": {
                "key": None,
                "overwrite_from_env": {},
                "fallbacks_from_env": {}
            }
        }
    }
    setup_mock_data(config_instance, data)
    
    result = get_service("test_service")
    assert "overwrite_from_env" not in result.config
    assert "fallbacks_from_env" not in result.config
