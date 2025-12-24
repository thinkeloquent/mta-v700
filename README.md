```yml
providers:
  # Static (default/current behavior)
  anthropic:
    endpoint_auth_type: bearer
    endpoint_api_key: "${ANTHROPIC_API_KEY}"

  # Startup resolver - computed once at first access
  vault-provider:
    endpoint_auth_type: bearer
    endpoint_auth_token_resolver: startup
    # No endpoint_api_key - computed by registered function

  # Request resolver - computed per request
  multi-tenant:
    endpoint_auth_type: bearer
    endpoint_auth_token_resolver: request
    # Token depends on incoming request context
```

Notes

- fetch_auth_encoding remains unchanged - it only formats credentials as headers
- The feature focuses on where credentials come from, not how they're encoded
- Backward compatibility: configs without endpoint_auth_token_resolver default to static
