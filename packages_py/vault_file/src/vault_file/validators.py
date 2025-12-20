from typing import Dict, Any
import uuid
import re

class VaultValidationError(Exception):
    pass

class VaultSerializationError(Exception):
    pass

def validate_vault_data(data: Dict[str, Any]) -> None:
    required_keys = ["header", "metadata", "payload"]
    for key in required_keys:
        if key not in data:
            raise VaultValidationError(f"Missing required key: {key}")
    
    validate_header(data.get("header", {}))

def validate_header(header_data: Dict[str, Any]) -> None:
    required_keys = ["id", "version", "created_at"]
    for key in required_keys:
        if key not in header_data:
            raise VaultValidationError(f"Missing required header key: {key}")
            
    # UUID Validation
    try:
        uuid.UUID(header_data["id"])
    except ValueError:
        raise VaultValidationError("Invalid UUID format")
        
    # Version Format (Simple check for now)
    if not isinstance(header_data["version"], str):
         raise VaultValidationError("Version must be a string")
