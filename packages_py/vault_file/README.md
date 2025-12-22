# vault-file

A secure environment variable loader and vault file manager for Python applications. Provides singleton access to environment variables with support for `.env` files, directory loading, computed values, and structured vault files.

## Installation

```bash
pip install vault-file
```

Or with Poetry:

```bash
poetry add vault-file
```

## Features

- **EnvStore**: Singleton environment variable manager
- **VaultFile**: Structured JSON file format with header, metadata, and payload
- **Directory Loading**: Load multiple `.env*` files from a directory using glob patterns
- **Computed Values**: Define derived values with lazy evaluation and caching
- **Atomic Writes**: Safe file operations with atomic disk writes
- **os.environ Integration**: Seamless integration with Python's environment

## Quick Start

### EnvStore - Environment Variable Loading

```python
from vault_file import EnvStore

# Load at startup
EnvStore.on_startup('/path/to/vault.env')

# Access anywhere in your app (singleton)
store = EnvStore()

# Get a value (checks internal store first, then os.environ)
api_key = store.get('API_KEY')

# Get or throw if not found
db_url = store.get_or_throw('DATABASE_URL')
```

### VaultFile - Structured Configuration

```python
from vault_file import VaultFile, VaultHeader, VaultMetadata, VaultPayload

# Create a new vault file
vault = VaultFile(
    header={'version': '1.0'},
    metadata={'data': {'environment': 'production'}},
    payload={'data': {'secrets': {'api_key': '...'}}}
)

# Serialize to JSON
json_str = vault.to_json()

# Parse from JSON
loaded = VaultFile.from_json(json_str)

# Save to disk (atomic write)
vault.save_to_disk('/path/to/vault.json')

# Load from disk
vault = VaultFile.load_from_disk('/path/to/vault.json')
```

## API Reference

### EnvStore

#### `EnvStore()`

Get the singleton instance. Uses `__new__` for singleton pattern.

```python
store = EnvStore()
```

#### `EnvStore.on_startup(location, pattern='.env*', override=False, computed_definitions=None)`

Class method to initialize and load environment variables at application startup.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `location` | `str` | required | Path to file or directory |
| `pattern` | `str` | `'.env*'` | Glob pattern for directory loading |
| `override` | `bool` | `False` | Override existing variables |
| `computed_definitions` | `Dict[str, Callable]` | `None` | Computed value definitions |

```python
EnvStore.on_startup(
    '/app/config',
    pattern='.env*',
    override=False,
    computed_definitions={
        'db_url': lambda store: f"postgresql://{store.get('DB_HOST')}:{store.get('DB_PORT')}"
    }
)
```

#### `store.load(location, pattern='.env*', override=False, computed_definitions=None)`

Load environment variables from a file or directory.

```python
result = store.load('/app/.env')
print(result.files_loaded)      # ['/app/.env']
print(result.errors)            # []
print(result.total_vars_loaded) # 15
```

#### `store.get(key)`

Get an environment variable. Checks internal store first, then `os.environ`.

```python
api_key = store.get('API_KEY')  # Returns None if not found
```

#### `store.get_or_throw(key)`

Get an environment variable or raise `EnvKeyNotFoundError` if not found.

```python
api_key = store.get_or_throw('API_KEY')
# Raises: EnvKeyNotFoundError: Environment variable 'API_KEY' not found
```

#### `store.get_computed(key)`

Get a computed value. Raises `KeyError` if key not defined.

```python
db_url = store.get_computed('db_url')
```

#### `store.get_all()`

Get all environment variables (merged `os.environ` + internal store).

```python
all_vars = store.get_all()
```

#### `store.get_load_result()`

Get metadata about loaded files.

```python
info = store.get_load_result()
print(info['loaded_files'])  # ['/app/.env', '/app/.env.local']
print(info['store_size'])    # 15
```

#### `store.is_initialized()`

Check if the store has been initialized.

```python
if store.is_initialized():
    # safe to use
    pass
```

#### `store.reset()`

Reset the store (clear all loaded variables).

