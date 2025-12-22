
import os
import pytest
from unittest.mock import patch, MagicMock
from app_yaml_config import AppYamlConfig, StorageNotFoundError, get_storage, StorageConfig, StorageOptions

@pytest.fixture
def mock_config():
    with patch('app_yaml_config.AppYamlConfig.get_instance') as mock_get_instance:
        instance = MagicMock()
        mock_get_instance.return_value = instance
        
        # Setup mock data with various scenarios
        instance.get.return_value = {
            "redis": {
                "host": "localhost",
                "port": 6379
            },
            "redis_env": {
                "host": None,
                "env_host_key": "REDIS_HOST",
                "port": None,
                "env_port_key": "REDIS_PORT"
            },
            "redis_fallback": {
                "host": None,
                "env_host_key": "PRIMARY_HOST",
                "env_host_key_fallbacks": ["FALLBACK_HOST_1", "FALLBACK_HOST_2"]
            },
            "mixed": {
                "host": "explicit_host", # Should not be overwritten
                "env_host_key": "REDIS_HOST",
                "port": None,
                "env_port_key": "REDIS_PORT"
            }
        }
        yield instance

class TestStorageConfig:
    
    def test_basic_retrieval(self, mock_config):
        storage = get_storage("redis")
        assert storage.name == "redis"
        assert storage.config["host"] == "localhost"
        assert storage.config["port"] == 6379
        assert len(storage.env_overwrites) == 0

    def test_storage_not_found(self, mock_config):
        with pytest.raises(StorageNotFoundError):
            get_storage("unknown")

    def test_list_storages(self, mock_config):
        sc = StorageConfig()
        storages = sc.list_storages()
        assert "redis" in storages
        assert "redis_env" in storages
        assert len(storages) == 4

    def test_has_storage(self, mock_config):
        sc = StorageConfig()
        assert sc.has_storage("redis") is True
        assert sc.has_storage("unknown") is False

    def test_env_overwrite_primary(self, mock_config):
        with patch.dict(os.environ, {"REDIS_HOST": "env_host", "REDIS_PORT": "6380"}):
            storage = get_storage("redis_env")
            assert storage.config["host"] == "env_host"
            assert storage.config["port"] == "6380"
            assert "host" in storage.env_overwrites
            assert "port" in storage.env_overwrites
            assert storage.resolution_sources["host"].source == "overwrite"
            assert storage.resolution_sources["host"].env_var == "REDIS_HOST"

    def test_env_overwrite_fallback(self, mock_config):
        # Primary missing, first fallback missing, second fallback present
        with patch.dict(os.environ, {"FALLBACK_HOST_2": "fallback_val"}):
            storage = get_storage("redis_fallback")
            assert storage.config["host"] == "fallback_val"
            assert storage.resolution_sources["host"].source == "fallback"
            assert storage.resolution_sources["host"].env_var == "FALLBACK_HOST_2"

    def test_env_overwrite_primary_wins(self, mock_config):
        # Using primary even if fallback exists
        with patch.dict(os.environ, {"PRIMARY_HOST": "primary_val", "FALLBACK_HOST_1": "fallback_val"}):
            storage = get_storage("redis_fallback")
            assert storage.config["host"] == "primary_val"
            assert storage.resolution_sources["host"].source == "overwrite"

    def test_non_null_preserved(self, mock_config):
        # explicit value should NOT be overwritten
        with patch.dict(os.environ, {"REDIS_HOST": "env_host", "REDIS_PORT": "9999"}):
            storage = get_storage("mixed")
            assert storage.config["host"] == "explicit_host" # Preserved
            assert storage.config["port"] == "9999" # Null -> Overwritten

    def test_remove_meta_keys(self, mock_config):
        # Default behavior: remove meta keys
        storage = get_storage("redis_env")
        assert "env_host_key" not in storage.config
        assert "env_port_key" not in storage.config

        # Option: keep meta keys
        storage_keep = get_storage("redis_env", options=StorageOptions(remove_meta_keys=False))
        assert "env_host_key" in storage_keep.config
        assert storage_keep.config["env_host_key"] == "REDIS_HOST"

    def test_regex_pattern_matching(self, mock_config):
        # Test private method directly for robustness
        sc = StorageConfig()
        assert sc._extract_base_property("env_host_key") == "host"
        assert sc._extract_base_property("env_host_key_fallbacks") == "host"
        assert sc._extract_base_property("env_my_custom_prop_key") == "my_custom_prop"
        assert sc._extract_base_property("host") is None
        assert sc._extract_base_property("env_host") is None
