/**
 * Load AppYamlConfig at startup.
 */

import { AppYamlConfig } from '@internal/app-yaml-config';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.resolve(__dirname, '..', '..');
const configDir = path.join(projectRoot, 'common', 'config');
const appEnv = (process.env.APP_ENV || 'dev').toLowerCase();

try {
  const configFiles = ['base.yml', `server.${appEnv}.yaml`];
  const loaded = [];
  const notLoaded = [];

  for (const f of configFiles) {
    const filePath = path.join(configDir, f);
    if (fs.existsSync(filePath)) {
      loaded.push(f);
    } else {
      notLoaded.push(f);
    }
  }

  await AppYamlConfig.initialize({
    files: ['base.yml', 'server.{APP_ENV}.yaml'],
    configDir,
    computedDefinitions: {
      proxy_url: (c) => c.getNested(['global', 'network', 'proxy_urls', appEnv]),
    },
  });

  const config = AppYamlConfig.getInstance();

  // Register Factory Computed Definitions
  // Use dynamic import for factory to ensure it runs after init if needed, or static is fine.
  // We need to import YamlConfigFactory. typescript? This is .mjs file.
  // We can import from @internal/yaml-config-factory
  const { YamlConfigFactory } = await import('@internal/yaml-config-factory');
  const factory = new YamlConfigFactory(config);

  const exposeAuth = config.get('expose_yaml_config_compute_auth') || {};
  const categories = ['providers', 'services', 'storages'];

  for (const cat of categories) {
    const items = exposeAuth[cat] || [];
    for (const item of items) {
      const key = `auth:${cat}.${item}`;
      const path = `${cat}.${item}`;
      config.registerComputed(key, (c) => factory.compute(path));
    }
  }

  console.log('AppYamlConfig initialized.');
  if (loaded.length) console.log(`  Loaded: ${loaded.join(', ')}`);
  if (notLoaded.length) console.log(`  Not found: ${notLoaded.join(', ')}`);
  console.log(`App Name: ${config.getNested(['app', 'name'])}`);
  if (process.env.VAULT_SECRET_FILE) console.log(`  Vault file: ${process.env.VAULT_SECRET_FILE}`);
} catch (err) {
  if (err.code === 'ENOENT') {
    console.error(`[FATAL] Config file missing: ${err.message}`);
    console.error(`  APP_ENV=${appEnv}, configDir=${configDir}`);
    console.error(`  Ensure base.yml and server.${appEnv}.yaml exist in ${configDir}`);
  } else {
    console.error(`[FATAL] Failed to initialize AppYamlConfig: ${err.message}`);
  }
  process.exit(1);
}

export { configDir, appEnv };
