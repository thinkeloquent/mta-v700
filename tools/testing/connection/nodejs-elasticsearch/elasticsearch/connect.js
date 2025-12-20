/**
 * Node.js Elasticsearch Connection Test
 *
 * Replicates the logic from tools/testing/connection/python-elasticsearch
 * Uses @elastic/elasticsearch client.
 */

import { Client } from "@elastic/elasticsearch";
import { promises as dns } from "node:dns";
import fs from "node:fs";
import dotenv from "dotenv";
import process from "node:process";
import { fileURLToPath } from "node:url";

dotenv.config();

// =============================================================================
// Configuration
// =============================================================================

function getEsConfig() {
  return {
    // Core Coonection
    scheme: process.env.ELASTICSEARCH_SCHEME || "https",
    host: process.env.ELASTICSEARCH_HOST || "localhost",
    port: parseInt(process.env.ELASTICSEARCH_PORT || "9200", 10),
    cloudId: process.env.ELASTIC_CLOUD_ID || "",

    // Auth
    user: process.env.ELASTICSEARCH_USER || "",
    password: process.env.ELASTICSEARCH_PASSWORD || "",
    apiKey: process.env.ELASTICSEARCH_API_KEY || "",

    // Index
    index: process.env.ELASTICSEARCH_INDEX || "",

    // SSL/TLS
    verifyCerts:
      (process.env.ELASTICSEARCH_VERIFY_CERTS || "false").toLowerCase() ===
      "true",
    sslShowWarn:
      (process.env.ELASTICSEARCH_SSL_SHOW_WARN || "false").toLowerCase() ===
      "true",
    caCerts: process.env.ELASTICSEARCH_CA_CERTS || "",
    clientCert: process.env.ELASTICSEARCH_CLIENT_CERT || "",
    clientKey: process.env.ELASTICSEARCH_CLIENT_KEY || "",

    // Proxy (Node.js client handles proxy via agent or specialized setup, often automatically via env vars)
    // We will just log it for info purposes here
    httpProxy: process.env.HTTP_PROXY || process.env.http_proxy || "",
    httpsProxy: process.env.HTTPS_PROXY || process.env.https_proxy || "",
  };
}

function buildUrl(config) {
  if (config.cloudId) return `Cloud ID: ${config.cloudId}`;
  return `${config.scheme}://${config.host}:${config.port}`;
}

// =============================================================================
// Helper Functions
// =============================================================================

function formatConnectionError(err, host) {
  const msg = err.message || err.toString();
  const lowerMsg = msg.toLowerCase();

  // DNS Error
  if (lowerMsg.includes("getaddrinfo") || lowerMsg.includes("enotfound")) {
    return (
      `DNS_ERROR: Cannot resolve hostname '${host}'\n` +
      `    Possible causes:\n` +
      `    - Hostname is misspelled or invalid\n` +
      `    - DNS server is unreachable\n` +
      `    - Original error: ${msg}`
    );
  }

  // Connection Refused
  if (lowerMsg.includes("econnrefused")) {
    return (
      `CONNECTION_REFUSED: Server is not accepting connections on '${host}'\n` +
      `    Possible causes:\n` +
      `    - Elasticsearch service is not running\n` +
      `    - Wrong port number\n` +
      `    - Firewall blocking connection\n` +
      `    - Original error: ${msg}`
    );
  }

  // Timeout
  if (lowerMsg.includes("timeout") || lowerMsg.includes("etimedout")) {
    return (
      `CONNECTION_TIMEOUT: Connection timed out for '${host}'\n` +
      `    Possible causes:\n` +
      `    - Server is overloaded or unresponsive\n` +
      `    - Network latency issues\n` +
      `    - Firewall silently dropping packets\n` +
      `    - Original error: ${msg}`
    );
  }

  // SSL/TLS
  if (
    lowerMsg.includes("certificate") ||
    lowerMsg.includes("ssl") ||
    lowerMsg.includes("pkix")
  ) {
    return (
      `SSL_ERROR: SSL/TLS connection failed\n` +
      `    Possible causes:\n` +
      `    - Invalid or expired SSL certificate\n` +
      `    - Self-signed certificate not trusted\n` +
      `    Try: Set ELASTICSEARCH_VERIFY_CERTS=false for testing\n` +
      `    - Original error: ${msg}`
    );
  }

  // Auth
  if (err.meta && err.meta.statusCode === 401) {
    return (
      `AUTH_ERROR: Authentication failed\n` +
      `    Possible causes:\n` +
      `    - Invalid API key\n` +
      `    - Wrong username/password\n` +
      `    - Original error: ${msg}`
    );
  }

  return `ERROR: ${msg}`;
}

