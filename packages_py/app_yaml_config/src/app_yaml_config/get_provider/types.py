
from dataclasses import dataclass
from typing import Dict, Any, Optional
from ..domain import BaseResolveOptions, BaseResult, ResolutionSource

@dataclass
class ProviderOptions(BaseResolveOptions):
    """Options for retrieving provider configuration."""
    merge_global: bool = True
    overwrite_from_env: Optional[Dict[str, Any]] = None
    fallbacks_from_env: Optional[Dict[str, Any]] = None

@dataclass
class ProviderResult(BaseResult):
    """Result of a provider configuration retrieval."""
    global_merged: bool = True
