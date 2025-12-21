
import os
import pytest
from unittest.mock import patch, MagicMock
from app_yaml_config import AppYamlConfig, get_provider, ProviderNotFoundError, ProviderOptions

@pytest.fixture
def mock_config():
    # Reset singleton
    AppYamlConfig._instance = None
    
    # Create mock config data
    config_data = {
        'global': {
            'client': {
                'timeout_seconds': 60.0,
                'retries': 3
            },
            'network': {
                'default_env': 'dev'
            }
        },
        'providers': {
            'test_provider': {
                'base_url': 'https://api.test',
                'client': {
                    'timeout_seconds': 120.0  # Override
                },
                'api_key': None,
                'overwrite_from_env': {
                    'api_key': 'TEST_PROVIDER_API_KEY'
                }
            },
            'no_env_provider': {
                'api_key': 'hardcoded'
            },
            'missing_env_provider': {
                'api_key': None,
                'overwrite_from_env': {
                    'api_key': 'MISSING_ENV_VAR'
                }
            }
        }
    }
    
    # Mock initialize/load
    with patch('app_yaml_config.AppYamlConfig.initialize') as mock_init:
        # Manually set up instance
        instance = AppYamlConfig()
        instance._config = config_data
        instance._initialized = True
        AppYamlConfig._instance = instance
        yield instance
        AppYamlConfig._instance = None

def test_get_provider_basic_retrieval(mock_config):
    """Test retrieving a provider merges global config."""
    result = get_provider('test_provider')
    
    # Check merged global fields
    assert result.config['network']['default_env'] == 'dev'
    assert result.config['client']['retries'] == 3
    
    # Check provider specific overrides
    assert result.config['base_url'] == 'https://api.test'
    assert result.config['client']['timeout_seconds'] == 120.0

def test_get_provider_env_overwrite(mock_config):
    """Test environment variable overwrite for null values."""
    with patch.dict(os.environ, {'TEST_PROVIDER_API_KEY': 'secret-123'}):
        result = get_provider('test_provider')
        
        assert result.config['api_key'] == 'secret-123'
        assert 'api_key' in result.env_overwrites
        assert 'overwrite_from_env' not in result.config

def test_get_provider_env_overwrite_skipped_if_not_null(mock_config):
    """Test env overwrite is skipped if value is not null."""
    # Even if env var is set, it shouldn't overwrite if value is present
    with patch.dict(os.environ, {'TEST_PROVIDER_API_KEY': 'secret-123'}):
        # Temporarily modify config to have a value
        mock_config._config['providers']['test_provider']['api_key'] = 'not-null'
        
        result = get_provider('test_provider')
        assert result.config['api_key'] == 'not-null'

def test_get_provider_env_overwrite_missing_env(mock_config):
    """Test env overwrite leaves null if env var is missing."""
    with patch.dict(os.environ, {}, clear=True):
        result = get_provider('missing_env_provider')
        assert result.config['api_key'] is None
        assert 'api_key' not in result.env_overwrites

def test_provider_not_found(mock_config):
    """Test error raised for unknown provider."""
    with pytest.raises(ProviderNotFoundError):
        get_provider('unknown_provider')

def test_disable_global_merge(mock_config):
    """Test disabling global merge."""
    options = ProviderOptions(merge_global=False)
    result = get_provider('test_provider', options=options)
    
    assert 'network' not in result.config
    assert result.config['client']['timeout_seconds'] == 120.0
    assert 'retries' not in result.config['client']
