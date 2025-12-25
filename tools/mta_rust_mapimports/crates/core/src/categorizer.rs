use crate::models::{ImportType, Language, PackageManifest};
use std::collections::HashSet;

/// Directories that contain internal/workspace packages
const INTERNAL_PACKAGE_DIRS: &[&str] = &[
    "packages_py/",
    "packages_mjs/",
    "fastapi_server/",
    "fastify_server/",
    "fastapi_apps/",
    "fastify_apps/",
    "frontend_apps/",
];

/// Directories to exclude from internal package detection
const EXCLUDED_DIRS: &[&str] = &[
    "node_modules",
    ".pnpm",
    ".npm",
    ".venv",
    "venv",
    "__SPECS__",
    "__STAGE__",
    "dist",
    "build",
    ".git",
    "target",
];

/// Categorizes imports as internal, external, local, stdlib, or unknown
pub struct ImportCategorizer {
    /// Names of internal/workspace packages
    internal_packages: HashSet<String>,
    /// Python stdlib modules
    python_stdlib: HashSet<String>,
    /// Node.js builtin modules
    node_builtins: HashSet<String>,
    /// External dependencies from manifests
    external_deps: HashSet<String>,
}

impl ImportCategorizer {
    /// Create a new categorizer from the discovered manifests
    pub fn new(manifests: &[PackageManifest]) -> Self {
        let mut categorizer = Self {
            internal_packages: HashSet::new(),
            python_stdlib: Self::python_stdlib_modules(),
            node_builtins: Self::node_builtin_modules(),
            external_deps: HashSet::new(),
        };

        for manifest in manifests {
            let path_str = manifest.path.to_string_lossy();

            // Skip anything in excluded directories (node_modules, __STAGE__, etc.)
            if EXCLUDED_DIRS.iter().any(|dir| path_str.contains(dir)) {
                // Still collect dependencies from these, but don't mark as internal
                for dep_name in manifest.dependencies.keys() {
                    categorizer.external_deps.insert(dep_name.clone());
                }
                continue;
            }

            // Detect internal packages from workspace paths
            // Must be at root level or directly under these directories (not nested in node_modules)
            let is_internal = Self::is_internal_package_path(&path_str);

            if is_internal {
                categorizer.internal_packages.insert(manifest.name.clone());
                // Also add underscore variant for Python
                categorizer
                    .internal_packages
                    .insert(manifest.name.replace('-', "_"));
            }

            // Collect all external dependencies
            for dep_name in manifest.dependencies.keys() {
                categorizer.external_deps.insert(dep_name.clone());
            }
            for dep_name in manifest.dev_dependencies.keys() {
                categorizer.external_deps.insert(dep_name.clone());
            }
        }

        categorizer
    }

    /// Check if a manifest path indicates an internal/workspace package
    fn is_internal_package_path(path: &str) -> bool {
        // Check if path is in any excluded directory
        if EXCLUDED_DIRS.iter().any(|dir| path.contains(dir)) {
            return false;
        }

        // Check if path is in any internal package directory
        for dir in INTERNAL_PACKAGE_DIRS {
            if path.contains(dir) {
                return true;
            }
        }

        false
    }

    /// Categorize an import based on its module name and language
    pub fn categorize(&self, module: &str, language: &Language) -> ImportType {
        // 1. Check for local/relative imports
        if module.starts_with('.')
            || module.starts_with("./")
            || module.starts_with("../")
        {
            return ImportType::Local;
        }

        // 2. Get the base module name (first part before . or /)
        let base_module = module
            .split('/')
            .next()
            .unwrap_or(module)
            .split('.')
            .next()
            .unwrap_or(module);

        // 3. Check for stdlib
        match language {
            Language::Python => {
                if self.python_stdlib.contains(base_module) {
                    return ImportType::Stdlib;
                }
            }
            Language::JavaScript | Language::TypeScript => {
                if self.node_builtins.contains(base_module) || module.starts_with("node:") {
                    return ImportType::Stdlib;
                }
            }
        }

        // 4. Check for internal packages (workspace references)
        let normalized = base_module.replace('-', "_");
        if self.internal_packages.contains(base_module)
            || self.internal_packages.contains(&normalized)
        {
            return ImportType::Internal;
        }

        // JS: Check for @internal/ or similar patterns
        if module.starts_with("@internal/") {
            return ImportType::Internal;
        }

        // 5. Check if it's a known external dependency
        if self.external_deps.contains(base_module) {
            return ImportType::External;
        }

        // 6. Heuristic: scoped npm packages (@scope/pkg) are usually external
        if module.starts_with('@') && !module.starts_with("@internal") {
            return ImportType::External;
        }

        // 7. Default to Unknown for unresolved imports
        ImportType::Unknown
    }

