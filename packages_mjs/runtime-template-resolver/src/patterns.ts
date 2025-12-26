export const PATTERNS = {
    // $.path.to.value
    DOT_PATH: /\$\.([a-zA-Z_][\w]*(?:\.[\w]+|\[\d+\]|\["[^"]+"\]|\[\'[^ \']+\'\])*)/g,

    // {{path.to.value}} or {{path|"default"}}
    MUSTACHE: /\{\{([^}|]+)(?:\|"([^"]*)")?\}\}/g,

    // Escaped variants
    ESCAPED_DOT: /\\\$\./g,
    ESCAPED_MUSTACHE: /\\\{\{/g,
};
