#!/usr/bin/env node
/**
 * PostgreSQL Connection Test - Node.js Client Integration
 *
 * Authentication: Password
 * Protocol: PostgreSQL wire protocol (not HTTP)
 * Health Check: SELECT 1
 *
 * Uses internal packages:
 *   - @internal/provider_api_getters: Credential resolution
 *   - @internal/app-static-config-yaml: YAML configuration loading
 *   - @internal/db-connection-postgres: Configuration resolution
 */
import { fileURLToPath } from 'url';
import { dirname, resolve } from 'path';
import pg from 'pg';

// ============================================================================
// Project Setup
// ============================================================================
const __dirname = dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = resolve(__dirname, '..', '..', '..', '..');

// Load static config
const { AppYamlConfig } = await import(
  resolve(PROJECT_ROOT, 'packages_mjs', 'app-yaml-config', 'dist', 'index.js')
);
const configDir = resolve(PROJECT_ROOT, 'common', 'config');
const staticConfig = await AppYamlConfig.initialize({ files: ['server.yaml'], configDir });

// Import internal packages
const { PostgresConfig } = await import(
  resolve(PROJECT_ROOT, 'packages_mjs', 'db_connection_postgres', 'src', 'index.mjs')
);

// ============================================================================
// Configuration
// ============================================================================
const pgConfig = new PostgresConfig();

// Debug output
const CONFIG = {
  POSTGRES_HOST: pgConfig.host,
  POSTGRES_PORT: pgConfig.port,
  POSTGRES_USER: pgConfig.user,
  POSTGRES_DB: pgConfig.database,
  POSTGRES_SCHEMA: pgConfig.schema,
  DISABLE_SSL: !pgConfig.ssl ? true : false,
  DEBUG: !['false', '0'].includes((process.env.DEBUG || '').toLowerCase()),
};

// ============================================================================
// Health Check
// ============================================================================
async function healthCheck() {
  console.log('\n=== PostgreSQL Health Check (pg) ===\n');
  return healthCheckPg();
}

// ============================================================================
// Sample Operations using pg
// ============================================================================
async function healthCheckPg() {
  console.log('\n=== PostgreSQL Health Check (pg) ===\n');

  const { Pool } = pg;

  console.log(`Connecting to: ${pgConfig.host}:${pgConfig.port}/${pgConfig.database}`);

  const pool = new Pool(pgConfig.getConnectionConfig());

  try {
    const client = await pool.connect();

    try {
      // Test connection
      const result = await client.query('SELECT 1 as test');
      console.log(`SELECT 1: ${result.rows[0].test}`);

      // Get version
      const versionResult = await client.query('SELECT version()');
      console.log(`Version: ${versionResult.rows[0].version}`);

      // Get current database
      const dbResult = await client.query('SELECT current_database()');
      console.log(`Database: ${dbResult.rows[0].current_database}`);

      return { success: true, data: { version: versionResult.rows[0].version } };
    } finally {
      client.release();
    }
  } catch (error) {
    console.error('Error:', error.message);
    return { success: false, error: error.message };
  } finally {
    await pool.end();
  }
}

async function sampleOperations() {
  console.log('\n=== Sample PostgreSQL Operations ===\n');

  const { Pool } = pg;
  const pool = new Pool(pgConfig.getConnectionConfig());

  try {
    const client = await pool.connect();

    try {
      // List schemas
      const schemasResult = await client.query(`
        SELECT schema_name
        FROM information_schema.schemata
        ORDER BY schema_name
        LIMIT 10
      `);
      console.log('Schemas:');
      schemasResult.rows.forEach((row) => {
        console.log(`  - ${row.schema_name}`);
      });

      // List tables in public schema
      const tablesResult = await client.query(`
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = $1
        ORDER BY table_name
        LIMIT 10
      `, [pgConfig.schema]);
      console.log(`\nTables in ${pgConfig.schema}:`);
      tablesResult.rows.forEach((row) => {
        console.log(`  - ${row.table_name}`);
      });

      // Get database size
      const sizeResult = await client.query(`
        SELECT pg_size_pretty(pg_database_size(current_database())) as size
      `);
      console.log(`\nDatabase size: ${sizeResult.rows[0].size}`);

      return { success: true };
    } finally {
      client.release();
    }
  } catch (error) {
    console.error('Error:', error.message);
    return { success: false, error: error.message };
  } finally {
    await pool.end();
  }
}

// ============================================================================
// Run Tests
// ============================================================================
async function main() {
  console.log('PostgreSQL Connection Test (Node.js Client Integration)');
  console.log('='.repeat(55));
  console.log(`Host: ${pgConfig.host}:${pgConfig.port}`);
  console.log(`Database: ${pgConfig.database}`);
  console.log(`User: ${pgConfig.user}`);
  console.log(`Schema: ${pgConfig.schema}`);
  console.log(`Debug: ${CONFIG.DEBUG}`);

  await healthCheck();

  // Uncomment to run additional tests:
  // await healthCheckPg();
  // await sampleOperations();
}

main().catch(console.error);