    /// Get the list of known internal packages
    pub fn internal_packages(&self) -> Vec<String> {
        self.internal_packages.iter().cloned().collect()
    }

    /// Python standard library modules
    fn python_stdlib_modules() -> HashSet<String> {
        [
            // Core
            "abc", "aifc", "argparse", "array", "ast", "asynchat", "asyncio",
            "asyncore", "atexit", "audioop", "base64", "bdb", "binascii",
            "binhex", "bisect", "builtins", "bz2",
            // C-Z
            "calendar", "cgi", "cgitb", "chunk", "cmath", "cmd", "code",
            "codecs", "codeop", "collections", "colorsys", "compileall",
            "concurrent", "configparser", "contextlib", "contextvars", "copy",
            "copyreg", "cProfile", "crypt", "csv", "ctypes", "curses",
            // D-E
            "dataclasses", "datetime", "dbm", "decimal", "difflib", "dis",
            "distutils", "doctest", "email", "encodings", "enum", "errno",
            // F-G
            "faulthandler", "fcntl", "filecmp", "fileinput", "fnmatch",
            "fractions", "ftplib", "functools", "gc", "getopt", "getpass",
            "gettext", "glob", "graphlib", "grp", "gzip",
            // H-I
            "hashlib", "heapq", "hmac", "html", "http", "idlelib", "imaplib",
            "imghdr", "imp", "importlib", "inspect", "io", "ipaddress",
            "itertools",
            // J-L
            "json", "keyword", "lib2to3", "linecache", "locale", "logging",
            "lzma",
            // M-N
            "mailbox", "mailcap", "marshal", "math", "mimetypes", "mmap",
            "modulefinder", "multiprocessing", "netrc", "nis", "nntplib",
            "numbers",
            // O-P
            "operator", "optparse", "os", "ossaudiodev", "pathlib", "pdb",
            "pickle", "pickletools", "pipes", "pkgutil", "platform", "plistlib",
            "poplib", "posix", "posixpath", "pprint", "profile", "pstats",
            "pty", "pwd", "py_compile", "pyclbr", "pydoc",
            // Q-R
            "queue", "quopri", "random", "re", "readline", "reprlib",
            "resource", "rlcompleter", "runpy",
            // S
            "sched", "secrets", "select", "selectors", "shelve", "shlex",
            "shutil", "signal", "site", "smtpd", "smtplib", "sndhdr",
            "socket", "socketserver", "spwd", "sqlite3", "ssl", "stat",
            "statistics", "string", "stringprep", "struct", "subprocess",
            "sunau", "symtable", "sys", "sysconfig", "syslog",
            // T
            "tabnanny", "tarfile", "telnetlib", "tempfile", "termios", "test",
            "textwrap", "threading", "time", "timeit", "tkinter", "token",
            "tokenize", "trace", "traceback", "tracemalloc", "tty", "turtle",
            "turtledemo", "types", "typing",
            // U-Z
            "unicodedata", "unittest", "urllib", "uu", "uuid", "venv",
            "warnings", "wave", "weakref", "webbrowser", "winreg", "winsound",
            "wsgiref", "xdrlib", "xml", "xmlrpc", "zipapp", "zipfile",
            "zipimport", "zlib", "zoneinfo",
            // Underscore prefixed (internal but commonly used)
            "_thread", "__future__",
        ]
        .into_iter()
        .map(String::from)
        .collect()
    }