async function validateHost(host) {
  if (!host) return { valid: false, message: "Host is empty" };
  if (host === "localhost" || host === "127.0.0.1") return { valid: true };

  try {
    await dns.lookup(host);
    return { valid: true };
  } catch (err) {
    return {
      valid: false,
      message: `Cannot resolve hostname '${host}': ${err.message}`,
    };
  }
}

function getTlsConfig(config) {
  const tlsOptions = {
    // In Node.js, rejectUnauthorized: false is equivalent to verify_certs=False
    rejectUnauthorized: config.verifyCerts,
  };

  if (config.caCerts) {
    try {
      tlsOptions.ca = fs.readFileSync(config.caCerts);
    } catch (e) {
      console.warn(`    WARNING: Could not read CA cert file: ${e.message}`);
    }
  }

  if (config.clientCert) {
    try {
      tlsOptions.cert = fs.readFileSync(config.clientCert);
    } catch (e) {
      console.warn(
        `    WARNING: Could not read client cert file: ${e.message}`
      );
    }
  }

  if (config.clientKey) {
    try {
      tlsOptions.key = fs.readFileSync(config.clientKey);
    } catch (e) {
      console.warn(`    WARNING: Could not read client key file: ${e.message}`);
    }
  }

  return tlsOptions;
}

function createClient(config, authOverride = {}) {
  const options = {
    tls: getTlsConfig(config),
  };

  // Connection
  if (config.cloudId) {
    options.cloud = { id: config.cloudId };
  } else {
    options.node = `${config.scheme}://${config.host}:${config.port}`;
  }

  if (config.user && config.password) {
    options.auth = { username: config.user, password: config.password };
  }

  return new Client(options);
}

// =============================================================================
// Tests
// =============================================================================

