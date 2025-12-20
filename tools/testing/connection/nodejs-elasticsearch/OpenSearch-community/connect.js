/**
 * Node.js OpenSearch Connection Test
 * 
 * Uses @opensearch-project/opensearch client.
 * Compatible with OpenSearch and legacy Elasticsearch clusters.
 */

const { Client } = require('@opensearch-project/opensearch');
const dns = require('dns').promises;
const fs = require('fs');
require('dotenv').config();

// =============================================================================
// Configuration
// =============================================================================

function getConfig() {
    // Prefer OPENSEARCH_ prefix, fallback to ELASTICSEARCH_
    return {
        // Core Connection
        scheme: process.env.OPENSEARCH_SCHEME || process.env.ELASTICSEARCH_SCHEME || 'https',
        host: process.env.OPENSEARCH_HOST || process.env.ELASTICSEARCH_HOST || 'localhost',
        port: parseInt(process.env.OPENSEARCH_PORT || process.env.ELASTICSEARCH_PORT || '9200', 10),

        // Auth
        user: process.env.OPENSEARCH_USER || process.env.ELASTICSEARCH_USER || '',
        password: process.env.OPENSEARCH_PASSWORD || process.env.ELASTICSEARCH_PASSWORD || '',

        // Index
        index: process.env.OPENSEARCH_INDEX || process.env.ELASTICSEARCH_INDEX || '',

        // SSL/TLS
        verifyCerts: (process.env.OPENSEARCH_VERIFY_CERTS || process.env.ELASTICSEARCH_VERIFY_CERTS || 'false').toLowerCase() === 'true',
        caCerts: process.env.OPENSEARCH_CA_CERTS || process.env.ELASTICSEARCH_CA_CERTS || '',
        clientCert: process.env.OPENSEARCH_CLIENT_CERT || process.env.ELASTICSEARCH_CLIENT_CERT || '',
        clientKey: process.env.OPENSEARCH_CLIENT_KEY || process.env.ELASTICSEARCH_CLIENT_KEY || '',
    };
}

// =============================================================================
// Helper Functions
// =============================================================================

function formatConnectionError(err, host) {
    const msg = err.message || err.toString();
    return `ERROR: ${msg}`;
}

async function validateHost(host) {
    if (!host) return { valid: false, message: 'Host is empty' };
    if (host === 'localhost' || host === '127.0.0.1') return { valid: true };
    try {
        await dns.lookup(host);
        return { valid: true };
    } catch (err) {
        return { valid: false, message: `Cannot resolve hostname '${host}': ${err.message}` };
    }
}

function getTlsConfig(config) {
    const tlsOptions = {
        rejectUnauthorized: config.verifyCerts,
    };

    if (config.caCerts) {
        try {
            tlsOptions.ca = fs.readFileSync(config.caCerts);
        } catch (e) {
            console.warn(`    WARNING: Could not read CA cert file: ${e.message}`);
        }
    }
    return tlsOptions;
}

function createClient(config, authOverride = {}) {
    const options = {
        node: `${config.scheme}://${config.host}:${config.port}`,
        ssl: getTlsConfig(config)
    };

    if (authOverride.user !== undefined || authOverride.password !== undefined) {
        if (authOverride.user && authOverride.password) {
            options.auth = { username: authOverride.user, password: authOverride.password };
        }
    } else if (config.user && config.password) {
        options.auth = { username: config.user, password: config.password };
    }

    return new Client(options);
}

// =============================================================================
// Tests
// =============================================================================

async function runTests() {
    const config = getConfig();

    console.log("=".repeat(60));
    console.log("Node.js @opensearch-project/opensearch Connection Test");
    console.log("=".repeat(60));

    console.log("\nConfig:");
    console.log(`  Scheme: ${config.scheme}`);
    console.log(`  Host: ${config.host}`);
    console.log(`  Port: ${config.port}`);
    console.log(`  User: ${config.user || 'N/A'}`);
    console.log(`  Index: ${config.index || 'N/A'}`);

    console.log("\nSSL Config:");
    console.log(`  Verify Certs: ${config.verifyCerts}`);

    console.log("\n[Pre-flight] Validating hostname...");
    const { valid, message } = await validateHost(config.host);
    if (!valid) {
        console.log(`  WARNING: ${message}`);
    } else {
        console.log(`  OK: Hostname '${config.host}' is resolvable`);
    }

    // ---------------------------------------------------------------------------
    // Test 1: Basic Auth
    // ---------------------------------------------------------------------------
    if (config.user && config.password) {
        console.log("\n[Test 1] Client with Basic Auth");
        let client = null;
        try {
            client = createClient(config);
            const info = await client.info();
            console.log(`  SUCCESS: Connected to ${info.version.distribution || 'Elasticsearch'} ${info.version.number}`);
            console.log(`  Cluster: ${info.cluster_name}`);

            if (config.index) {
                const exists = await client.indices.exists({ index: config.index });
                console.log(`  Index '${config.index}' exists: ${exists.body}`);
            }
        } catch (e) {
            console.log(`  FAILURE: ${formatConnectionError(e, config.host)}`);
        } finally {
            if (client) await client.close();
        }
    } else {
        console.log("\n[Test 1] Basic Auth - SKIPPED (no username/password set)");
    }

    // ---------------------------------------------------------------------------
    // Test 2: No Authentication
    // ---------------------------------------------------------------------------
    console.log("\n[Test 2] Client without authentication");
    let client = null;
    try {
        client = createClient(config, { user: '', password: '' });
        const info = await client.info();
        console.log(`  SUCCESS: Connected to ${info.version.distribution || 'Elasticsearch'} ${info.version.number}`);
        console.log(`  Cluster: ${info.cluster_name}`);
    } catch (e) {
        console.log(`  FAILURE: ${formatConnectionError(e, config.host)}`);
    } finally {
        if (client) await client.close();
    }

    console.log("\n" + "=".repeat(60));
    console.log("Tests completed");
    console.log("=".repeat(60));
}

if (require.main === module) {
    runTests().catch(err => {
        console.error("Fatal Error:", err);
    });
}