    /// Node.js builtin modules
    fn node_builtin_modules() -> HashSet<String> {
        [
            // Core modules
            "assert", "async_hooks", "buffer", "child_process", "cluster",
            "console", "constants", "crypto", "dgram", "diagnostics_channel",
            "dns", "domain", "events", "fs", "http", "http2", "https",
            "inspector", "module", "net", "os", "path", "perf_hooks",
            "process", "punycode", "querystring", "readline", "repl",
            "stream", "string_decoder", "sys", "timers", "tls", "trace_events",
            "tty", "url", "util", "v8", "vm", "wasi", "worker_threads", "zlib",
            // Node.js specific globals that can be imported
            "global", "queueMicrotask", "setImmediate", "clearImmediate",
        ]
        .into_iter()
        .map(String::from)
        .collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashMap;
    use std::path::PathBuf;

    fn create_test_manifest(name: &str, path: &str, deps: Vec<&str>) -> PackageManifest {
        let mut dependencies = HashMap::new();
        for dep in deps {
            dependencies.insert(
                dep.to_string(),
                crate::models::DependencyInfo {
                    name: dep.to_string(),
                    version: "^1.0.0".to_string(),
                    source: PathBuf::from(path),
                    is_dev: false,
                    is_workspace: false,
                    internal: false,
                    relative: false,
                    local_path: None,
                },
            );
        }

        PackageManifest {
            name: name.to_string(),
            version: Some("1.0.0".to_string()),
            path: PathBuf::from(path),
            language: Language::Python,
            dependencies,
            dev_dependencies: HashMap::new(),
        }
    }

    #[test]
    fn test_local_import() {
        let categorizer = ImportCategorizer::new(&[]);

        assert_eq!(
            categorizer.categorize(".", &Language::Python),
            ImportType::Local
        );
        assert_eq!(
            categorizer.categorize("./utils", &Language::JavaScript),
            ImportType::Local
        );
        assert_eq!(
            categorizer.categorize("../config", &Language::Python),
            ImportType::Local
        );
    }

    #[test]
    fn test_stdlib_python() {
        let categorizer = ImportCategorizer::new(&[]);

        assert_eq!(
            categorizer.categorize("os", &Language::Python),
            ImportType::Stdlib
        );
        assert_eq!(
            categorizer.categorize("sys", &Language::Python),
            ImportType::Stdlib
        );
        assert_eq!(
            categorizer.categorize("typing", &Language::Python),
            ImportType::Stdlib
        );
        assert_eq!(
            categorizer.categorize("collections.abc", &Language::Python),
            ImportType::Stdlib
        );
    }

    #[test]
    fn test_stdlib_node() {
        let categorizer = ImportCategorizer::new(&[]);

        assert_eq!(
            categorizer.categorize("fs", &Language::JavaScript),
            ImportType::Stdlib
        );
        assert_eq!(
            categorizer.categorize("path", &Language::JavaScript),
            ImportType::Stdlib
        );
        assert_eq!(
            categorizer.categorize("node:fs", &Language::JavaScript),
            ImportType::Stdlib
        );
    }

    #[test]
    fn test_external_dependency() {
        let manifest = create_test_manifest(
            "my-app",
            "/project/package.json",
            vec!["express", "lodash"],
        );
        let categorizer = ImportCategorizer::new(&[manifest]);

        assert_eq!(
            categorizer.categorize("express", &Language::JavaScript),
            ImportType::External
        );
        assert_eq!(
            categorizer.categorize("lodash", &Language::JavaScript),
            ImportType::External
        );
    }

    #[test]
    fn test_internal_package() {
        let manifest = create_test_manifest(
            "fetch-client",
            "/project/packages_py/fetch_client/pyproject.toml",
            vec![],
        );
        let categorizer = ImportCategorizer::new(&[manifest]);

        assert_eq!(
            categorizer.categorize("fetch_client", &Language::Python),
            ImportType::Internal
        );
        assert_eq!(
            categorizer.categorize("fetch-client", &Language::Python),
            ImportType::Internal
        );
    }

    #[test]
    fn test_scoped_npm_package() {
        let categorizer = ImportCategorizer::new(&[]);

        assert_eq!(
            categorizer.categorize("@types/node", &Language::TypeScript),
            ImportType::External
        );
        assert_eq!(
            categorizer.categorize("@fastify/cors", &Language::JavaScript),
            ImportType::External
        );
    }
}
