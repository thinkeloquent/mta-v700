
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union, TypedDict

class ResolutionSource(TypedDict):
    source: str  # 'yaml', 'overwrite', 'fallback'
    env_var: Optional[str]

@dataclass
class ProviderOptions:
    """Options for retrieving a provider configuration."""
    merge_global: bool = True
    apply_env_overwrites: bool = True
    # Runtime overrides
    overwrite_from_env: Optional[Dict[str, Union[str, List[str]]]] = None
    fallbacks_from_env: Optional[Dict[str, List[str]]] = None

@dataclass
class ProviderResult:
    """Result of a provider configuration retrieval."""
    name: str
    config: Dict[str, Any]
    env_overwrites: List[str] = field(default_factory=list)
    global_merged: bool = False
    resolution_sources: Dict[str, ResolutionSource] = field(default_factory=dict)
