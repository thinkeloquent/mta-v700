
import pytest
import os
from unittest.mock import MagicMock, patch
from app_yaml_config.get_provider.provider_config import ProviderConfig

@pytest.fixture
def config_instance():
    mock_config = MagicMock()
    def deep_merge(target, source):
        target.update(source)
        return target
    mock_config._deep_merge.side_effect = deep_merge
    return mock_config

def setup_mock_data(mock_config, data):
    def get_side_effect(key, default=None):
        return data.get(key, default)
    mock_config.get.side_effect = get_side_effect

def test_overwrite_from_env_array(config_instance):
    """Test overwrite_from_env with array of variables."""
    data = {
        "global": {},
        "providers": {
            "test_provider": {
                "api_key": None,
                "overwrite_from_env": {
                    "api_key": ["PRIMARY_KEY", "SECONDARY_KEY"]
                }
            }
        }
    }
    setup_mock_data(config_instance, data)

    # Case 1: Primary key exists
    with patch.dict(os.environ, {"PRIMARY_KEY": "primary_val", "SECONDARY_KEY": "secondary_val"}):
        provider_config = ProviderConfig(config_instance)
        result = provider_config.get("test_provider")
        assert result.config["api_key"] == "primary_val"
        assert result.env_overwrites == ["api_key"]
        assert result.resolution_sources["api_key"].source == "overwrite"
        assert result.resolution_sources["api_key"].env_var == "PRIMARY_KEY"

    # Case 2: Only secondary key exists
    with patch.dict(os.environ, {"SECONDARY_KEY": "secondary_val"}):
        # Ensure PRIMARY_KEY is NOT set
        with patch.dict(os.environ):
            if "PRIMARY_KEY" in os.environ:
                del os.environ["PRIMARY_KEY"]
                
            provider_config = ProviderConfig(config_instance)
            result = provider_config.get("test_provider")
            assert result.config["api_key"] == "secondary_val"
            assert result.env_overwrites == ["api_key"]
            assert result.resolution_sources["api_key"].source == "overwrite"
            assert result.resolution_sources["api_key"].env_var == "SECONDARY_KEY"

def test_fallbacks_from_env(config_instance):
    """Test fallbacks_from_env logic."""
    data = {
        "global": {},
        "providers": {
            "test_provider": {
                "api_key": None,
                "overwrite_from_env": {
                    "api_key": "PRIMARY_KEY"
                },
                "fallbacks_from_env": {
                    "api_key": ["FALLBACK_KEY_1", "FALLBACK_KEY_2"]
                }
            }
        }
    }
    setup_mock_data(config_instance, data)

    # Case 1: Primary overwrite exists (Fallback ignored)
    with patch.dict(os.environ, {"PRIMARY_KEY": "primary_val", "FALLBACK_KEY_1": "fallback_val"}):
        provider_config = ProviderConfig(config_instance)
        result = provider_config.get("test_provider")
        assert result.config["api_key"] == "primary_val"
        assert result.env_overwrites == ["api_key"]
        assert result.resolution_sources["api_key"].source == "overwrite"

    # Case 2: Primary missing, Fallback 1 exists
    with patch.dict(os.environ, {"FALLBACK_KEY_1": "fallback_val_1"}):
        with patch.dict(os.environ):
            if "PRIMARY_KEY" in os.environ: del os.environ["PRIMARY_KEY"]
            
            provider_config = ProviderConfig(config_instance)
            result = provider_config.get("test_provider")
            assert result.config["api_key"] == "fallback_val_1"
            assert result.env_overwrites == ["api_key"]
            assert result.resolution_sources["api_key"].source == "fallback"

    # Case 3: Primary missing, Fallback 1 missing, Fallback 2 exists
    with patch.dict(os.environ, {"FALLBACK_KEY_2": "fallback_val_2"}):
        with patch.dict(os.environ):
            if "PRIMARY_KEY" in os.environ: del os.environ["PRIMARY_KEY"]
            if "FALLBACK_KEY_1" in os.environ: del os.environ["FALLBACK_KEY_1"]

            provider_config = ProviderConfig(config_instance)
            result = provider_config.get("test_provider")
            assert result.config["api_key"] == "fallback_val_2"
            assert result.env_overwrites == ["api_key"]
            assert result.resolution_sources["api_key"].source == "fallback"

def test_mixed_config(config_instance):
    """Test mixed configuration with existing values."""
    data = {
        "global": {},
        "providers": {
            "test_provider": {
                "existing_key": "static_value",
                "missing_key": None,
                "overwrite_from_env": {
                    "existing_key": "ENV_VAR_1",
                    "missing_key": "ENV_VAR_2"
                }
            }
        }
    }
    setup_mock_data(config_instance, data)

    with patch.dict(os.environ, {"ENV_VAR_1": "should_be_ignored", "ENV_VAR_2": "used_value"}):
        provider_config = ProviderConfig(config_instance)
        result = provider_config.get("test_provider")
        
        # Existing key should NOT be overwritten (not None)
        assert result.config["existing_key"] == "static_value"
        # Missing key SHOULD be overwritten
        assert result.config["missing_key"] == "used_value"
        
        assert "missing_key" in result.env_overwrites
        assert "existing_key" not in result.env_overwrites

