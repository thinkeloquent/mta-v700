# @internal/vault-file

A secure environment variable loader and vault file manager for Node.js/TypeScript applications. Provides singleton access to environment variables with support for `.env` files, directory loading, computed values, and structured vault files.

## Installation

```bash
npm install @internal/vault-file
```

## Features

- **EnvStore**: Singleton environment variable manager
- **VaultFile**: Structured JSON file format with header, metadata, and payload
- **Directory Loading**: Load multiple `.env*` files from a directory using glob patterns
- **Computed Values**: Define derived values with lazy evaluation and caching
- **Zod Validation**: Schema validation for vault files
- **process.env Integration**: Seamless integration with Node.js environment

## Quick Start

### EnvStore - Environment Variable Loading

```typescript
import { EnvStore } from '@internal/vault-file';

// Load at startup
await EnvStore.onStartup('/path/to/vault.env');

// Access anywhere in your app
const store = EnvStore.getInstance();

// Get a value (checks process.env first, then internal store)
const apiKey = store.get('API_KEY');

// Get or throw if not found
const dbUrl = store.getOrThrow('DATABASE_URL');
```

### VaultFile - Structured Configuration

```typescript
import { VaultFile } from '@internal/vault-file';

// Create a new vault file
const vault = new VaultFile(
  { version: '1.0.0' },
  { data: { environment: 'production' } },
  { content: { secrets: { apiKey: '...' } } }
);

// Serialize to JSON
const json = vault.toJSON();

// Parse from JSON
const loaded = VaultFile.fromJSON(json);
```

## API Reference

### EnvStore

#### `EnvStore.getInstance(): EnvStore`

Get the singleton instance.

```typescript
const store = EnvStore.getInstance();
```

#### `EnvStore.onStartup(location, pattern?, override?, computedDefinitions?): Promise<EnvStore>`

Initialize and load environment variables at application startup.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `location` | `string` | required | Path to file or directory |
| `pattern` | `string` | `'.env*'` | Glob pattern for directory loading |
| `override` | `boolean` | `false` | Override existing variables |
| `computedDefinitions` | `ComputedRegistry` | `{}` | Computed value definitions |

```typescript
await EnvStore.onStartup('/app/config', '.env*', false, {
  dbUrl: (store) => `postgresql://${store.get('DB_HOST')}:${store.get('DB_PORT')}`
});
```

#### `store.load(location, pattern?, override?, computedDefinitions?): LoadResult`

Load environment variables from a file or directory.

```typescript
const result = store.load('/app/.env');
console.log(result.loaded);  // ['/app/.env']
console.log(result.errors);  // []
```

#### `store.get(key): string | undefined`

Get an environment variable. Checks `process.env` first, then internal store.

```typescript
const apiKey = store.get('API_KEY');
```

#### `store.getOrThrow(key): string`

Get an environment variable or throw if not found.

```typescript
const apiKey = store.getOrThrow('API_KEY');
// Throws: Error: Environment variable 'API_KEY' not found
```

#### `store.getComputed<T>(key): T`

Get a computed value. Throws if key not defined.

```typescript
const dbUrl = store.getComputed<string>('dbUrl');
```

#### `store.getAll(): Record<string, string>`

Get all environment variables (merged internal store + process.env).

```typescript
const all = store.getAll();
```

#### `store.getLoadResult(): { loadedFiles: string[], storeSize: number }`

Get metadata about loaded files.

```typescript
const info = store.getLoadResult();
console.log(info.loadedFiles);  // ['/app/.env', '/app/.env.local']
console.log(info.storeSize);    // 15
```

#### `store.isInitialized(): boolean`

Check if the store has been initialized.

```typescript
if (store.isInitialized()) {
  // safe to use
}
```

#### `store.reset(): void`

Reset the store (clear all loaded variables).

```typescript
store.reset();
```

### Global `env` Export

A pre-initialized singleton instance is exported for convenience:

```typescript
import { env } from '@internal/vault-file';

const apiKey = env.get('API_KEY');
```

### VaultFile

#### `new VaultFile(header?, metadata?, payload?)`

Create a new vault file with optional initial values.

```typescript
const vault = new VaultFile(
  { id: 'custom-id', version: '2.0.0' },
  { data: { env: 'prod' } },
  { content: { secret: 'value' } }
);
```

Default values:
- `header.id`: Auto-generated UUID v4
- `header.version`: `'1.0.0'`
- `header.createdAt`: Current ISO timestamp
- `metadata.data`: `{}`
- `payload.content`: `null`

#### `vault.toJSON(): string`

Serialize to formatted JSON string.

```typescript
const json = vault.toJSON();
// {
//   "header": { "id": "...", "version": "1.0.0", "createdAt": "..." },
//   "metadata": { "data": {} },
//   "payload": { "content": null }
// }
```

#### `VaultFile.fromJSON(jsonStr): VaultFile`

Parse and validate a vault file from JSON string.

```typescript
const vault = VaultFile.fromJSON(jsonString);
```

Throws:
- `VaultSerializationError` if JSON is invalid
- `VaultValidationError` if schema validation fails

#### `vault.validateState(): void`

Validate the current state against the schema.

```typescript
vault.validateState(); // Throws VaultValidationError if invalid
```

#### `vault.update(options): this`

Update this instance with partial data. Returns the instance for chaining.

```typescript
vault.update({
  header: { version: '2.0.0' },
  metadata: { data: { updated: true } },
  payload: { content: { newData: 'value' } }
});
```

- `header`: Selectively merged (only provided fields are updated)
- `metadata.data`: Replaced entirely if provided
- `payload.content`: Replaced entirely if provided

#### `vault.merge(other): this`

Deep merge another VaultFile into this instance. Returns the instance for chaining.

```typescript
const base = new VaultFile({ version: '1.0.0' }, { data: { a: 1 } });
const updates = new VaultFile({ version: '2.0.0' }, { data: { b: 2 } });

