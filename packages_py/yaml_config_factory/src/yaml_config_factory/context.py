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
        
        # Handle starlette/fastapi Request
        headers = {}
        if hasattr(request, 'headers'):
            headers = {k.lower(): str(v) for k, v in request.headers.items()}
            
        query = {}
        if hasattr(request, 'query_params'):
            query = dict(request.query_params)
            
        path = {}
        if hasattr(request, 'path_params'):
            path = dict(request.path_params)
            
        return {
            'headers': headers,
            'query': query,
            'path': path
        }

    @staticmethod
    def merge_contexts(startup: TemplateContext, request_ctx: Dict[str, Any]) -> Dict[str, Any]:
        result = startup.to_dict()
        result['request'] = request_ctx
        return result
