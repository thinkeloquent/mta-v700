/**
 * node-redis Connection Test
 *
 * Tests Redis connectivity using the official node-redis package (redis).
 * Matches Python implementation: tools/testing/connection/python-redis/redis-py
 *
 * Environment Variables:
 *   REDIS_HOST     - Redis host (default: localhost)
 *   REDIS_PORT     - Redis port (default: 6379)
 *   REDIS_PASSWORD - Redis password (optional)
 *   REDIS_USERNAME - Redis username (optional, for ACL)
 *   REDIS_DB       - Redis database number (default: 0)
 *   REDIS_SSL      - Enable SSL (default: false)
 */

import { createClient } from "redis";

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
 * Build Redis URL from config.
 * @param {Object} config - Redis configuration
 * @param {boolean} useTls - Whether to use TLS
 * @returns {string} Redis URL
 */
function buildRedisUrl(config, useTls = false) {
  const protocol = useTls ? "rediss" : "redis";
  let auth = "";

  if (config.username && config.password) {
    auth = `${encodeURIComponent(config.username)}:${encodeURIComponent(
      config.password
    )}@`;
  } else if (config.password) {
    // Redis < 6 style (no username)
    auth = `:${encodeURIComponent(config.password)}@`;
  }

  return `${protocol}://${auth}${config.host}:${config.port}/${config.db}`;
}

/**
 * Test 1: Basic connection without SSL
 */
async function testBasicConnection(config) {
  console.log("\n[Test 1] Basic connection (no SSL)");

  const client = createClient({
    url: buildRedisUrl(config, false),
    socket: {
      connectTimeout: 5000,
      tls: true,
      rejectUnauthorized: false, // Disable SSL verification
    },
  });

  client.on("error", (err) => {
    // Suppress error logging during test
  });

  try {
    await client.connect();
    const pong = await client.ping();
    console.log(`  SUCCESS: Connected! PING returned: ${pong}`);
    await client.disconnect();
    return true;
  } catch (e) {
    console.log(`  FAILURE: ${e.message}`);
    return false;
  }
}

/**
 * Test 2: Connection with SSL enabled (no verification)
 */
async function testSslNoVerify(config) {
  console.log("\n[Test 2] SSL connection with verification disabled");

  const client = createClient({
    url: buildRedisUrl(config, true),
    socket: {
      connectTimeout: 5000,
      tls: true,
      rejectUnauthorized: false, // Disable SSL verification
    },
  });

  client.on("error", (err) => {
    // Suppress error logging during test
  });

  try {
    await client.connect();
    const pong = await client.ping();
    console.log(
      `  SUCCESS: Connected with SSL (no verify)! PING returned: ${pong}`
    );
    await client.disconnect();
    return true;
  } catch (e) {
    console.log(`  FAILURE: ${e.message}`);
    return false;
  }
}

/**
 * Test 3: Connection using socket options directly
 */
async function testSocketOptions(config) {
  console.log("\n[Test 3] Connection using socket options");

  const socketOptions = {
    host: config.host,
    port: config.port,
    connectTimeout: 5000,
    tls: true,
    rejectUnauthorized: false, // Disable SSL verification
  };

  // Add TLS options if SSL is enabled
  if (config.useSsl) {
    socketOptions.tls = true;
    socketOptions.rejectUnauthorized = false;
  }

  const clientOptions = {
    socket: socketOptions,
    database: config.db,
  };

  // Add authentication
  if (config.username) {
    clientOptions.username = config.username;
  }
  if (config.password) {
    clientOptions.password = config.password;
  }

  const client = createClient(clientOptions);

  client.on("error", (err) => {
    // Suppress error logging during test
  });

  try {
    await client.connect();
    const pong = await client.ping();
    console.log(
      `  SUCCESS: Connected using socket options! PING returned: ${pong}`
    );

    // Get server info
    const info = await client.info("server");
    const versionMatch = info.match(/redis_version:(\S+)/);
    if (versionMatch) {
      console.log(`  Server version: ${versionMatch[1]}`);
    }

    await client.disconnect();
    return true;
  } catch (e) {
    console.log(`  FAILURE: ${e.message}`);
    return false;
  }
}

