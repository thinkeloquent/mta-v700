/**
 * AWS SDK OpenSearch Client Test (Control Plane)
 * 
 * Uses @aws-sdk/client-opensearch to manage OpenSearch domains.
 * This is NOT for querying data (indexing/searching).
 */

const { OpenSearchClient, ListDomainNamesCommand } = require("@aws-sdk/client-opensearch");
require('dotenv').config();

// =============================================================================
// Configuration
// =============================================================================

const region = process.env.AWS_REGION || 'us-east-1';

// =============================================================================
// Test
// =============================================================================

async function runTests() {
    console.log("=".repeat(60));
    console.log("AWS SDK OpenSearch Client Test (Control Plane)");
    console.log("=".repeat(60));
    console.log(`Region: ${region}`);

    // Credential resolution is handled automatically by AWS SDK
    // (Env vars, ~/.aws/credentials, IAM role, etc.)

    const client = new OpenSearchClient({ region });

    try {
        console.log("\n[Test] Listing Domain Names...");
        const command = new ListDomainNamesCommand({});
        const response = await client.send(command);

        const names = response.DomainNames ? response.DomainNames.map(d => d.DomainName) : [];
        console.log(`  SUCCESS: Found ${names.length} domains`);
        if (names.length > 0) {
            console.log(`  Domains: ${names.join(', ')}`);
        }

    } catch (err) {
        if (err.name === 'CredentialsProviderError') {
            console.log("  FAILURE: No AWS credentials found.");
            console.log("  Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY or verify ~/.aws/credentials");
        } else {
            console.log(`  FAILURE: ${err.message}`);
        }
    }

    console.log("\n" + "=".repeat(60));
}

if (require.main === module) {
    runTests().catch(err => {
        console.error("Fatal Error:", err);
    });
}
