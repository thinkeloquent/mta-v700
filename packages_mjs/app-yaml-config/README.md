# @internal/app-yaml-config

A singleton YAML configuration loader for Node.js/TypeScript applications with support for environment-specific overrides, deep merging, and computed values.

## Installation

```bash
npm install @internal/app-yaml-config
```

## Features

- **Singleton Pattern**: Single source of truth for application configuration
- **YAML Support**: Load configuration from `.yaml` / `.yml` files
- **Environment-Specific Overrides**: Automatic loading of `{name}.{env}.yaml` files
- **Deep Merging**: Merge multiple config files with array replacement (not concatenation)
- **Computed Values**: Define derived values with circular dependency detection
- **APP_ENV Support**: Automatic `{APP_ENV}` placeholder substitution (converted to lowercase)

## Quick Start

```typescript
import { AppYamlConfig } from '@internal/app-yaml-config';

// Initialize (typically at app startup)
await AppYamlConfig.initialize({
  files: ['base.yml', 'server.{APP_ENV}.yaml'],
  configDir: './config',
});

// Access configuration anywhere in your app
const config = AppYamlConfig.getInstance();

// Get a top-level value
const appName = config.get('app');

// Get a nested value
const dbHost = config.getNested(['database', 'host']);

// Get with default
const port = config.get('port', 3000);
```

## API Reference

### `AppYamlConfig.initialize(options): Promise<AppYamlConfig>`

Initialize the configuration singleton. Must be called before `getInstance()`.

#### Options

| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `files` | `string[]` | Yes | List of config files to load (in order) |
| `configDir` | `string` | No | Base directory for resolving relative paths |
| `appEnv` | `string` | No | Environment name (defaults to `process.env.APP_ENV` or `'dev'`) |
| `computedDefinitions` | `ComputedRegistry` | No | Map of computed value definitions |

#### Example

```typescript
await AppYamlConfig.initialize({
  files: ['base.yml', 'server.{APP_ENV}.yaml'],
  configDir: path.join(__dirname, 'config'),
  appEnv: 'production',
  computedDefinitions: {
    dbUrl: (config) => {
      const host = config.getNested(['db', 'host']);
      const port = config.getNested(['db', 'port']);
      return `postgresql://${host}:${port}`;
    }
  }
});
```

### `AppYamlConfig.getInstance(): AppYamlConfig`

Get the singleton instance. Throws `ConfigNotInitializedError` if not initialized.

```typescript
const config = AppYamlConfig.getInstance();
```

### `config.get<T>(key: string, defaultValue?: T): T | undefined`

Get a top-level configuration value.

```typescript
const name = config.get('appName');
const port = config.get('port', 8080); // with default
```

### `config.getNested<T>(keys: string[], defaultValue?: T): T | undefined`

Get a nested configuration value using a key path.

```typescript
const dbHost = config.getNested(['database', 'host']);
const timeout = config.getNested(['server', 'timeout'], 30000);
```

### `config.getComputed<T>(key: string): T`

Get a computed value. Throws `ComputedKeyNotFoundError` if key not defined.

```typescript
const dbUrl = config.getComputed('dbUrl');
```

### `config.getAll(): Record<string, any>`

Get a deep copy of all configuration data.

```typescript
const allConfig = config.getAll();
```

### `config.isInitialized(): boolean`

Check if the configuration has been initialized.

```typescript
if (config.isInitialized()) {
  // safe to use
}
```

### `config.getLoadResult(): LoadResult | null`

Get metadata about the loaded configuration files.

```typescript
const result = config.getLoadResult();
console.log(result.filesLoaded);  // ['base.yml', 'server.dev.yaml']
console.log(result.appEnv);       // 'dev'
```

## File Resolution

Files are resolved in the following order:

1. **{APP_ENV} Substitution**: `server.{APP_ENV}.yaml` becomes `server.dev.yaml`
2. **Relative Path Resolution**: Resolved against `configDir` if provided
3. **Environment Override**: If `config.dev.yaml` exists, it's used instead of `config.yaml`

### Example

Given:
- `configDir: './config'`
- `appEnv: 'dev'`
- `files: ['base.yml', 'server.{APP_ENV}.yaml']`

Resolution:
1. `base.yml` → `./config/base.yml` (or `./config/base.dev.yml` if exists)
2. `server.{APP_ENV}.yaml` → `./config/server.dev.yaml`

## Deep Merge Behavior

When loading multiple files, objects are deep merged while **arrays are replaced** (not concatenated).

```yaml
# base.yml
server:
  host: localhost
  ports: [3000]

# server.dev.yaml
server:
  port: 8080
  ports: [8080, 8081]
```

Result:
```yaml
server:
  host: localhost    # from base.yml
  port: 8080         # from server.dev.yaml
  ports: [8080, 8081] # replaced, not concatenated
```

## Computed Values

Computed values are lazily evaluated and cached. They can depend on other config values or other computed values.

```typescript
await AppYamlConfig.initialize({
  files: ['config.yml'],
  computedDefinitions: {
    dbUrl: (config) => {
      const { host, port, name } = config.getNested(['database']);
      return `postgresql://${host}:${port}/${name}`;
    },
    apiEndpoint: (config) => {
      const base = config.get('apiBase');
      const version = config.get('apiVersion', 'v1');
      return `${base}/${version}`;
    }
  }
});

const config = AppYamlConfig.getInstance();
const dbUrl = config.getComputed('dbUrl');
```

### Circular Dependency Detection

Circular dependencies are detected and will throw `CircularDependencyError`:

```typescript
computedDefinitions: {
  A: (c) => c.getComputed('B'),
  B: (c) => c.getComputed('A')  // Circular!
}
```

## Error Types

| Error | Description |
|-------|-------------|
| `ConfigNotInitializedError` | `getInstance()` called before `initialize()` |
| `ConfigAlreadyInitializedError` | Reserved for strict re-initialization handling |
| `ValidationError` | YAML parsing failed |
| `ComputedKeyNotFoundError` | Computed key not defined |
| `CircularDependencyError` | Circular dependency in computed values |

## Usage with Fastify/Express

```typescript
// config/index.ts
import { AppYamlConfig } from '@internal/app-yaml-config';
import path from 'path';

export async function loadConfig() {
  await AppYamlConfig.initialize({
    files: ['base.yml', 'server.{APP_ENV}.yaml'],
    configDir: path.join(__dirname),
  });
}

export function getConfig() {
  return AppYamlConfig.getInstance();
}
```

```typescript
// index.ts
import { loadConfig, getConfig } from './config';

async function main() {
  await loadConfig();

  const config = getConfig();
  const port = config.getNested(['server', 'port'], 3000);

  app.listen(port);
}
```

## Testing

For testing, use `_resetForTesting()` to reset the singleton between tests:

```typescript
beforeEach(() => {
  AppYamlConfig._resetForTesting();
});
```

## TypeScript Support

Full TypeScript support with generics for type-safe access:

```typescript
interface DatabaseConfig {
  host: string;
  port: number;
}

const dbConfig = config.getNested<DatabaseConfig>(['database']);
```

## License

MIT
