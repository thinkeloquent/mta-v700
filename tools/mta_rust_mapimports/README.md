# MTA Rust MapImports

A high-performance Rust CLI tool that scans Python and Node.js/TypeScript projects to map all imports, categorize them, and extract dependency versions.

## Features

- **Multi-language support**: Python (.py, .pyi), JavaScript (.js, .mjs, .cjs, .jsx), TypeScript (.ts, .mts, .cts, .tsx)
- **Import categorization**: External (npm/pypi), Internal (workspace), Local (relative), Stdlib, Unknown
- **Manifest parsing**: package.json, pyproject.toml (Poetry/PEP 621), requirements.txt
- **Output formats**: JSON, YAML, Summary
- **Fast**: Parallel processing with ~1400+ files/sec
- **Gitignore support**: Respects .gitignore and custom ignore patterns

## Installation

### From source (recommended)

```bash
# From the project root (mta-v700)
cd /path/to/mta-v700

# Install globally using cargo
cargo install --path tools/mta_rust_mapimports/crates/cli

# Or from within the tool directory
cd tools/mta_rust_mapimports
cargo install --path crates/cli

# Verify installation
mapimports --version
```

### Build locally without installing

```bash
cd tools/mta_rust_mapimports

# Debug build
cargo build

# Release build (optimized)
cargo build --release

# Run directly
./target/release/mapimports --help
```

## Usage

### Basic Commands

```bash
# Scan current directory (JSON output to stdout)
mapimports

# Scan specific directory
mapimports /path/to/project

# Output in different formats
mapimports --format json      # JSON (default)
mapimports --format yaml      # YAML
mapimports --format summary   # Human-readable summary
```

### Filtering

```bash
# Scan only Python files
mapimports --language python

# Scan only JavaScript/TypeScript files
mapimports --language node

# Show only external dependencies with versions
mapimports --deps-only

# Show only unresolved/unknown imports
mapimports --unknown-only
```

### Output Options

```bash
# Save to file
mapimports --output imports.json

# Save YAML to file
mapimports --format yaml --output imports.yaml
```

### Ignore Patterns

```bash
# Add custom ignore patterns (gitignore style)
mapimports --ignore "*.test.*" --ignore "__tests__/*"

# Use custom ignore file
mapimports --ignore-file .customignore

# Include node_modules and .venv (normally excluded)
mapimports --include-deps
```

### Performance Options

```bash
# Show progress spinner
mapimports --verbose

# Set number of threads (0 = auto)
mapimports --threads 4
```

## Example Output

### Summary Format

```
Import Analysis Summary
=======================
Root: /path/to/project

Files Scanned: 116
- Python: 116
- JavaScript: 0
- TypeScript: 0

Total Imports: 420
- External: 45
- Internal: 37
- Local: 158
- Stdlib: 175
- Unknown: 5

External Dependencies:
  fastapi @ ^0.100.0
  httpx @ >=0.24.0
  pydantic @ ^2.0.0
  redis @ >=4.5.0

Internal Packages:
  fetch_client
  db_connection_postgres
  vault_file

Scan Duration: 83ms (1393.70 files/sec)
```

### JSON Format (truncated)

```json
{
  "root": "/path/to/project",
  "files": [
    {
      "path": "src/main.py",
      "language": "python",
      "imports": [
        {
          "module": "fastapi",
          "items": ["FastAPI", "Request"],
          "import_type": "external",
          "line": 1
        }
      ]
    }
  ],
  "external_dependencies": {
    "fastapi": {
      "name": "fastapi",
      "version": "^0.100.0",
      "source": "pyproject.toml"
    }
  },
  "stats": {
    "total_files": 116,
    "total_imports": 420,
    "external_imports": 45
  }
}
```

## Import Categorization

| Category | Description | Examples |
|----------|-------------|----------|
| **External** | Packages from npm/pypi | `fastapi`, `express`, `@fastify/cors` |
| **Internal** | Workspace packages | `@internal/utils`, `fetch_client` |
| **Local** | Relative imports | `./utils`, `../config`, `.` |
| **Stdlib** | Standard library | `os`, `sys`, `fs`, `path` |
| **Unknown** | Unresolved imports | Not in manifests or stdlib |

## Default Ignore Patterns

The following are ignored by default (override with `--include-deps`):

- `**/node_modules/**`
- `**/.venv/**`, `**/venv/**`
- `**/__pycache__/**`
- `**/dist/**`, `**/build/**`
- `**/.git/**`, `**/target/**`

## Development

### Run Tests

```bash
cd tools/mta_rust_mapimports
cargo test
```

### Project Structure

```
tools/mta_rust_mapimports/
├── Cargo.toml              # Workspace configuration
├── crates/
│   ├── core/               # Core library
│   │   └── src/
│   │       ├── lib.rs
│   │       ├── models.rs       # Data structures
│   │       ├── config.rs       # Configuration
│   │       ├── scanner.rs      # File scanning
│   │       ├── categorizer.rs  # Import classification
│   │       ├── parsers/        # AST parsers (tree-sitter)
│   │       ├── manifest/       # Manifest parsers
│   │       └── output/         # Output formatters
│   ├── cli/                # CLI binary
│   └── wasm/               # WASM bindings (future)
```

## License

MIT
