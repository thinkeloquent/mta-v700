import os
from typing import List, Optional, Union
from pydantic import BaseModel

class EnvVarResolveResult(BaseModel):
    value: Optional[str]
    source: Optional[str]
    tried: List[str]

def resolve_env_var(env_var_name: str) -> Optional[str]:
    """Look up a single environment variable value."""
    return os.getenv(env_var_name)

def resolve_env_var_chain(
    primary: Optional[str] = None,
    overwrite: Optional[Union[str, List[str]]] = None
) -> EnvVarResolveResult:
    """
    Try multiple env vars in order (overwrite -> primary -> fallbacks).
    Returns values, source, and list of tried vars.
    """
    tried: List[str] = []
    
    # 1. Try overwrite first (highest priority)
    if overwrite:
        overwrites = [overwrite] if isinstance(overwrite, str) else overwrite
        for env_var in overwrites:
            tried.append(env_var)
            val = resolve_env_var(env_var)
            if val is not None:
                return EnvVarResolveResult(value=val, source=env_var, tried=tried)

    # 2. Try primary
    if primary:
        tried.append(primary)
        val = resolve_env_var(primary)
        if val is not None:
            return EnvVarResolveResult(value=val, source=primary, tried=tried)

    return EnvVarResolveResult(value=None, source=None, tried=tried)
