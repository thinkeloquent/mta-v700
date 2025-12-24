/**
 * Server Entry Point
 * Loads vault-file ENV variables before importing the server.
 */

import { EnvStore, VaultFile } from "@internal/vault-file";
import dotenv from "dotenv";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.resolve(__dirname, "..");


// Step 1: Load .env file if exists
const envPath = path.join(projectRoot, ".env");
if (fs.existsSync(envPath)) {
    dotenv.config({ path: envPath });
    console.log(`  .env file: ${envPath}`);
}

// Step 2: Initialize Vault File with base64 file parsers
const vaultFile = process.env.VAULT_SECRET_FILE;
if (vaultFile) {
    try {
        await EnvStore.onStartup(
            vaultFile,
            '.env*',
            false,
            {}, // computed definitions
            {
                FILE_APP_ENV: (store) => {
                    const b64 = store.get('FILE_APP_ENV');
                    return b64 ? VaultFile.fromBase64Auto(b64).content : null;
                }
            }
        );
        console.log(`  Vault file loaded: ${vaultFile}`);
    } catch (error) {
        console.error("Failed to load vault file:", error);
        process.exit(1);
    }
} else {
    console.log('VAULT_SECRET_FILE env var not set, skipping EnvStore initialization');
}

// Step 3: Import and start the server (after ENV is loaded)
await import("./endpoint_auth_compute.mjs"); // Register compute functions
await import("./app.mjs");
