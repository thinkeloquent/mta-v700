export function parsePath(path: string): string[] {
    if (!path) return [];

    // Simple fast path
    if (!path.includes('[') && !path.includes('"') && !path.includes("'")) {
        return path.split('.');
    }

    const segments: string[] = [];
    let current = "";
    let inBracket = false;
    let inQuote = false;
    let quoteChar: string | null = null;

    for (let i = 0; i < path.length; i++) {
        const char = path[i];

        if (inQuote) {
            if (char === quoteChar) {
                inQuote = false;
                quoteChar = null;
                if (current) segments.push(current);
                current = "";
            } else {
                current += char;
            }
        } else if (inBracket) {
            if (char === '"' || char === "'") {
                inQuote = true;
                quoteChar = char;
            } else if (char === ']') {
                inBracket = false;
                if (current) {
                    segments.push(current);
                    current = "";
                }
            } else {
                current += char;
            }
        } else {
            if (char === '.') {
                if (current) {
                    segments.push(current);
                    current = "";
                }
            } else if (char === '[') {
                if (current) {
                    segments.push(current);
                    current = "";
                }
                inBracket = true;
            } else {
                current += char;
            }
        }
    }

    if (current) {
        segments.push(current);
    }

    return segments;
}