async function runTests() {
  const config = getEsConfig();

  console.log("=".repeat(60));
  console.log("Node.js @elastic/elasticsearch Connection Test");
  console.log("=".repeat(60));

  console.log("\nConfig:");
  if (config.cloudId) {
    console.log(`  Cloud ID: Set (${config.cloudId.substring(0, 10)}...)`);
  } else {
    console.log(`  Scheme: ${config.scheme}`);
    console.log(`  Host: ${config.host}`);
    console.log(`  Port: ${config.port}`);
  }
  console.log(`  User: ${config.user || "N/A"}`);
  console.log(`  API Key: ${config.apiKey ? "set" : "not set"}`);
  console.log(`  Index: ${config.index || "N/A"}`);
  console.log(`  HTTPS Proxy: ${config.httpsProxy || "N/A"}`);

  console.log("\nSSL Config:");
  console.log(`  Verify Certs: ${config.verifyCerts}`);
  console.log(`  CA Certs: ${config.caCerts || "N/A"}`);

  // Pre-flight validation
  if (!config.cloudId) {
    console.log("\n[Pre-flight] Validating hostname...");
    const { valid, message } = await validateHost(config.host);
    if (!valid) {
      console.log(`  WARNING: ${message}`);
      console.log("  Tests will likely fail. Check ELASTICSEARCH_HOST.");
    } else {
      console.log(`  OK: Hostname '${config.host}' is resolvable`);
    }
  } else {
    console.log("\n[Pre-flight] Using Cloud ID (skipping host validation)");
  }

  // ---------------------------------------------------------------------------
  // Test 1: API Key Authentication
  // ---------------------------------------------------------------------------
  if (config.apiKey) {
    console.log("\n[Test 1] Client with API Key");
    let client = null;
    try {
      // Force API key by clearing basic auth in override
      client = createClient(config, { user: "", password: "" });
      const info = await client.info();
      console.log(
        `  SUCCESS: Connected to Elasticsearch ${info.version.number}`
      );
      console.log(`  Cluster: ${info.cluster_name}`);
      console.log(`  Tagline: ${info.tagline}`);

      if (config.index) {
        const exists = await client.indices.exists({ index: config.index });
        console.log(`  Index '${config.index}' exists: ${exists}`);
      }
    } catch (e) {
      console.log(`  FAILURE: ${formatConnectionError(e, config.host)}`);
    } finally {
      if (client) await client.close();
    }
  } else {
    console.log("\n[Test 1] API Key Authentication - SKIPPED (no API key set)");
  }

  // ---------------------------------------------------------------------------
  // Test 2: Basic Auth
  // ---------------------------------------------------------------------------
  if (config.user && config.password) {
    console.log("\n[Test 2] Client with Basic Auth");
    let client = null;
    try {
      // Force basic auth by clearing API key in override
      client = createClient(config, { apiKey: "" });
      const info = await client.info();
      console.log(
        `  SUCCESS: Connected to Elasticsearch ${info.version.number}`
      );
      console.log(`  Cluster: ${info.cluster_name}`);

      if (config.index) {
        const exists = await client.indices.exists({ index: config.index });
        console.log(`  Index '${config.index}' exists: ${exists}`);
      }
    } catch (e) {
      console.log(`  FAILURE: ${formatConnectionError(e, config.host)}`);
    } finally {
      if (client) await client.close();
    }
  } else {
    console.log("\n[Test 2] Basic Auth - SKIPPED (no username/password set)");
  }

  // ---------------------------------------------------------------------------
  // Test 3: No Authentication
  // ---------------------------------------------------------------------------
  console.log("\n[Test 3] Client without authentication");
  let client = null;
  try {
    client = createClient(config, { apiKey: "", user: "", password: "" });
    const info = await client.info();
    console.log(`  SUCCESS: Connected to Elasticsearch ${info.version.number}`);
    console.log(`  Cluster: ${info.cluster_name}`);
  } catch (e) {
    console.log(`  FAILURE: ${formatConnectionError(e, config.host)}`);
  } finally {
    if (client) await client.close();
  }

  // ---------------------------------------------------------------------------
  // Test 4: Full Flow (Index stats)
  // ---------------------------------------------------------------------------
  console.log("\n[Test 4] Full authentication flow (auto-detect)");
  try {
    client = createClient(config); // Use defaults from config
    const info = await client.info();
    console.log(`  SUCCESS: Connected to Elasticsearch ${info.version.number}`);

    if (config.index) {
      console.log(`\n  Checking index: ${config.index}`);
      const exists = await client.indices.exists({ index: config.index });
      if (exists) {
        console.log(`    Index exists: True`);
        try {
          const stats = await client.indices.stats({ index: config.index });
          const prim = stats._all.primaries;
          console.log(`    Document count: ${prim.docs.count}`);
          console.log(
            `    Size: ${(prim.store.size_in_bytes / 1024 / 1024).toFixed(
              2
            )} MB`
          );
        } catch (e) {
          console.log(`    Could not get stats: ${e.message}`);
        }
      } else {
        console.log(`    Index exists: False`);
      }
    }
  } catch (e) {
    console.log(`  FAILURE: ${formatConnectionError(e, config.host)}`);
  } finally {
    if (client) await client.close();
  }

  // ---------------------------------------------------------------------------
  // Test 5: Custom SSL (Insecure)
  // ---------------------------------------------------------------------------
  console.log("\n[Test 5] Custom SSL (verification disabled)");
  try {
    // Force verifyCerts=false for this test
    const insecureConfig = { ...config, verifyCerts: false };
    client = createClient(insecureConfig);
    const info = await client.info();
    console.log(`  SUCCESS: Connected with verification disabled`);
    console.log(`  Version: ${info.version.number}`);
  } catch (e) {
    console.log(`  FAILURE: ${formatConnectionError(e, config.host)}`);
  } finally {
    if (client) await client.close();
  }

  console.log("\n" + "=".repeat(60));
  console.log("Tests completed");
  console.log("=".repeat(60));
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  runTests().catch((err) => {
    console.error("Fatal Error:", err);
  });
}