```python
store.reset()
```

### Global `env` Export

A pre-initialized singleton instance is exported for convenience:

```python
from vault_file import env

api_key = env.get('API_KEY')
```

### VaultFile

#### `VaultFile(header=None, metadata=None, payload=None)`

Create a new vault file with optional initial values. Accepts dataclass instances or dictionaries.

```python
# Using dictionaries
vault = VaultFile(
    header={'id': 'custom-id', 'version': '2.0'},
    metadata={'data': {'env': 'prod'}},
    payload={'data': {'secret': 'value'}}
)

# Using dataclasses
from vault_file import VaultHeader, VaultMetadata, VaultPayload

vault = VaultFile(
    header=VaultHeader(version='2.0'),
    metadata=VaultMetadata(data={'env': 'prod'}),
    payload=VaultPayload(data={'secret': 'value'})
)
```

Default values:
- `header.id`: Auto-generated UUID v4
- `header.version`: `'1.0'`
- `header.created_at`: Current UTC datetime
- `metadata.data`: `{}`
- `payload.data`: `None`

#### `vault.to_json()`

Serialize to formatted JSON string.

```python
json_str = vault.to_json()
# {
#   "header": { "id": "...", "version": "1.0", "created_at": "..." },
#   "metadata": { "data": {} },
#   "payload": { "data": null }
# }
```

#### `vault.to_dict()`

Convert to dictionary.

```python
data = vault.to_dict()
```

#### `VaultFile.from_json(json_str)`

Parse and validate a vault file from JSON string.

```python
vault = VaultFile.from_json(json_string)
```

Raises:
- `VaultSerializationError` if JSON is invalid or validation fails

#### `vault.save_to_disk(path)`

Atomically save vault file to disk. Creates parent directories if needed.

```python
vault.save_to_disk('/path/to/vault.json')
```

#### `VaultFile.load_from_disk(path)`

Load vault file from disk.

```python
vault = VaultFile.load_from_disk('/path/to/vault.json')
```

Raises:
- `FileNotFoundError` if file doesn't exist
- `VaultSerializationError` if JSON is invalid

#### `vault.update(header=None, metadata=None, payload=None)`

Update this instance with partial data. Returns the instance for chaining.

```python
vault.update(
    header={'version': '2.0'},
    metadata={'data': {'updated': True}},
    payload={'data': {'new_data': 'value'}}
)
```

- `header`: Selectively merged (only provided fields are updated)
- `metadata['data']`: Replaced entirely if provided
- `payload['data']`: Replaced entirely if provided

#### `vault.merge(other)`

Deep merge another VaultFile into this instance. Returns the instance for chaining.

```python
base = VaultFile(
    header={'version': '1.0'},
    metadata={'data': {'a': 1}}
)
updates = VaultFile(
    header={'version': '2.0'},
    metadata={'data': {'b': 2}}
)

base.merge(updates)
# base.header.version == '2.0'
# base.metadata.data == {'a': 1, 'b': 2}
```

Merge behavior:
- `header`: Other's fields override this (except `id` is preserved)
- `metadata.data`: Deep merged (other overrides conflicts)
- `payload.data`: Replaced by other's data (if not None)

#### `vault.merge_from_json(json_str)`

Convenience method to parse JSON and merge into this instance.

```python
vault.merge_from_json('{"header": {"version": "2.0"}, ...}')
```

#### `VaultFile.from_base64_file(data_uri)`

Parse a VaultFile from a base64-encoded data URI.

```python
data_uri = 'data:application/json;base64,eyJoZWFkZXIiOi4uLn0='
vault = VaultFile.from_base64_file(data_uri)
```

Format: `data:application/json;base64,<BASE64 Encoded String>`

Raises:
- `VaultSerializationError` if prefix is invalid or base64 decoding fails

#### `vault.to_base64_file()`

Serialize this VaultFile to a base64-encoded data URI.

```python
vault = VaultFile(
    header={'version': '1.0'},
    metadata={'data': {'env': 'prod'}},
    payload={'data': {'secret': 'value'}}
)

data_uri = vault.to_base64_file()
# -> "data:application/json;base64,eyJoZWFkZXIiOnsi..."
```

