"""
Server Entry Point
Loads vault-file ENV variables before importing the server.
"""

import os
from dotenv import load_dotenv
from vault_file import EnvStore, VaultFile

# Step 1: Load .env file if exists
app_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(app_dir, ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)
    print(f"  .env file: {env_path}")

# Step 2: Initialize Vault File with base64 file parsers
vault_file = os.getenv("VAULT_SECRET_FILE")
if vault_file:
    try:
        EnvStore.on_startup(
            vault_file,
            base64_file_parsers={
                'FILE_APP_ENV': lambda store: VaultFile.from_base64_auto(
                    store.get('FILE_APP_ENV')
                )[0] if store.get('FILE_APP_ENV') else None
            }
        )
        print(f"  Vault file loaded: {vault_file}")
    except Exception as e:
        print(f"Failed to load vault file: {e}")
        # We might want to exit here if vault is critical, but preserving existing behavior for now
else:
    print("VAULT_SECRET_FILE env var not set, skipping EnvStore initialization")

# Step 3: Import and expose the app (after ENV is loaded)
# This import must happen AFTER EnvStore.on_startup so that AppYamlConfig sees the env vars
from . import endpoint_auth_compute  # Register compute functions
from . import endpoint_context_compute  # Register context compute functions
from .app import app  # noqa: E402

__all__ = ["app"]
