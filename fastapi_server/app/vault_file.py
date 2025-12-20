"""Re-export vault_file package for consistent app imports."""

from vault_file import EnvStore, VaultFile

__all__ = ["EnvStore", "VaultFile"]
