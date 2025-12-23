
import logging
import pytest
from unittest.mock import MagicMock, patch
from yaml_config_factory import YamlConfigFactory, ComputeOptions
from fetch_auth_config import AuthConfig, AuthType
from fetch_auth_config.types.auth_config import AuthResolutionMeta

# Enable debug logging for tests
logging.getLogger("yaml_config_factory").setLevel(logging.DEBUG)

class TestYamlConfigFactoryOptimization:
    """Tests for YamlConfigFactory with Observability and Edge Cases."""

    @pytest.fixture
    def mock_app_config(self):
        config = MagicMock()
        config.get_load_result.return_value.app_env = 'dev'
        return config

    @pytest.fixture
    def mock_fetch_auth(self):
        return MagicMock()

    @pytest.fixture
    def mock_encode_auth(self):
        return MagicMock()

    @pytest.fixture
    def factory(self, mock_app_config, mock_fetch_auth, mock_encode_auth):
        return YamlConfigFactory(mock_app_config, mock_fetch_auth, mock_encode_auth)

    # =========================================================================
    # Statement & Branch Coverage
    # =========================================================================

    def test_compute_default_options(self, factory, mock_app_config, mock_fetch_auth, caplog):
        """Test compute with default options (only auth)."""
        # Setup
        mock_app_config.get_nested.return_value = {"some": "config"}
        mock_fetch_auth.return_value = AuthConfig(
            type=AuthType.BEARER, 
            provider_name='test', 
            resolution=AuthResolutionMeta({}, 'static', False)
        )

        with caplog.at_level(logging.DEBUG):
            result = factory.compute("providers.test")

        assert result.auth_config is not None
        assert result.proxy_config is None
        assert result.network_config is None
        
        assert "compute: Starting" in caplog.text
        assert "compute: Completed" in caplog.text

    def test_compute_all_options(self, factory, mock_app_config, mock_fetch_auth, caplog):
        """Test compute with all options enabled."""
        # Setup
        mock_app_config.get_nested.return_value = {"proxy_url": False}
        mock_app_config.get.return_value = {"network": {"default_environment": "prod"}}
        mock_fetch_auth.return_value = AuthConfig(
            type=AuthType.NONE, 
            provider_name='test', 
            resolution=AuthResolutionMeta({}, 'static', False)
        )

        opts = ComputeOptions(
            include_headers=True,
            include_proxy=True,
            include_network=True,
            include_config=True
        )

        with caplog.at_level(logging.DEBUG):
            result = factory.compute("providers.test", opts)

        assert result.auth_config is not None
        assert result.proxy_config is not None
        assert result.network_config is not None
        assert result.config is not None

        assert "compute: Resolving proxy" in caplog.text
        assert "compute: Resolving network config" in caplog.text

    # =========================================================================
    # Boundary & Error Handling
    # =========================================================================

    def test_compute_empty_path(self, factory, caplog):
        with caplog.at_level(logging.ERROR):
            with pytest.raises(ValueError, match="Path cannot be empty"):
                factory.compute("")
        assert "compute failed" in caplog.text

    def test_compute_invalid_path_format(self, factory):
        with pytest.raises(ValueError, match="Invalid path format"):
            factory.compute("providers")

    def test_compute_invalid_config_type(self, factory):
        with pytest.raises(ValueError, match="Invalid config type"):
            factory.compute("invalid.test")

    def test_compute_config_not_found(self, factory, mock_app_config):
        mock_app_config.get_nested.return_value = None
        with pytest.raises(ValueError, match="Configuration not found"):
            factory.compute("providers.missing")

    # =========================================================================
    # Logic Verification
    # =========================================================================

    def test_compute_network_mapping(self, factory, mock_app_config):
        mock_app_config.get.return_value = {
            "network": {
                "default_environment": "staging",
                "proxy_urls": {"dev": "http://dev"},
                "agent_proxy": {"http_proxy": "http://agent"}
            }
        }
        
        result = factory.compute_network()
        
        assert result.default_environment == "staging"
        assert result.proxy_urls["dev"] == "http://dev"
        assert result.agent_proxy["http_proxy"] == "http://agent"
