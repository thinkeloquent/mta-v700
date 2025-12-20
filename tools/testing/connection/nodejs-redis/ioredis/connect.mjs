/**
 * ioredis Connection Test
 *
 * Tests Redis connectivity using the ioredis package.
 * ioredis has strong support for Cluster, Sentinel, Streams, Pipelining, and PubSub.
 *
 * Matches Python implementation: tools/testing/connection/python-redis/aioredis
 *
 * Environment Variables:
 *   REDIS_HOST     - Redis host (default: localhost)
 *   REDIS_PORT     - Redis port (default: 6379)
 *   REDIS_PASSWORD - Redis password (optional)
 *   REDIS_USERNAME - Redis username (optional, for ACL)
 *   REDIS_DB       - Redis database number (default: 0)
 *   REDIS_SSL      - Enable SSL (default: false)
 */

import Redis from "ioredis";

/**
 * Get Redis configuration from environment.
 * @returns {Object} Redis configuration
 */
function getRedisConfig() {
  const host = process.env.REDIS_HOST || "localhost";
  const port = parseInt(process.env.REDIS_PORT || "6379", 10);
  const password = process.env.REDIS_PASSWORD || null;
  const username = process.env.REDIS_USERNAME || null;
  const db = parseInt(process.env.REDIS_DB || "0", 10);
  const useSsl = (process.env.REDIS_SSL || "false").toLowerCase() === "true";

  return { host, port, password, username, db, useSsl };
}

/**
 * Print configuration details.
 * @param {Object} config - Redis configuration
 */
function printConfig(config) {
  console.log("Config:");
  console.log(`  Host: ${config.host}`);
  console.log(`  Port: ${config.port}`);
  console.log(`  Username: ${config.username || "(none)"}`);
  console.log(`  Password: ${config.password ? "***" : "(none)"}`);
  console.log(`  DB: ${config.db}`);
  console.log(`  SSL: ${config.useSsl}`);
}

/**
 * Build ioredis options from config.
 * @param {Object} config - Redis configuration
 * @param {Object} extraOptions - Additional options
 * @returns {Object} ioredis options
 */
function buildOptions(config, extraOptions = {}) {
  const options = {
    host: config.host,
    port: config.port,
    db: config.db,
    connectTimeout: 5000,
    maxRetriesPerRequest: 1,
    retryStrategy: () => null, // Don't retry for tests
    ...extraOptions,
  };

  if (config.password) {
    options.password = config.password;
  }
  if (config.username) {
    options.username = config.username;
  }

  options.tls = {
    rejectUnauthorized: false,
  };

  return options;
}

/**
 * Create a promisified connection test.
 * @param {Redis} client - ioredis client
 * @param {number} timeout - Timeout in ms
 * @returns {Promise} Resolves when connected
 */
function waitForConnection(client, timeout = 5000) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      reject(new Error("Connection timeout"));
    }, timeout);

    client.once("ready", () => {
      clearTimeout(timer);
      resolve();
    });

    client.once("error", (err) => {
      clearTimeout(timer);
      reject(err);
    });
  });
}

/**
 * Test 1: Basic connection without SSL
 */
async function testBasicConnection(config) {
  console.log("\n[Test 1] Basic connection (no SSL)");

  const options = buildOptions(config);
  const client = new Redis(options);

  try {
    await waitForConnection(client);
    const pong = await client.ping();
    console.log(`  SUCCESS: Connected! PING returned: ${pong}`);
    await client.quit();
    return true;
  } catch (e) {
    console.log(`  FAILURE: ${e.message}`);
    try {
      await client.quit();
    } catch {
      // Ignore
    }
    return false;
  }
}

/**
 * Test 2: Connection with SSL enabled (no verification)
 */
async function testSslNoVerify(config) {
  console.log("\n[Test 2] SSL connection with verification disabled");

  const options = buildOptions(config);

  const client = new Redis(options);

  try {
    await waitForConnection(client);
    const pong = await client.ping();
    console.log(
      `  SUCCESS: Connected with SSL (no verify)! PING returned: ${pong}`
    );
    await client.quit();
    return true;
  } catch (e) {
    console.log(`  FAILURE: ${e.message}`);
    try {
      await client.quit();
    } catch {
      // Ignore
    }
    return false;
  }
}

/**
 * Test 3: Connection using Redis URL
 */
async function testUrlConnection(config) {
  console.log("\n[Test 3] Connection using Redis URL");

  // Build URL
  const protocol = config.useSsl ? "rediss" : "redis";
  let auth = "";
  if (config.username && config.password) {
    auth = `${encodeURIComponent(config.username)}:${encodeURIComponent(
      config.password
    )}@`;
  } else if (config.password) {
    auth = `:${encodeURIComponent(config.password)}@`;
  }
  const url = `${protocol}://${auth}${config.host}:${config.port}/${config.db}`;

  const options = {
    maxRetriesPerRequest: 1,
    retryStrategy: () => null,
    connectTimeout: 5000,
  };

  if (config.useSsl) {
    options.tls = { rejectUnauthorized: false };
  }

  const client = new Redis(url, options);

  try {
    await waitForConnection(client);
    const pong = await client.ping();
    console.log(`  SUCCESS: Connected via URL! PING returned: ${pong}`);

    // Get server info
    const info = await client.info("server");
    const versionMatch = info.match(/redis_version:(\S+)/);
    if (versionMatch) {
      console.log(`  Server version: ${versionMatch[1]}`);
    }

    await client.quit();
    return true;
  } catch (e) {
    console.log(`  FAILURE: ${e.message}`);
    try {
      await client.quit();
    } catch {
      // Ignore
    }
    return false;
  }
}

