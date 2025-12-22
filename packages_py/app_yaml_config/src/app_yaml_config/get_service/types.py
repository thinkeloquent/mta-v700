
from dataclasses import dataclass
from ..domain import BaseResolveOptions, BaseResult, ResolutionSource

@dataclass
class ServiceOptions(BaseResolveOptions):
    """Options for retrieving service configuration."""
    pass

@dataclass
class ServiceResult(BaseResult):
    """Result of a service configuration retrieval."""
    pass