/**
 * Test 4: Set and Get operations
 */
async function testSetGet(config) {
  console.log("\n[Test 4] SET/GET operations");

  const socketOptions = {
    host: config.host,
    port: config.port,
    connectTimeout: 5000,
    tls: true,
    rejectUnauthorized: false, // Disable SSL verification
  };

  if (config.useSsl) {
    socketOptions.tls = true;
    socketOptions.rejectUnauthorized = false;
  }

  const clientOptions = {
    socket: socketOptions,
    database: config.db,
  };

  if (config.username) clientOptions.username = config.username;
  if (config.password) clientOptions.password = config.password;

  const client = createClient(clientOptions);

  client.on("error", (err) => {
    // Suppress error logging during test
  });

  try {
    await client.connect();

    const testKey = `test:node-redis:${Date.now()}`;
    const testValue = "Hello from node-redis!";

    // SET
    await client.set(testKey, testValue, { EX: 60 }); // Expires in 60 seconds
    console.log(`  SET ${testKey} = "${testValue}"`);

    // GET
    const retrieved = await client.get(testKey);
    console.log(`  GET ${testKey} = "${retrieved}"`);

    // DEL
    await client.del(testKey);
    console.log(`  DEL ${testKey}`);

    console.log("  SUCCESS: SET/GET/DEL operations completed");
    await client.disconnect();
    return true;
  } catch (e) {
    console.log(`  FAILURE: ${e.message}`);
    return false;
  }
}

/**
 * Test 5: Connection pool / multiple commands
 */
async function testMultipleCommands(config) {
  console.log("\n[Test 5] Multiple commands (pipeline)");

  const socketOptions = {
    host: config.host,
    port: config.port,
    connectTimeout: 5000,
    tls: true,
    rejectUnauthorized: false, // Disable SSL verification
  };

  if (config.useSsl) {
    socketOptions.tls = true;
    socketOptions.rejectUnauthorized = false;
  }

  const clientOptions = {
    socket: socketOptions,
    database: config.db,
  };

  if (config.username) clientOptions.username = config.username;
  if (config.password) clientOptions.password = config.password;

  const client = createClient(clientOptions);

  client.on("error", (err) => {
    // Suppress error logging during test
  });

  try {
    await client.connect();

    // Use multi for transaction/pipeline
    const multi = client.multi();
    const baseKey = `test:pipeline:${Date.now()}`;

    multi.set(`${baseKey}:1`, "value1");
    multi.set(`${baseKey}:2`, "value2");
    multi.set(`${baseKey}:3`, "value3");
    multi.get(`${baseKey}:1`);
    multi.get(`${baseKey}:2`);
    multi.get(`${baseKey}:3`);
    multi.del(`${baseKey}:1`);
    multi.del(`${baseKey}:2`);
    multi.del(`${baseKey}:3`);

    const results = await multi.exec();
    console.log(`  Executed ${results.length} commands in pipeline`);
    console.log("  SUCCESS: Pipeline completed");

    await client.disconnect();
    return true;
  } catch (e) {
    console.log(`  FAILURE: ${e.message}`);
    return false;
  }
}

/**
 * Main test runner
 */
async function main() {
  console.log("=".repeat(60));
  console.log("node-redis Connection Test");
  console.log("=".repeat(60));

  const config = getRedisConfig();
  printConfig(config);

  const results = {
    basic: false,
    sslNoVerify: false,
    socketOptions: false,
    setGet: false,
    pipeline: false,
  };

  // Run tests
  results.basic = await testBasicConnection(config);
  results.sslNoVerify = await testSslNoVerify(config);
  results.socketOptions = await testSocketOptions(config);
  results.setGet = await testSetGet(config);
  results.pipeline = await testMultipleCommands(config);

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
