import os
from typing import Any, Dict, List, Optional, Union

def resolve(
    arg: Any, 
    env_keys: Union[str, List[str]], 
    config: Optional[Dict[str, Any]], 
    config_key: Optional[str], 
    default: Any
) -> Any:
    """
    Resolve configuration value from multiple sources in priority order:
    1. Direct argument (if not None)
    2. Environment variables
    3. Configuration dictionary
    4. Default value
    """
    # 1. Argument
    if arg is not None:
        return arg
    
    # 2. Env Vars
    if isinstance(env_keys, str):
        env_keys = [env_keys]
    
    for key in env_keys:
        if key:
            val = os.getenv(key)
            if val is not None:
                return val
            
    # 3. Config object
    if config and config_key and config_key in config:
        return config[config_key]
        
    # 4. Default
    return default

def resolve_bool(
    arg: Any, 
    env_keys: Union[str, List[str]], 
    config: Optional[Dict[str, Any]], 
    config_key: Optional[str], 
    default: bool
) -> bool:
    """Resolve boolean value with string conversion support."""
    val = resolve(arg, env_keys, config, config_key, default)
    
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() in ("true", "1", "yes", "on")
    if isinstance(val, int):
        return bool(val)
        
    return bool(val)

def resolve_int(
    arg: Any, 
    env_keys: Union[str, List[str]], 
    config: Optional[Dict[str, Any]], 
    config_key: Optional[str], 
    default: int
) -> int:
    """Resolve integer value."""
    val = resolve(arg, env_keys, config, config_key, default)
    try:
        return int(val)
    except (ValueError, TypeError):
        return default

def resolve_float(
    arg: Any, 
    env_keys: Union[str, List[str]], 
    config: Optional[Dict[str, Any]], 
    config_key: Optional[str], 
    default: float
) -> float:
    """Resolve float value."""
    val = resolve(arg, env_keys, config, config_key, default)
    try:
        return float(val)
    except (ValueError, TypeError):
        return default
