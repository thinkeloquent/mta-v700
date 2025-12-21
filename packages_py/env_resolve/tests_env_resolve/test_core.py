import os
import pytest
from unittest.mock import patch
from env_resolve.core import resolve, resolve_bool, resolve_int, resolve_float

def test_resolve_arg():
    assert resolve("arg", ["ENV_VAR"], {}, "config", "default") == "arg"

def test_resolve_env(monkeypatch):
    monkeypatch.setenv("TEST_ENV_VAR", "env_val")
    assert resolve(None, ["TEST_ENV_VAR"], {}, "config", "default") == "env_val"

def test_resolve_env_priority(monkeypatch):
    monkeypatch.setenv("TEST_ENV_1", "val1")
    monkeypatch.setenv("TEST_ENV_2", "val2")
    assert resolve(None, ["TEST_ENV_1", "TEST_ENV_2"], {}, "config", "default") == "val1"
    
def test_resolve_config():
    config = {"key": "config_val"}
    assert resolve(None, ["MISSING_ENV"], config, "key", "default") == "config_val"

def test_resolve_default():
    assert resolve(None, ["MISSING_ENV"], {}, "key", "default") == "default"

def test_resolve_bool():
    assert resolve_bool(True, [], {}, None, False) is True
    assert resolve_bool(None, [], {}, None, True) is True
    
    # String variants
    assert resolve_bool("true", [], {}, None, False) is True
    assert resolve_bool("1", [], {}, None, False) is True
    assert resolve_bool("yes", [], {}, None, False) is True
    assert resolve_bool("on", [], {}, None, False) is True
    
    assert resolve_bool("false", [], {}, None, True) is False
    assert resolve_bool("0", [], {}, None, True) is False
    assert resolve_bool("no", [], {}, None, True) is False
    assert resolve_bool("off", [], {}, None, True) is False

def test_resolve_int():
    assert resolve_int(123, [], {}, None, 0) == 123
    assert resolve_int("123", [], {}, None, 0) == 123
    assert resolve_int(None, [], {}, None, 456) == 456
    
    # Config
    assert resolve_int(None, [], {"k": "789"}, "k", 0) == 789

def test_resolve_float():
    assert resolve_float(1.5, [], {}, None, 0.0) == 1.5
    assert resolve_float("2.5", [], {}, None, 0.0) == 2.5
