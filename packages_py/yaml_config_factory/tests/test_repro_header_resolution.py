
import pytest
from unittest.mock import MagicMock, AsyncMock
from yaml_config_factory import YamlConfigFactory, ComputeOptions

class TestHeaderResolutionReproduction:

    @pytest.fixture
    def mock_app_config(self):
        config = MagicMock()
        config.get_load_result.return_value.app_env = 'test'
        config.get_all.return_value = {}
        return config

    @pytest.fixture
    def mock_fetch_auth(self):
        mock = AsyncMock()
        # Ensure it returns a dummy object with required attributes
        dummy_auth = MagicMock()
        dummy_auth.type = 'none'
        dummy_auth.provider_name = 'test'
        dummy_auth.resolution = MagicMock()
        mock.return_value = dummy_auth
        return mock

    @pytest.fixture
    def mock_encode_auth(self):
        return MagicMock()

    @pytest.fixture
    def factory(self, mock_app_config, mock_fetch_auth, mock_encode_auth):
        return YamlConfigFactory(mock_app_config, mock_fetch_auth, mock_encode_auth)

    @pytest.mark.asyncio
    async def test_resolve_header_when_present(self, factory, mock_app_config):
        raw_config = {
            "overwrite_from_context": {
                "resolved_header": "{{request.headers.x-test-header}}"
            }
        }

        mock_app_config.get_nested.return_value = raw_config
        mock_app_config.get.side_effect = lambda k: {"test_provider": raw_config} if k == 'providers' else {}

        # Mock FastAPI Request
        request_mock = MagicMock()
        request_mock.headers = {"x-test-header": "resolved-value"}
        
        # Note: request.headers in FastAPI is not a dict but Mapping. get() works.
        # But yaml_config_factory implementation of ContextBuilder.build_request_context handles it.
        # Wait, let's verify context builder implementation for Python.
        # It uses: context['request'] = {'headers': dict(request.headers) if request else {}, ...}

        # context['request'] = {'headers': dict(request.headers) if request else {}, ...}

        result = await factory.compute('providers.test_provider', ComputeOptions(include_config=True), request_mock)

        assert result.config['resolved_header'] == 'resolved-value'

    @pytest.mark.asyncio
    async def test_not_resolve_header_when_missing(self, factory, mock_app_config):
        raw_config = {
            "overwrite_from_context": {
                "resolved_header": "{{request.headers.x-missing-header}}"
            }
        }

        mock_app_config.get_nested.return_value = raw_config
        mock_app_config.get.side_effect = lambda k: {"test_provider": raw_config} if k == 'providers' else {}

        # Mock FastAPI Request
        request_mock = MagicMock()
        request_mock.headers = {"x-other-header": "value"}

        # Await the result
        result = await factory.compute('providers.test_provider', ComputeOptions(include_config=True), request_mock)

        # Standard behavior: keep template string if unresolved
        assert result.config['resolved_header'] == '{{request.headers.x-missing-header}}'
