"""
Request builder helper.
"""
from typing import Any, Dict, Optional, Union
from ..types import HttpMethod, RequestOptions

class RequestBuilder:
    """Fluent builder for RequestOptions."""
    
    def __init__(self, url: str = "", method: HttpMethod = "GET"):
        self._options: RequestOptions = {
            "url": url,
            "method": method,
            "headers": {},
            "params": {}
        }

    def url(self, url: str) -> "RequestBuilder":
        self._options["url"] = url
        return self

    def method(self, method: HttpMethod) -> "RequestBuilder":
        self._options["method"] = method
        return self

    def header(self, key: str, value: str) -> "RequestBuilder":
        self._options["headers"][key] = value
        return self
        
    def headers(self, headers: Dict[str, str]) -> "RequestBuilder":
        self._options["headers"].update(headers)
        return self

    def param(self, key: str, value: Any) -> "RequestBuilder":
        self._options["params"][key] = value
        return self
        
    def params(self, params: Dict[str, Any]) -> "RequestBuilder":
        self._options["params"].update(params)
        return self

    def json(self, data: Any) -> "RequestBuilder":
        self._options["json"] = data
        return self
        
    def data(self, data: Any) -> "RequestBuilder":
        self._options["data"] = data
        return self
        
    def timeout(self, timeout: float) -> "RequestBuilder":
        self._options["timeout"] = timeout
        return self

    def build(self) -> RequestOptions:
        """Get the constructed options."""
        return self._options
