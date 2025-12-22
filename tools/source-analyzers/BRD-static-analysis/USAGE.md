# BRD Static Analysis Tool

A "Code-to-Spec" engine that generates Business Requirements Documents (BRD) from source code using static analysis.

## Features

- **Automated Discovery**: Scans project directories to classify files (Models, Controllers, Configs).
- **Polyglot Parsing**: Supports Python (via `ast`) and is designed for `tree-sitter` expansion.
- **Business Logic Extraction**: Identifies API Endpoints (`@app.get`, `@router.post`) and Validation Logic (`raise`).
- **Structured Output**: Generates BRD in YAML format (extensible to Markdown/JSON).

## Installation

```bash
pip install .
```

## Usage

Run the tool on a target directory:

```bash
python -m brd_generator.main src/my_project --output my_project_brd.yaml
```

### Options

- `path`: The root directory to analyze (Required).
- `--output`: Output file path (Default: `./brd.yaml`).
- `--format`: Output format (Default: `yaml`).

## Architecture

1. **Discovery Engine**: Finds relevant files and filters noise.
2. **Polyglot Parser**: Converts source code to normalized AST Nodes.
3. **Semantic Analyzer**: Matches AST patterns to Business Concepts (Features, Constraints).
4. **Synthesis Engine**: Renders the analysis into a BRD document.
python -m brd_generator.main <path>
