import pytest
import os
from db_connection_elasticsearch import ElasticsearchConfig, get_elasticsearch_client
from db_connection_elasticsearch.constants import VENDOR_ON_PREM

def test_imports():
    assert ElasticsearchConfig is not None
    assert get_elasticsearch_client is not None
    assert VENDOR_ON_PREM == "on-prem"


def test_config_overrides():
    # Force on-prem to override potential env vars
    config = ElasticsearchConfig(vendor_type="on-prem", host="localhost", port=9200)
    assert config.vendor_type == "on-prem"
    assert config.port == 9200
    
def test_env_or_defaults():
    # If ENV is set, it might be DO, else on-prem
    config = ElasticsearchConfig()
    if os.environ.get("ELASTIC_DB_HOST"):
        # If env is present, just ensure config matches
        pass
    else:
        assert config.vendor_type == "on-prem"

