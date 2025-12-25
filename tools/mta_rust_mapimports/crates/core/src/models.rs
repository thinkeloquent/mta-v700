use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::PathBuf;

/// Type of import source
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ImportType {
    /// External package from npm/pypi
    External,
    /// Internal import from same project (workspace package)
    Internal,
    /// Local relative import (./foo, ../bar)
    Local,
    /// Standard library (builtin)
    Stdlib,
    /// Unknown/unresolved
    Unknown,
}

impl Default for ImportType {
    fn default() -> Self {
        ImportType::Unknown
    }
}

/// Language of the source file
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Language {
    Python,
    JavaScript,
    TypeScript,
}

impl Language {
    pub fn from_extension(ext: &str) -> Option<Self> {
        match ext.to_lowercase().as_str() {
            "py" | "pyi" => Some(Language::Python),
            "js" | "mjs" | "cjs" | "jsx" => Some(Language::JavaScript),
            "ts" | "mts" | "cts" | "tsx" => Some(Language::TypeScript),
            _ => None,
        }
    }
}

/// A single import statement
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ImportStatement {
    /// The module/package being imported
    pub module: String,
    /// Specific items imported (e.g., `from foo import bar, baz`)
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub items: Vec<String>,
    /// Whether it's a default import (JS) or wildcard
    #[serde(default)]
    pub is_default: bool,
    /// Line number in source file
    pub line: usize,
    /// Column position
    pub column: usize,
    /// Full import statement text
    pub raw: String,
    /// Categorization
    pub import_type: ImportType,
    /// Alias if any (e.g., `import numpy as np`)
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub alias: Option<String>,
}

/// Represents a source file with its imports
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SourceFile {
    /// Relative path from project root
    pub path: PathBuf,
    /// Absolute path
    pub absolute_path: PathBuf,
    /// Detected language
    pub language: Language,
    /// All imports in this file
    pub imports: Vec<ImportStatement>,
    /// Associated package (if in a workspace package)
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub package: Option<String>,
}

/// Dependency information from manifest files
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DependencyInfo {
    /// Package name
    pub name: String,
    /// Version constraint (e.g., "^1.0.0", ">=2.0")
    pub version: String,
    /// Source manifest file
    pub source: PathBuf,
    /// Is this a dev dependency?
    #[serde(default)]
    pub is_dev: bool,
    /// Is this a workspace/local dependency?
    #[serde(default)]
    pub is_workspace: bool,
    /// Is this an internal package (defined in this monorepo)?
    #[serde(default)]
    pub internal: bool,
    /// Is this a relative/local import (file: or link: prefix)?
    #[serde(default)]
    pub relative: bool,
    /// Resolved local path (for workspace deps)
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub local_path: Option<PathBuf>,
}

/// Package manifest (package.json, pyproject.toml, etc.)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PackageManifest {
    /// Name of the package
    pub name: String,
    /// Version
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub version: Option<String>,
    /// Path to manifest file
    pub path: PathBuf,
    /// Language/ecosystem
    pub language: Language,
    /// Dependencies
    #[serde(default, skip_serializing_if = "HashMap::is_empty")]
    pub dependencies: HashMap<String, DependencyInfo>,
    /// Dev dependencies
    #[serde(default, skip_serializing_if = "HashMap::is_empty")]
    pub dev_dependencies: HashMap<String, DependencyInfo>,
}

/// Aggregated import analysis results
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ImportMap {
    /// Project root path
    pub root: PathBuf,
    /// All source files analyzed
    pub files: Vec<SourceFile>,
    /// All manifests found
    pub manifests: Vec<PackageManifest>,
    /// Aggregated external dependencies with versions
    pub external_dependencies: HashMap<String, DependencyInfo>,
    /// Internal package references
    pub internal_packages: Vec<String>,
    /// Import statistics
    pub stats: ImportStats,
    /// Scan metadata
    pub metadata: ScanMetadata,
}

impl ImportMap {
    /// Filter to only show external dependencies with versions
    pub fn filter_to_dependencies(&self) -> Self {
        ImportMap {
            root: self.root.clone(),
            files: vec![],
            manifests: self.manifests.clone(),
            external_dependencies: self.external_dependencies.clone(),
            internal_packages: self.internal_packages.clone(),
            stats: self.stats.clone(),
            metadata: self.metadata.clone(),
        }
    }

    /// Filter to only show unknown/unresolved imports
    pub fn filter_to_unknown(&self) -> Self {
        let files: Vec<SourceFile> = self
            .files
            .iter()
            .filter_map(|f| {
                let unknown_imports: Vec<ImportStatement> = f
                    .imports
                    .iter()
                    .filter(|i| i.import_type == ImportType::Unknown)
                    .cloned()
                    .collect();

                if unknown_imports.is_empty() {
                    None
                } else {
                    Some(SourceFile {
                        path: f.path.clone(),
                        absolute_path: f.absolute_path.clone(),
                        language: f.language.clone(),
                        imports: unknown_imports,
                        package: f.package.clone(),
                    })
                }
            })
            .collect();

        let unknown_count = files.iter().map(|f| f.imports.len()).sum();

        ImportMap {
            root: self.root.clone(),
            files,
            manifests: vec![],
            external_dependencies: HashMap::new(),
            internal_packages: vec![],
            stats: ImportStats {
                total_files: 0,
                total_imports: unknown_count,
                external_imports: 0,
                internal_imports: 0,
                local_imports: 0,
                stdlib_imports: 0,
                unknown_imports: unknown_count,
                python_files: 0,
                javascript_files: 0,
                typescript_files: 0,
            },
            metadata: self.metadata.clone(),
        }
    }
}