base.merge(updates);
// base.header.version === '2.0.0'
// base.metadata.data === { a: 1, b: 2 }
```

Merge behavior:
- `header`: Other's fields override this (except `id` is preserved)
- `metadata.data`: Deep merged (other overrides conflicts)
- `payload.content`: Replaced by other's content (if not null)

#### `vault.mergeFromJSON(jsonStr): this`

Convenience method to parse JSON and merge into this instance.

```typescript
vault.mergeFromJSON('{"header": {"version": "2.0.0"}, ...}');
```

#### `VaultFile.fromBase64File(dataUri): VaultFile`

Parse a VaultFile from a base64-encoded data URI.

```typescript
const dataUri = 'data:application/json;base64,eyJoZWFkZXIiOi4uLn0=';
const vault = VaultFile.fromBase64File(dataUri);
```

Format: `data:application/json;base64,<BASE64 Encoded String>`

Throws:
- `VaultSerializationError` if prefix is invalid or base64 decoding fails

#### `vault.toBase64File(): string`

Serialize this VaultFile to a base64-encoded data URI.

```typescript
const vault = new VaultFile(
  { version: '1.0.0' },
  { data: { env: 'prod' } },
  { content: { secret: 'value' } }
);

const dataUri = vault.toBase64File();
// -> "data:application/json;base64,eyJoZWFkZXIiOnsi..."
```

This is useful for:
- Embedding vault data in environment variables
- Passing vault data through URLs or headers
- Storing vault data in systems that prefer base64 encoding

## Data Types

### LoadResult

```typescript
interface LoadResult {
  loaded: string[];                           // Successfully loaded files
  errors: Array<{ file: string; error: string }>; // Errors encountered
}
```

### VaultHeader

```typescript
interface VaultHeader {
  id: string;        // UUID v4
  version: string;   // Semantic version (e.g., '1.0.0')
  createdAt: string; // ISO 8601 timestamp
}
```

### VaultMetadata

```typescript
interface VaultMetadata {
  data: Record<string, any>;
}
```

### VaultPayload

```typescript
interface VaultPayload {
  content: any;
}
```

### ComputedRegistry

```typescript
type ComputedDefinition = (store: EnvStore) => any;
type ComputedRegistry = Record<string, ComputedDefinition>;
```

## Error Types

| Error | Description |
|-------|-------------|
| `VaultValidationError` | Schema validation failed |
| `VaultSerializationError` | JSON parsing or serialization failed |

## Computed Values

Define computed values that derive from environment variables:

```typescript
await EnvStore.onStartup('/app/.env', '.env*', false, {
  // Simple computed value
  dbUrl: (store) => {
    const host = store.get('DB_HOST') || 'localhost';
    const port = store.get('DB_PORT') || '5432';
    const name = store.get('DB_NAME') || 'app';
    return `postgresql://${host}:${port}/${name}`;
  },

  // Computed with parsing
  dbPoolSize: (store) => {
    return parseInt(store.get('DB_POOL_SIZE') || '10', 10);
  },

  // Computed object
  redisConfig: (store) => ({
    host: store.get('REDIS_HOST'),
    port: parseInt(store.get('REDIS_PORT') || '6379', 10),
    password: store.get('REDIS_PASSWORD'),
  }),
});

const store = EnvStore.getInstance();
const dbUrl = store.getComputed<string>('dbUrl');
const poolSize = store.getComputed<number>('dbPoolSize');
const redis = store.getComputed<{ host: string; port: number; password?: string }>('redisConfig');
```

## Directory Loading

Load multiple `.env` files from a directory:

```
config/
├── .env           # Base config
├── .env.local     # Local overrides
├── .env.dev       # Development config
└── .env.prod      # Production config
```

```typescript
// Loads all .env* files in sorted order
await EnvStore.onStartup('./config', '.env*');

// Custom pattern
await EnvStore.onStartup('./config', '.env.{dev,prod}');
```

Files are loaded in sorted order, with later files overriding earlier ones (when `override: true`).

## Usage with Fastify/Express

```typescript
// env.ts
import { EnvStore } from '@internal/vault-file';

export async function loadEnv() {
  const vaultFile = process.env.VAULT_SECRET_FILE;
  if (vaultFile) {
    await EnvStore.onStartup(vaultFile);
  }
}

export function getEnv() {
  return EnvStore.getInstance();
}
```

```typescript
// index.ts
import { loadEnv, getEnv } from './env';

async function main() {
  await loadEnv();

  const env = getEnv();
  const port = parseInt(env.get('PORT') || '3000', 10);

  app.listen(port);
}
```

## Validation Schemas (Zod)

The package exports Zod schemas for custom validation:

```typescript
import {
  VaultHeaderSchema,
  VaultMetadataSchema,
  VaultPayloadSchema,
  VaultFileSchema
} from '@internal/vault-file';

// Validate custom data
const result = VaultFileSchema.safeParse(data);
if (!result.success) {
  console.error(result.error);
}
```

## Dependencies

- `dotenv` - Parse `.env` files
- `glob` - File pattern matching
- `uuid` - Generate UUIDs
- `zod` - Schema validation

## License

MIT
