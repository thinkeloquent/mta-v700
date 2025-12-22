# app-yaml-config

A singleton YAML configuration loader for Python applications with support for environment-specific overrides, deep merging, and computed values.

## Installation

```bash
pip install app-yaml-config
```

Or with Poetry:

```bash
poetry add app-yaml-config
```

## Features

- **Singleton Pattern**: Single source of truth for application configuration
- **YAML Support**: Load configuration from `.yaml` / `.yml` files
- **Environment-Specific Overrides**: Automatic loading of `{name}.{env}.yaml` files
- **Deep Merging**: Merge multiple config files with array replacement (not concatenation)
- **Computed Values**: Define derived values with circular dependency detection
- **APP_ENV Support**: Automatic `{APP_ENV}` placeholder substitution (converted to lowercase)
- **Immutable**: Configuration cannot be modified after initialization

## Quick Start

```python
from app_yaml_config import AppYamlConfig

# Initialize (typically at app startup)
AppYamlConfig.initialize(
    files=['base.yml', 'server.{APP_ENV}.yaml'],
    config_dir='./config',
)

# Access configuration anywhere in your app
config = AppYamlConfig.get_instance()

# Get a top-level value
app_name = config.get('app')

# Get a nested value
db_host = config.get_nested('database', 'host')

# Get with default
port = config.get('port', 3000)
```

## API Reference

### `AppYamlConfig.initialize(files, config_dir=None, app_env=None, computed_definitions=None)`

Initialize the configuration singleton. Must be called before `get_instance()`.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `files` | `List[str]` | Yes | List of config files to load (in order) |
| `config_dir` | `str` | No | Base directory for resolving relative paths |
| `app_env` | `str` | No | Environment name (defaults to `os.getenv('APP_ENV', 'dev')`) |
| `computed_definitions` | `Dict[str, Callable]` | No | Map of computed value definitions |

#### Returns

`AppYamlConfig` - The initialized singleton instance.

#### Example

```python
from app_yaml_config import AppYamlConfig

def db_url(config):
    host = config.get_nested('db', 'host')
    port = config.get_nested('db', 'port')
    return f"postgresql://{host}:{port}"

AppYamlConfig.initialize(
    files=['base.yml', 'server.{APP_ENV}.yaml'],
    config_dir='/app/config',
    app_env='production',
    computed_definitions={
        'db_url': db_url
    }
)
```

### `AppYamlConfig.get_instance()`

Get the singleton instance. Raises `ConfigNotInitializedError` if not initialized.

```python
config = AppYamlConfig.get_instance()
```

### `config.get(key, default=None)`

Get a top-level configuration value.

```python
name = config.get('app_name')
port = config.get('port', 8080)  # with default
```

### `config.get_nested(*keys, default=None)`

Get a nested configuration value using variadic keys.

```python
db_host = config.get_nested('database', 'host')
timeout = config.get_nested('server', 'timeout', default=30000)
```

### `config.get_computed(key)`

Get a computed value. Raises `ComputedKeyNotFoundError` if key not defined.

```python
db_url = config.get_computed('db_url')
```

### `config.get_all()`

Get a deep copy of all configuration data.

```python
all_config = config.get_all()
```

### `config.is_initialized()`

Check if the configuration has been initialized.

```python
if config.is_initialized():
    # safe to use
    pass
```

### `config.get_load_result()`

Get metadata about the loaded configuration files.

```python
result = config.get_load_result()
print(result.files_loaded)  # ['base.yml', 'server.dev.yaml']
print(result.app_env)       # 'dev'
print(result.merge_order)   # ['base.yml', 'server.dev.yaml']
```

## File Resolution

Files are resolved in the following order:

1. **{APP_ENV} Substitution**: `server.{APP_ENV}.yaml` becomes `server.dev.yaml`
2. **Relative Path Resolution**: Resolved against `config_dir` if provided
3. **Environment Override**: If `config.dev.yaml` exists, it's used instead of `config.yaml`

### Example

