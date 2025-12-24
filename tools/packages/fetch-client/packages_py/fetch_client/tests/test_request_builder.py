"""
Tests for RequestBuilder.
"""
from fetch_client.core.request import RequestBuilder

def test_request_builder():
    opts = (
        RequestBuilder("https://example.com/api")
        .method("POST")
        .header("Authorization", "Bearer token")
        .param("q", "search")
        .json({"foo": "bar"})
        .timeout(10.0)
        .build()
    )
    
    assert opts["url"] == "https://example.com/api"
    assert opts["method"] == "POST"
    assert opts["headers"]["Authorization"] == "Bearer token"
    assert opts["params"]["q"] == "search"
    assert opts["json"] == {"foo": "bar"}
    assert opts["timeout"] == 10.0