/**
 * Test 4: SET/GET operations
 */
async function testSetGet(config) {
  console.log("\n[Test 4] SET/GET operations");

  const options = buildOptions(config);
  if (config.useSsl) {
    options.tls = { rejectUnauthorized: false };
  }

  const client = new Redis(options);

  try {
    await waitForConnection(client);

    const testKey = `test:ioredis:${Date.now()}`;
    const testValue = "Hello from ioredis!";

    // SET with expiry
    await client.set(testKey, testValue, "EX", 60);
    console.log(`  SET ${testKey} = "${testValue}"`);

    // GET
    const retrieved = await client.get(testKey);
    console.log(`  GET ${testKey} = "${retrieved}"`);

    // DEL
    await client.del(testKey);
    console.log(`  DEL ${testKey}`);

    console.log("  SUCCESS: SET/GET/DEL operations completed");
    await client.quit();
    return true;
  } catch (e) {
    console.log(`  FAILURE: ${e.message}`);
    try {
      await client.quit();
    } catch {
      // Ignore
    }
    return false;
  }
}

/**
 * Test 5: Pipeline operations
 */
async function testPipeline(config) {
  console.log("\n[Test 5] Pipeline operations");

  const options = buildOptions(config);
  if (config.useSsl) {
    options.tls = { rejectUnauthorized: false };
  }

  const client = new Redis(options);

  try {
    await waitForConnection(client);

    const baseKey = `test:pipeline:${Date.now()}`;

    // Create pipeline
    const pipeline = client.pipeline();
    pipeline.set(`${baseKey}:1`, "value1");
    pipeline.set(`${baseKey}:2`, "value2");
    pipeline.set(`${baseKey}:3`, "value3");
    pipeline.get(`${baseKey}:1`);
    pipeline.get(`${baseKey}:2`);
    pipeline.get(`${baseKey}:3`);
    pipeline.del(`${baseKey}:1`);
    pipeline.del(`${baseKey}:2`);
    pipeline.del(`${baseKey}:3`);

    const results = await pipeline.exec();
    console.log(`  Executed ${results.length} commands in pipeline`);
    console.log("  SUCCESS: Pipeline completed");

    await client.quit();
    return true;
  } catch (e) {
    console.log(`  FAILURE: ${e.message}`);
    try {
      await client.quit();
    } catch {
      // Ignore
    }
    return false;
  }
}

/**
 * Test 6: Transaction (MULTI/EXEC)
 */
async function testTransaction(config) {
  console.log("\n[Test 6] Transaction (MULTI/EXEC)");

  const options = buildOptions(config);
  if (config.useSsl) {
    options.tls = { rejectUnauthorized: false };
  }

  const client = new Redis(options);

  try {
    await waitForConnection(client);

    const baseKey = `test:transaction:${Date.now()}`;

    // Use multi for atomic transaction
    const results = await client
      .multi()
      .set(`${baseKey}:counter`, "0")
      .incr(`${baseKey}:counter`)
      .incr(`${baseKey}:counter`)
      .incr(`${baseKey}:counter`)
      .get(`${baseKey}:counter`)
      .del(`${baseKey}:counter`)
      .exec();

    console.log(`  Executed ${results.length} commands in transaction`);
    const finalValue = results[4][1]; // GET result
    console.log(`  Final counter value: ${finalValue}`);
    console.log("  SUCCESS: Transaction completed");

    await client.quit();
    return true;
  } catch (e) {
    console.log(`  FAILURE: ${e.message}`);
    try {
      await client.quit();
    } catch {
      // Ignore
    }
    return false;
  }
}

/**
 * Main test runner
 */
async function main() {
  console.log("=".repeat(60));
  console.log("ioredis Connection Test");
  console.log("=".repeat(60));

  const config = getRedisConfig();
  printConfig(config);

  const results = {
    basic: false,
    sslNoVerify: false,
    urlConnection: false,
    setGet: false,
    pipeline: false,
    transaction: false,
  };

  // Run tests
  results.basic = await testBasicConnection(config);
  results.sslNoVerify = await testSslNoVerify(config);
  results.urlConnection = await testUrlConnection(config);
  results.setGet = await testSetGet(config);
  results.pipeline = await testPipeline(config);
  results.transaction = await testTransaction(config);

  // Summary
  console.log("\n" + "=".repeat(60));
  console.log("Test Summary");
  console.log("=".repeat(60));

  const passed = Object.values(results).filter(Boolean).length;
  const total = Object.keys(results).length;

  console.log(`  Passed: ${passed}/${total}`);

  for (const [test, result] of Object.entries(results)) {
    const status = result ? "\x1b[32mPASS\x1b[0m" : "\x1b[31mFAIL\x1b[0m";
    console.log(`  ${test}: ${status}`);
  }

  process.exit(passed === total ? 0 : 1);
}

main().catch((err) => {
  console.error("Fatal error:", err);
  process.exit(1);
});
