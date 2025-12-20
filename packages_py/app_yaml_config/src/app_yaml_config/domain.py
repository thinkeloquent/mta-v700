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
