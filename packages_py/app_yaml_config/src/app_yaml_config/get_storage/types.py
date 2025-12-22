
from dataclasses import dataclass
from ..domain import BaseResolveOptions, BaseResult, ResolutionSource

@dataclass
class StorageOptions(BaseResolveOptions):
    """Options for retrieving storage configuration."""
    pass

@dataclass
class StorageResult(BaseResult):
    """Result of a storage configuration retrieval."""
    pass
