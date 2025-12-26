from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from app_yaml_config import AppYamlConfig
import os

@dataclass
class TemplateContext:
    env: Dict[str, str] = field(default_factory=dict)
    app: Dict[str, Any] = field(default_factory=dict)
    request: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"env": self.env, "app": self.app, "request": self.request, "config": self.config}

class ContextBuilder:
    @staticmethod
    def build_startup_context(config: AppYamlConfig) -> TemplateContext:
        ctx = TemplateContext()
        ctx.env = dict(os.environ)
        
        # Get raw config for app info
        raw_app_config = config.get('app') or {}
        
        # Determine environment from load result
        load_result = config.get_load_result()
        app_env = 'dev'
        if load_result and load_result.app_env:
            app_env = load_result.app_env.value if hasattr(load_result.app_env, 'value') else str(load_result.app_env)
            
        ctx.app = {
            'name': raw_app_config.get('name', 'unknown'),
            'version': raw_app_config.get('version', '0.0.0'),
            'description': raw_app_config.get('description', ''),
            'environment': app_env
        }
        ctx.config = config.get_all()
        return ctx

    @staticmethod
    def build_request_context(request: Any) -> Dict[str, Any]:
        if request is None:
            return {'headers': {}, 'query': {}, 'path': {}}
        
        # Helper to get attribute or item
        def get_data(obj, key, attr_key=None):
            attr_key = attr_key or key
            if isinstance(obj, dict):
                return obj.get(key, {})
            if hasattr(obj, attr_key):
                val = getattr(obj, attr_key)
                if hasattr(val, 'items'): # dict-like
                    return dict(val)
                return val
            return {}

        headers = {}
        # Try 'headers' key or attribute
        raw_headers = get_data(request, 'headers')
        if raw_headers:
             headers = {k.lower(): str(v) for k, v in raw_headers.items()}
            
        return {
            'headers': headers,
            'query': get_data(request, 'query', 'query_params'),
            'path': get_data(request, 'path', 'path_params')
        }


    @staticmethod
    def merge_contexts(startup: TemplateContext, request_ctx: Dict[str, Any]) -> Dict[str, Any]:
        result = startup.to_dict()
        result['request'] = request_ctx
        return result