Given:
- `config_dir='./config'`
- `app_env='dev'`
- `files=['base.yml', 'server.{APP_ENV}.yaml']`

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
  host: localhost     # from base.yml
  port: 8080          # from server.dev.yaml
  ports: [8080, 8081] # replaced, not concatenated
```

## Computed Values

Computed values are lazily evaluated and cached. They can depend on other config values or other computed values.

```python
from app_yaml_config import AppYamlConfig

def db_url(config):
    db = config.get('database', {})
    return f"postgresql://{db.get('host')}:{db.get('port')}/{db.get('name')}"

def api_endpoint(config):
    base = config.get('api_base')
    version = config.get('api_version', 'v1')
    return f"{base}/{version}"

AppYamlConfig.initialize(
    files=['config.yml'],
    computed_definitions={
        'db_url': db_url,
        'api_endpoint': api_endpoint,
    }
)

config = AppYamlConfig.get_instance()
print(config.get_computed('db_url'))
```

### Computed Value Dependencies

Computed values can depend on other computed values:

```python
computed_definitions = {
    'x2': lambda c: c.get('base') * 2,
    'x4': lambda c: c.get_computed('x2') * 2,  # depends on x2
}
```

### Circular Dependency Detection

Circular dependencies are detected and will raise `CircularDependencyError`:

```python
computed_definitions = {
    'A': lambda c: c.get_computed('B'),
    'B': lambda c: c.get_computed('A'),  # Circular!
}
```

## Immutability

The configuration is immutable after initialization. These methods will raise `NotImplementedError`:

```python
config.set('key', 'value')   # NotImplementedError
config.update({'key': 'v'})  # NotImplementedError
config.reset()               # NotImplementedError
config.clear()               # NotImplementedError
```

## Error Types

| Error | Description |
|-------|-------------|
| `ConfigNotInitializedError` | `get_instance()` or `get_computed()` called before `initialize()` |
| `ConfigAlreadyInitializedError` | Reserved for strict re-initialization handling |
| `ValidationError` | YAML parsing failed |
| `ComputedKeyNotFoundError` | Computed key not defined |
| `CircularDependencyError` | Circular dependency in computed values |
| `FileNotFoundError` | Config file not found |

## Usage with FastAPI

```python
# config.py
from app_yaml_config import AppYamlConfig
import os

def load_config():
    config_dir = os.path.join(os.path.dirname(__file__), 'config')
    AppYamlConfig.initialize(
        files=['base.yml', 'server.{APP_ENV}.yaml'],
        config_dir=config_dir,
    )

def get_config():
    return AppYamlConfig.get_instance()
```

```python
# main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager
from config import load_config, get_config

@asynccontextmanager
async def lifespan(app: FastAPI):
    load_config()
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    config = get_config()
    return {"app": config.get_nested('app', 'name')}
```

## Testing

For testing, use `_reset_for_testing()` to reset the singleton between tests:

```python
import pytest
from app_yaml_config import AppYamlConfig

@pytest.fixture(autouse=True)
def reset_config():
    instance = AppYamlConfig()
    instance._reset_for_testing()
    yield
    instance._reset_for_testing()
```

## Type Hints

Full type hint support:

```python
from typing import Dict, Any
from app_yaml_config import AppYamlConfig, ComputedDefinition

def my_computed(config: AppYamlConfig) -> str:
    return f"computed-{config.get('value')}"

definitions: Dict[str, ComputedDefinition] = {
    'my_key': my_computed
}
```

## Data Classes

### LoadResult

```python
@dataclass
class LoadResult:
    files_loaded: List[str]      # Successfully loaded files
    errors: List[Dict[str, Any]] # Any errors encountered
    app_env: Optional[str]       # Resolved environment
    merge_order: List[str]       # Order files were merged
```

## Dependencies

- `pyyaml>=6.0` - YAML parsing
- `python-dotenv>=1.0.0` - Environment variable support
- `deepmerge>=1.1.0` - Deep merge utilities

## License

MIT
