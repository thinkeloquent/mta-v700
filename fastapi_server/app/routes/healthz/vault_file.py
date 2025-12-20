"""Vault file healthz routes."""

from fastapi import APIRouter
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
