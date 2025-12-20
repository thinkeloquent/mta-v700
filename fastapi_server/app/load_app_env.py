"""Load .env and vault file at startup."""

from dotenv import load_dotenv
from .vault_file import EnvStore, VaultFile
import os

# 0. Load .env file if exists
app_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(app_dir, ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)
    print(f"  .env file: {env_path}")

# 1. Initialize Vault File with base64 file parsers
vault_file = os.getenv("VAULT_SECRET_FILE")
if vault_file:
    EnvStore.on_startup(
        vault_file,
        base64_file_parsers={
            'FILE_APP_ENV': lambda store: VaultFile.from_base64_auto(
                store.get('FILE_APP_ENV')
            )[0] if store.get('FILE_APP_ENV') else None  # [0] is parsed content, [1] is format
        }
    )
else:
    print("VAULT_SECRET_FILE env var not set, skipping EnvStore initialization")
