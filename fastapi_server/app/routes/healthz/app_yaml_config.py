from fastapi import APIRouter, HTTPException
from app_yaml_config import AppYamlConfig

router = APIRouter()

@router.get("/compute/{name:path}")
async def get_compute(name: str):
    """Get computed value by name, supports auth:providers.x pattern."""
    config = AppYamlConfig.get_instance()
    
    # 1. Check Standard Compute Allowlist
    allowed_compute = config.get("expose_yaml_config_compute", [])
    
    # 2. Check Auth Compute Allowlist
    is_auth_request = name.startswith("auth:")
    if is_auth_request:
        path_parts = name[5:].split(".") # Remove 'auth:'
        if len(path_parts) != 2:
             raise HTTPException(status_code=400, detail="Invalid auth path format")
             
        config_type = path_parts[0] # providers, services
        config_name = path_parts[1]
        
        expose_auth = config.get("expose_yaml_config_compute_auth", {})
        allowed_names = expose_auth.get(config_type, [])
        
        if config_name not in allowed_names:
             raise HTTPException(status_code=403, detail=f"{name} not in allowlist")
             
    elif name not in allowed_compute:
        raise HTTPException(status_code=403, detail=f"{name} not in allowlist")

    try:
        value = config.get_computed(name)
        # If it's auth, we might want to mask token? 
        # The factory returns {auth_config: ..., headers: ...}
        # Ideally we return the resolved object.
        # But we should be careful about secrets in HTTP response.
        # The PLAN says: "Never expose raw tokens in healthz responses - only metadata"
        
        if is_auth_request:
            # Transform for safe display
            # Value is likely {auth_config: AuthConfig, headers? }
            # Or just AuthConfig if factory.compute wrapper returned it directly?
            # Factory.compute returns Dict with auth_config.
            
            # Since register_computed lambda called factory.compute, value IS the dict.
            auth_config = value.get("auth_config")
            if auth_config:
                 # Create safe representation
                 safe_val = {
                     "type": auth_config.type,
                     "provider_name": auth_config.provider_name,
                     "token_resolved": bool(auth_config.token),
                     "token_source": auth_config.resolution.resolved_from if auth_config.resolution else "unknown",
                     "username": auth_config.username,
                     # Mask token
                     "token_preview": f"{auth_config.token[:4]}..." if auth_config.token else None
                 }
                 return {"name": name, "value": safe_val}

        return {"name": name, "value": value}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
