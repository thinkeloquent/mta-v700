# BRD Static Analysis Tool (JS Version)

Automated BRD Generator for JavaScript/TypeScript projects.

## Installation

```bash
npm install
npm run build
```

## Usage

```bash
# Run via Node
node dist/index.js generate <path-to-source> --output <output-file>

# Development
npm start generate <path-to-source>
```

## Features

- **Discovery**: Scans for JS/TS files.
- **Parsing**: Uses `@babel/parser` for robust AST generation.
- **Analysis**: Detects:
    - Decorators (`@Get`, `@Post`)
    - Express/Fastify routes (`app.get`)
    - Models (Classes ending in Dto/Entity)
    - Validations (`throw new Error`)

## Output

Generates a `yaml` or `json` BRD file containing:
- Executive Summary
- Functional Requirements (mapped to code)
- Reasoning
