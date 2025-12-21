
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

@dataclass
class ProviderOptions:
    """Options for retrieving a provider configuration."""
    merge_global: bool = True
    apply_env_overwrites: bool = True

@dataclass
class ProviderResult:
    """Result of a provider configuration retrieval."""
    name: str
    config: Dict[str, Any]
    env_overwrites: List[str] = field(default_factory=list)
    global_merged: bool = False
