# Runtime Template Resolver (Node.js)

Safe, lightweight runtime string template replacement with path-based value resolution.

## Installation

\`\`\`bash
npm install @internal/runtime-template-resolver
\`\`\`

## Usage

\`\`\`typescript
import { resolve } from '@internal/runtime-template-resolver';

const result = resolve('Hello {{name}}', { name: 'World' });
console.log(result); // "Hello World"
\`\`\`