/// Statistics about imports
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct ImportStats {
    pub total_files: usize,
    pub total_imports: usize,
    pub external_imports: usize,
    pub internal_imports: usize,
    pub local_imports: usize,
    pub stdlib_imports: usize,
    pub unknown_imports: usize,
    pub python_files: usize,
    pub javascript_files: usize,
    pub typescript_files: usize,
}

/// Scan metadata
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScanMetadata {
    pub scan_duration_ms: u64,
    pub files_per_second: f64,
    pub timestamp: String,
    pub tool_version: String,
}

impl Default for ScanMetadata {
    fn default() -> Self {
        Self {
            scan_duration_ms: 0,
            files_per_second: 0.0,
            timestamp: chrono::Utc::now().to_rfc3339(),
            tool_version: env!("CARGO_PKG_VERSION").to_string(),
        }
    }
}

/// Language-specific section of the import map
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LanguageSection {
    /// Source files for this language
    pub files: Vec<SourceFile>,
    /// Manifests for this language
    pub manifests: Vec<PackageManifest>,
    /// External dependencies with versions
    pub external_dependencies: HashMap<String, DependencyInfo>,
    /// Internal package references
    pub internal_packages: Vec<String>,
    /// Import statistics for this language
    pub stats: LanguageStats,
}

/// Statistics for a single language
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct LanguageStats {
    pub total_files: usize,
    pub total_imports: usize,
    pub external_imports: usize,
    pub internal_imports: usize,
    pub local_imports: usize,
    pub stdlib_imports: usize,
    pub unknown_imports: usize,
}

/// Grouped import map with separate sections for Python and Node.js
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GroupedImportMap {
    /// Project root path
    pub root: PathBuf,
    /// Python imports and dependencies
    pub python: LanguageSection,
    /// Node.js (JavaScript + TypeScript) imports and dependencies
    pub nodejs: LanguageSection,
    /// Scan metadata
    pub metadata: ScanMetadata,
}

impl ImportMap {
    /// Convert to grouped format (python/nodejs sections)
    pub fn to_grouped(&self) -> GroupedImportMap {
        // Separate files by language
        let python_files: Vec<SourceFile> = self
            .files
            .iter()
            .filter(|f| f.language == Language::Python)
            .cloned()
            .collect();

        let nodejs_files: Vec<SourceFile> = self
            .files
            .iter()
            .filter(|f| f.language == Language::JavaScript || f.language == Language::TypeScript)
            .cloned()
            .collect();

        // Separate manifests by language
        let python_manifests: Vec<PackageManifest> = self
            .manifests
            .iter()
            .filter(|m| m.language == Language::Python)
            .cloned()
            .collect();

        let nodejs_manifests: Vec<PackageManifest> = self
            .manifests
            .iter()
            .filter(|m| m.language == Language::JavaScript || m.language == Language::TypeScript)
            .cloned()
            .collect();

        // Separate dependencies by source manifest language
        let mut python_deps: HashMap<String, DependencyInfo> = HashMap::new();
        let mut nodejs_deps: HashMap<String, DependencyInfo> = HashMap::new();

        for (name, dep) in &self.external_dependencies {
            // Check if source is a Python manifest
            let source_str = dep.source.to_string_lossy();
            if source_str.contains("pyproject.toml") || source_str.contains("requirements.txt") {
                python_deps.insert(name.clone(), dep.clone());
            } else {
                nodejs_deps.insert(name.clone(), dep.clone());
            }
        }

        // Calculate stats for each language
        let python_stats = Self::calculate_language_stats(&python_files);
        let nodejs_stats = Self::calculate_language_stats(&nodejs_files);

        // Separate internal packages (heuristic: underscore = Python, hyphen = Node.js)
        let mut python_internal: Vec<String> = Vec::new();
        let mut nodejs_internal: Vec<String> = Vec::new();

        for pkg in &self.internal_packages {
            if pkg.contains('_') && !pkg.contains('-') {
                python_internal.push(pkg.clone());
            } else if pkg.contains('-') && !pkg.contains('_') {
                nodejs_internal.push(pkg.clone());
            } else {
                // Add to both if ambiguous
                python_internal.push(pkg.clone());
                nodejs_internal.push(pkg.clone());
            }
        }

        // Deduplicate
        python_internal.sort();
        python_internal.dedup();
        nodejs_internal.sort();
        nodejs_internal.dedup();

        GroupedImportMap {
            root: self.root.clone(),
            python: LanguageSection {
                files: python_files,
                manifests: python_manifests,
                external_dependencies: python_deps,
                internal_packages: python_internal,
                stats: python_stats,
            },
            nodejs: LanguageSection {
                files: nodejs_files,
                manifests: nodejs_manifests,
                external_dependencies: nodejs_deps,
                internal_packages: nodejs_internal,
                stats: nodejs_stats,
            },
            metadata: self.metadata.clone(),
        }
    }

    fn calculate_language_stats(files: &[SourceFile]) -> LanguageStats {
        let mut stats = LanguageStats::default();
        stats.total_files = files.len();

        for file in files {
            for import in &file.imports {
                stats.total_imports += 1;
                match import.import_type {
                    ImportType::External => stats.external_imports += 1,
                    ImportType::Internal => stats.internal_imports += 1,
                    ImportType::Local => stats.local_imports += 1,
                    ImportType::Stdlib => stats.stdlib_imports += 1,
                    ImportType::Unknown => stats.unknown_imports += 1,
                }
            }
        }

        stats
    }
}
