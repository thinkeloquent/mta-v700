/**
 * Load .env and vault file at startup.
 */

import { EnvStore, VaultFile } from "@internal/vault-file";
import dotenv from "dotenv";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.resolve(__dirname, "..");

// 0. Load .env file if exists
const envPath = path.join(projectRoot, ".env");
if (fs.existsSync(envPath)) {
  dotenv.config({ path: envPath });
  console.log(`  .env file: ${envPath}`);
}

// 1. Initialize Vault File with base64 file parsers
const vaultFile = process.env.VAULT_SECRET_FILE;
if (vaultFile) {
  await EnvStore.onStartup(
    vaultFile,
    '.env*',
    false,
    {}, // computed definitions
    {
      FILE_APP_ENV: (store) => {
        const b64 = store.get('FILE_APP_ENV');
        return b64 ? VaultFile.fromBase64Auto(b64).content : null;  // .content is parsed data
      }
    }
  );
} else {
  console.log('VAULT_SECRET_FILE env var not set, skipping EnvStore initialization');
}

export { vaultFile };
