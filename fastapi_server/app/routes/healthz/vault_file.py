"""Vault file healthz routes."""

from fastapi import APIRouter, HTTPException
from ...vault_file import EnvStore
import os

router = APIRouter(prefix="/healthz/admin/vault-file", tags=["Admin"])


@router.get("/status")
async def vault_file_status():
    """Vault file status."""
    vault_file = os.getenv("VAULT_SECRET_FILE")
    return {
        "loaded": bool(vault_file),
        "file": vault_file or None,
    }


@router.get("/json")
async def vault_file_json():
    """Vault file contents as JSON."""
    return EnvStore().get_all()


@router.get("/compute/{name}")
async def vault_file_compute(name: str):
    """Get a specific value from the vault file."""
    env_store = EnvStore()
    value = env_store.get(name)
    if value is None:
        raise HTTPException(status_code=404, detail=f"Key '{name}' not found in vault")
    # Mask the value for security
    masked = f"{value[:4]}..." if len(value) > 4 else "****"
    return {
        "name": name,
        "exists": True,
        "preview": masked,
    }
