# mta_rust_structuralcode_synfold

A structural code folding utility for Python and Node.js/TypeScript using Tree-sitter AST analysis.

## Overview

Unlike regex-based tools, `mta_rust_structuralcode_synfold` performs **syntax-aware** code folding by leveraging Tree-sitter to build an Abstract Syntax Tree (AST) of your source code. This enables precise identification of foldable regions based on actual code structure.

## Features

- **Syntax-Aware Folding**: Understands code structure, not just line patterns
- **Multi-Language Support**: Python, JavaScript, and TypeScript
- **Intelligent Fold Detection**:
  - Function and class bodies
  - Import statement blocks
  - Argument/parameter lists
  - Chained method calls (builder pattern)
  - Multi-line string literals
  - Comments and documentation
  - Array and object literals
- **Flexible Output**: JSON, YAML, or ANSI-colored terminal
- **Grouped Output**: Results organized by language (python/nodejs)
- **Configurable**: Minimum fold lines, fold type filters, ignore patterns

## Installation

```bash
# Build from source
cd tools/mta_rust_structuralcode_synfold
cargo build --release

# The binary will be at target/release/mta_rust_structuralcode_synfold

# Or install to ~/.cargo/bin
cargo install --path crates/cli
```

## Usage

### Basic Scan

```bash
# Scan current directory
mta_rust_structuralcode_synfold

# Scan specific directory
mta_rust_structuralcode_synfold /path/to/project

# Output as YAML
mta_rust_structuralcode_synfold --format yaml

# Output as human-readable summary
mta_rust_structuralcode_synfold --format summary
```

### Render a File with Folds

```bash
# Render a file with folds applied (ANSI colors)
mta_rust_structuralcode_synfold render src/main.py --ansi

# Render without colors
mta_rust_structuralcode_synfold render src/main.py --no-color
```

### List Folds in a File

```bash
# List all foldable regions in JSON
mta_rust_structuralcode_synfold list src/main.py

# List as summary
mta_rust_structuralcode_synfold list src/main.py --format summary
```

### Analyze a Project

```bash
# Get fold statistics for a project
mta_rust_structuralcode_synfold analyze ./fastapi_server/ --format json --output output.json
```

## Options

```
Options:
  -f, --format <FORMAT>      Output format [default: json] [possible values: json, yaml, summary, ansi]
  -o, --output <OUTPUT>      Output file (defaults to stdout)
      --language <LANGUAGE>  Only scan specific language [possible values: python, javascript, typescript, node]
      --ignore <IGNORE>      Additional ignore patterns (gitignore style)
      --ignore-file <PATH>   Ignore file path (defaults to .gitignore)
      --include-deps         Include node_modules / .venv in scan
      --min-lines <N>        Minimum lines for a region to be foldable [default: 4]
      --flat                 Use flat output structure (not grouped by language)
      --no-color             Disable syntax highlighting in ANSI output
  -v, --verbose              Show verbose progress
      --threads <N>          Parallel threads (0 = auto) [default: 0]
      --fold-types <TYPES>   Fold only specific types (comma-separated)
      --no-fold <TYPES>      Exclude specific fold types
  -h, --help                 Print help
  -V, --version              Print version
```

### Fold Types

Available fold types for `--fold-types` and `--no-fold`:

- `block` - Function/method bodies
- `import` - Import statement blocks
- `arglist` - Function arguments/parameters
- `chain` - Chained method calls
- `literal` - String/numeric literals
- `comment` - Comments
- `doc` - Documentation comments (docstrings, JSDoc)
- `class` - Class/interface bodies
- `array` - Array/list literals
- `object` - Object/dict literals
- `all` - All fold types

## Output Format

### Grouped JSON (default)

```json
{
  "root": "/path/to/project",
  "python": {
    "files": [...],
    "stats": {
      "total_files": 10,
      "total_folds": 45,
      "block_folds": 20,
      "import_folds": 5,
      ...
    }
  },
  "nodejs": {
    "files": [...],
    "stats": {...}
  },
  "metadata": {
    "scan_duration_ms": 150,
    "files_per_second": 66.67,
    ...
  }
}
```

### Flat Structure

With `--flat`, output is not grouped by language:

```json
{
  "root": "/path/to/project",
  "files": [...],
  "stats": {...},
  "metadata": {...}
}
```

## Architecture

```
mta_rust_structuralcode_synfold/
├── crates/
│   ├── core/           # Core library
│   │   ├── config.rs   # Configuration
│   │   ├── models.rs   # Data models
│   │   ├── parsers/    # Tree-sitter parsers
│   │   ├── engine/     # Scanner and renderer
│   │   └── output/     # JSON/YAML/ANSI formatters
│   └── cli/            # CLI application
└── queries/            # SCM query files (extensible)
    ├── python/
    ├── javascript/
    └── typescript/
```

## Examples

### Python Function Folding

Before:

```python
def complex_function(arg1, arg2, arg3):
    """This is a docstring."""
    result = []
    for i in range(100):
        if some_condition:
            result.append(i)
    return result
```

After (with folding):

```python
def complex_function(arg1, arg2, arg3):
    /* """...""" (1 lines) */
    /* ... (6 lines) */
```

### JavaScript Import Folding

Before:

```javascript
import React from "react";
import { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { format } from "date-fns";
import styles from "./styles.css";

function App() {
  // ... component code
}
```

After (with folding):

```javascript
/* 5 imports */

function App() {
  /* ... (10 lines) */
}
```

# Default (flow mode)

mta_rust_structuralcode_synfold analyze ./src

# Minimal (current behavior)

mta_rust_structuralcode_synfold analyze ./src --preview-mode minimal

# Names only

mta_rust_structuralcode_synfold analyze ./src --preview-mode names

# Source snippets

mta_rust_structuralcode_synfold analyze ./src --preview-mode source

## License

MIT
