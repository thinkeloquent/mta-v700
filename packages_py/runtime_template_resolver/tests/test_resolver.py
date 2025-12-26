import pytest
from runtime_template_resolver.resolver import resolve_path, SecurityError
from runtime_template_resolver.extractor import extract_placeholders
from runtime_template_resolver.path_parser import parse_path

class TestResolver:
    def test_simple_dict(self):
        data = {"key": "value"}
        assert resolve_path(data, "key") == "value"
        
    def test_nested_dict(self):
        data = {"a": {"b": {"c": "value"}}}
        assert resolve_path(data, "a.b.c") == "value"
        
    def test_list_index(self):
        data = {"items": ["first", "second"]}
        assert resolve_path(data, "items[0]") == "first"
        assert resolve_path(data, "items[1]") == "second"
        
    def test_mixed_access(self):
        data = {"users": [{"name": "alice"}, {"name": "bob"}]}
        assert resolve_path(data, "users[0].name") == "alice"

    def test_security_error(self):
        class Secure:
            _secret = "hidden"
            public = "visible"
            
        data = Secure()
        assert resolve_path(data, "public") == "visible"
        with pytest.raises(SecurityError):
            resolve_path(data, "_secret")

class TestExtractor:
    def test_extract_mustache(self):
        tpl = "Hello {{name}}"
        placeholders = extract_placeholders(tpl)
        assert len(placeholders) == 1
        assert placeholders[0]["path"] == "name"
        assert placeholders[0]["syntax"] == "MUSTACHE"
        
    def test_extract_dot(self):
        tpl = "Value: $.path.to.val"
        placeholders = extract_placeholders(tpl)
        assert len(placeholders) == 1
        assert placeholders[0]["path"] == "path.to.val"
        assert placeholders[0]["syntax"] == "DOT_PATH"

class TestPathParser:
    def test_parse_path(self):
        assert parse_path("a.b.c") == ["a", "b", "c"]
        assert parse_path("a[0].c") == ["a", "0", "c"]
        assert parse_path("a['b'].c") == ["a", "b", "c"]
