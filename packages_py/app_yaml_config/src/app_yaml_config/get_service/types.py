
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Literal, TypedDict

@dataclass
class ServiceOptions:
    """Options for retrieving service configuration."""
    apply_env_overwrites: bool = True
    apply_fallbacks: bool = True

class ResolutionSource(TypedDict):
    """Metadata about where a configuration value was resolved from."""
    source: Literal['yaml', 'overwrite', 'fallback']
    env_var: Optional[str]

@dataclass
class ServiceResult:
    """Result of a service configuration retrieval."""
    name: str
    config: Dict[str, Any]
    env_overwrites: List[str]
    resolution_sources: Dict[str, ResolutionSource] = field(default_factory=dict)