This is useful for:
- Embedding vault data in environment variables
- Passing vault data through URLs or headers
- Storing vault data in systems that prefer base64 encoding

## Data Classes

### VaultHeader

```python
@dataclass
class VaultHeader:
    id: str           # UUID v4 (auto-generated)
    version: str      # Version string (default: '1.0')
    created_at: datetime  # UTC timestamp (auto-generated)
```

### VaultMetadata

```python
@dataclass
class VaultMetadata:
    data: Dict[str, Any]  # Arbitrary metadata (default: {})
```

### VaultPayload

```python
@dataclass
class VaultPayload:
    data: Any  # Payload content (default: None)
```

### LoadResult

```python
@dataclass
class LoadResult:
    files_loaded: List[str]        # Successfully loaded files
    errors: List[Dict[str, Any]]   # Errors encountered
    total_vars_loaded: int         # Total variables loaded
```

## Error Types

| Error | Description |
|-------|-------------|
| `VaultValidationError` | Schema validation failed |
| `VaultSerializationError` | JSON parsing or serialization failed |
| `EnvKeyNotFoundError` | Environment variable not found (get_or_throw) |

## Computed Values

Define computed values that derive from environment variables:

```python
from vault_file import EnvStore

def db_url(store: EnvStore) -> str:
    host = store.get('DB_HOST') or 'localhost'
    port = store.get('DB_PORT') or '5432'
    name = store.get('DB_NAME') or 'app'
    return f"postgresql://{host}:{port}/{name}"

def db_pool_size(store: EnvStore) -> int:
    return int(store.get('DB_POOL_SIZE') or '10')

def redis_config(store: EnvStore) -> dict:
    return {
        'host': store.get('REDIS_HOST'),
        'port': int(store.get('REDIS_PORT') or '6379'),
        'password': store.get('REDIS_PASSWORD'),
    }

EnvStore.on_startup(
    '/app/.env',
    computed_definitions={
        'db_url': db_url,
        'db_pool_size': db_pool_size,
        'redis_config': redis_config,
    }
)

store = EnvStore()
print(store.get_computed('db_url'))       # postgresql://localhost:5432/app
print(store.get_computed('db_pool_size')) # 10
print(store.get_computed('redis_config')) # {'host': ..., 'port': 6379, ...}
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

```python
# Loads all .env* files in sorted order
EnvStore.on_startup('./config', pattern='.env*')

# Custom pattern
EnvStore.on_startup('./config', pattern='.env.dev')
```

Files are loaded in sorted order. With `override=True`, later files override earlier ones.

## Usage with FastAPI

```python
# env.py
from vault_file import EnvStore
import os

def load_env():
    vault_file = os.getenv('VAULT_SECRET_FILE')
    if vault_file:
        EnvStore.on_startup(vault_file)

def get_env() -> EnvStore:
    return EnvStore()
```

```python
# main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager
from env import load_env, get_env

@asynccontextmanager
async def lifespan(app: FastAPI):
    load_env()
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    env = get_env()
    return {"db_host": env.get('DB_HOST')}
```

## Atomic File Operations

The `save_to_disk` method uses atomic writes to prevent data corruption:

1. Writes to a temporary file in the same directory
2. Uses `os.replace()` for atomic rename
3. Cleans up temp file on failure

```python
vault = VaultFile(payload={'data': {'important': 'data'}})
vault.save_to_disk('/path/to/vault.json')  # Safe even on crash
```

## Type Hints

Full type hint support:

```python
from typing import Dict, Any, Optional
from vault_file import EnvStore, ComputedDefinition

def my_computed(store: EnvStore) -> str:
    return f"computed-{store.get('value')}"

definitions: Dict[str, ComputedDefinition] = {
    'my_key': my_computed
}
```

## Dependencies

- `python-dotenv>=1.0.0` - Parse `.env` files
- `pydantic>=2.0.0` - Data validation

## License

MIT
