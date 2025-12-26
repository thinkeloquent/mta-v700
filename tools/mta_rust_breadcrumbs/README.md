# mta-breadcrumbs

Enterprise-grade CLI for structural code navigation - provides accurate hierarchical context (breadcrumbs and outlines) for Python and Node.js applications.

## Features

- **Resilient Parsing**: Uses Tree-sitter for error-tolerant parsing that works even with incomplete or malformed code
- **Multi-language Support**: Python, JavaScript, and TypeScript
- **Hierarchical Extraction**: Extract classes, functions, methods, interfaces, and control flow structures
- **Breadcrumb Navigation**: Get the structural context at any position in a file
- **Multiple Output Formats**: JSON, YAML, and ANSI-colored terminal output
- **Language Grouping**: Output grouped by language (Python vs Node.js)
- **Parallel Processing**: Efficient multi-threaded scanning for large codebases

## Installation

```bash
# Build from source
cargo build --release

# The binary will be at target/release/mta-breadcrumbs
```

## Usage

### Scan a Directory

```bash
# Scan current directory (JSON output)
mta-breadcrumbs .

# Colorful terminal output
mta-breadcrumbs --format ansi

# YAML output
mta-breadcrumbs --format yaml

# Group output by language (python/nodejs)
mta-breadcrumbs --grouped

# Only Python files
mta-breadcrumbs --language python

# Only Node.js files (JavaScript + TypeScript)
mta-breadcrumbs --language node

# Write to file
mta-breadcrumbs --output outline.json
```

### Single File Outline

```bash
# Get outline for a single file
mta-breadcrumbs file src/main.py

# With ANSI colors
mta-breadcrumbs file src/main.py --format ansi
```

### Breadcrumb at Position

```bash
# Get breadcrumb at line 10, column 5
mta-breadcrumbs breadcrumb src/main.py 10 5

# Example output (ANSI):
# MyClass > my_method > if

# Example output (JSON):
# {
#   "components": [...],
#   "line": 10,
#   "column": 5
# }
```

### Filtering Options

```bash
# Only named scopes (classes, functions, methods)
mta-breadcrumbs --named-only

# Limit depth
mta-breadcrumbs --max-depth 3

# Exclude control flow (if, for, while, etc.)
mta-breadcrumbs --no-control-flow

# Custom ignore patterns
mta-breadcrumbs --ignore "**/tests/**" --ignore "**/vendor/**"
```

## Output Formats

### JSON (Default)

```json
{
  "root": "/path/to/project",
  "files": [
    {
      "path": "src/main.py",
      "language": "python",
      "total_lines": 100,
      "nodes": [
        {
          "node_type": "class",
          "name": "MyClass",
          "start_line": 1,
          "end_line": 50,
          "children": [...]
        }
      ]
    }
  ],
  "stats": {
    "total_files": 10,
    "total_lines": 1000,
    "total_nodes": 150
  }
}
```

### YAML

```yaml
root: /path/to/project
files:
  - path: src/main.py
    language: python
    nodes:
      - node_type: class
        name: MyClass
        start_line: 1
        end_line: 50
```

### ANSI (Colorful Terminal)

```
  Breadcrumbs Scan Results

Root: /path/to/project

Files: 10  Lines: 1000  Nodes: 150

📄 src/main.py (Python)
   🔷 class MyClass :1-50
      def __init__ :2-10
      ...
```

### Grouped Output

When using `--grouped`, output is organized by language:

```json
{
  "root": "/path/to/project",
  "python": {
    "language": "python",
    "files": [...],
    "file_count": 5,
    "total_nodes": 80
  },
  "nodejs": {
    "language": "nodejs",
    "files": [...],
    "file_count": 5,
    "total_nodes": 70
  }
}
```

## Supported Node Types

### Python
- `module` - Top-level module
- `class` - Class definition
- `function` - Function definition
- `async_function` - Async function
- `decorator` - Decorated definition
- `lambda` - Lambda expression
- `with` - With statement
- `try/except/finally` - Exception handling

### JavaScript/TypeScript
- `module` - Program root
- `class` - Class declaration
- `function` - Function declaration
- `method` - Class method
- `async_function` - Async function
- `arrow_fn` - Arrow function
- `interface` - TypeScript interface
- `type` - TypeScript type alias
- `enum` - TypeScript enum
- `namespace` - Namespace/module

## Error Handling

mta-breadcrumbs uses Tree-sitter's robust error recovery to handle malformed code:

- Missing tokens are detected and marked
- Error nodes are bubbled up to find the nearest valid scope
- Parse errors are included in the output for debugging

```json
{
  "errors": [
    {
      "line": 10,
      "column": 5,
      "message": "Missing: )",
      "error_type": "missing"
    }
  ]
}
```

## Architecture

```
mta_rust_breadcrumbs/
├── Cargo.toml              # Workspace root
├── crates/
│   ├── core/               # Core library
│   │   └── src/
│   │       ├── lib.rs      # Public API
│   │       ├── models.rs   # Data structures
│   │       ├── config.rs   # Configuration
│   │       ├── engine.rs   # Scanner engine
│   │       ├── parsers/    # Language parsers
│   │       │   ├── mod.rs
│   │       │   ├── python.rs
│   │       │   └── javascript.rs
│   │       └── output/     # Output formatters
│   │           ├── mod.rs
│   │           ├── json.rs
│   │           ├── yaml.rs
│   │           └── ansi.rs
│   └── cli/                # CLI binary
│       └── src/
│           └── main.rs
└── README.md
```

## Performance

- Parallel file processing with Rayon
- Efficient Tree-sitter parsing
- Automatic thread count detection
- Memory-efficient file traversal with ignore support

## License

MIT
