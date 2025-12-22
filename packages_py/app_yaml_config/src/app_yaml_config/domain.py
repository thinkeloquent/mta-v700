"""Data models for AppYamlConfig."""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable

@dataclass
class LoadResult:
    """Result of loading configuration files."""
    files_loaded: List[str] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    app_env: Optional[str] = None
    merge_order: List[str] = field(default_factory=list)

# Type alias for computed functions: (config: AppYamlConfig) -> Any
ComputedDefinition = Callable[['AppYamlConfig'], Any]

@dataclass
class ResolutionSource:
    source: str  # 'yaml' | 'overwrite' | 'fallback'
    env_var: Optional[str] = None

@dataclass
class BaseResolveOptions:
    apply_env_overwrites: bool = True
    apply_fallbacks: bool = True
    remove_meta_keys: bool = True

@dataclass
class BaseResult:
    name: str
    config: Dict[str, Any]
    env_overwrites: List[str]
    resolution_sources: Dict[str, ResolutionSource]
