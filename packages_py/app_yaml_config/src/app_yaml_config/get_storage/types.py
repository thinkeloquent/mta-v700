
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Literal, TypedDict

@dataclass
class StorageOptions:
    """Options for retrieving storage configuration."""
    apply_env_overwrites: bool = True
    apply_fallbacks: bool = True
    remove_meta_keys: bool = True

class ResolutionSource(TypedDict):
    """Metadata about where a configuration value was resolved from."""
    source: Literal['yaml', 'overwrite', 'fallback']
    env_var: Optional[str]

@dataclass
class StorageResult:
    """Result of a storage configuration retrieval."""
    name: str
    config: Dict[str, Any]
    env_overwrites: List[str]
    resolution_sources: Dict[str, ResolutionSource] = field(default_factory=dict)
