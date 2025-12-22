# YAML Spec Generator

Automated source code analysis and YAML specification generation tool.

## Overview

This tool automates the process of:

1. **File Discovery** - Scans directories for source files (Python, JavaScript, TypeScript)
2. **Source Code Analysis** - Parses and extracts structure using AST analysis
3. **YAML Spec Generation** - Produces structured documentation

## Installation

```bash
cd tools/source-analysis/yaml-spec-01

# Install with pip
pip install -e .
pip install -e tools/source-analysis/yaml-spec-01

# Or with poetry
poetry install

# For JavaScript analysis support
pip install -e ".[js]"

# For all features
pip install -e ".[full]"
```

## Usage

### Command Line

```bash
# Analyze a single directory
yaml-spec analyze ./src -o spec.yaml

# Analyze multiple directories
yaml-spec analyze ./packages_mjs/vault-file ./packages_py/vault_file -o vault-file-spec.yaml

# Analyze with options
yaml-spec analyze ./src \
  -o spec.yaml \
  -n "My Project Spec" \
  --line-numbers \
  --no-tests

# Preview output without writing
yaml-spec analyze ./src --preview

# Get quick statistics
yaml-spec info ./src

# Analyze a single file
yaml-spec file ./src/main.py
```

### Python API

```python
from yaml_spec import SpecGenerator, CodeAnalyzer

# High-level API
generator = SpecGenerator(
    include_tests=False,
    include_line_numbers=True,
)

yaml_str = generator.generate(
    directories=["./src", "./lib"],
    output_path="./docs/spec.yaml",
    spec_name="My Project",
)

# Lower-level analysis
analyzer = CodeAnalyzer()
analysis = analyzer.analyze_directory("./src")

for file_analysis in analysis.files:
    for cls in file_analysis.classes:
        print(f"Class: {cls.name}")
        for method in cls.methods:
            print(f"  - {method.name}()")
```

## Output Format

The generated YAML spec includes:

```yaml
spec_version: "1.0.0"
generated_at: "2025-12-17T..."
generator: "yaml-spec-generator v0.1.0"

package:
  name: "vault-file"
  version: "0.1.0"
  path: "/path/to/package"

  components:
    singleton_classes:
      EnvStore:
        file: "src/env_store.py"
        patterns: ["singleton"]
        fields:
          _instance: { type: "Optional[EnvStore]" }
        methods:
          get:
            parameters:
              key: { type: "str", required: true }
            returns: "Optional[str]"

    classes:
      VaultFile:
        file: "src/core.py"
        extends: ["IVaultFile"]
        fields:
          header: { type: "VaultHeader" }
        methods:
          to_json:
            returns: "str"

    functions:
      on_startup:
        file: "src/env_store.py"
        async: true
        parameters:
          location: { type: "str", required: true }
        returns: "EnvStore"

  exceptions:
    VaultValidationError:
      extends: "Exception"
      file: "src/validators.py"

  files:
    - path: "src/core.py"
      language: "python"
      summary:
        classes: 4
        functions: 0

analysis_metadata:
  statistics:
    files_analyzed: 5
    classes_found: 8
    functions_found: 3
  languages:
    python: 3
    typescript: 2
  tools_used:
    - name: "PythonAnalyzer"
      purpose: "AST-based Python code analysis"
```

## Features

### Pattern Detection

Automatically detects common patterns:

- **Singleton** - Classes with `_instance` field and `getInstance()` method
- **Dataclass** - Python `@dataclass` decorated classes
- **Abstract** - Classes extending ABC or with `@abstractmethod`
- **Factory** - Factory pattern implementations

### Multi-Language Support

| Language   | Parser             | Features                    |
| ---------- | ------------------ | --------------------------- |
| Python     | Built-in AST       | Full support                |
| JavaScript | esprima (optional) | Classes, functions, imports |
| TypeScript | Regex fallback     | Basic structure extraction  |

### Analysis Capabilities

- Class hierarchy and inheritance
- Method signatures with parameters and return types
- Field/property definitions with types
- Import/export statements
- Module-level constants
- Custom exception classes
- Decorators and annotations

## Architecture

```
yaml_spec/
├── __init__.py           # Package exports
├── models.py             # Data models (ClassInfo, FunctionInfo, etc.)
├── discovery.py          # File discovery and scanning
├── analyzer.py           # Main analyzer coordinator
├── spec_generator.py     # High-level API
├── cli.py                # Command-line interface
├── analyzers/
│   ├── base.py           # Base analyzer interface
│   ├── python_analyzer.py    # Python AST analyzer
│   └── javascript_analyzer.py # JS/TS analyzer
└── generators/
    └── yaml_generator.py # YAML output generator
```

## Extending

### Adding a New Language Analyzer

```python
from yaml_spec.analyzers.base import BaseAnalyzer
from yaml_spec.models import Language, FileAnalysis

class RustAnalyzer(BaseAnalyzer):
    @property
    def supported_languages(self) -> list[Language]:
        return [Language.RUST]  # Add to Language enum

    def analyze_file(self, path: Path) -> FileAnalysis:
        # Implement analysis logic
        pass
```

### Custom Output Generators

```python
from yaml_spec.models import PackageAnalysis

class JsonSpecGenerator:
    def generate(self, analyses: list[PackageAnalysis]) -> str:
        # Generate JSON output
        pass
```

## Dependencies

**Required:**

- Python 3.9+
- PyYAML
- Rich (for CLI formatting)
- Click (for CLI)

**Optional:**

- esprima (for JavaScript parsing)
- tree-sitter (for advanced multi-language support)

## License

Internal use only.
