//! Configuration module for the breadcrumbs scanner
//!
//! This module provides configuration structures and ignore filtering logic
//! for controlling how the scanner processes source files.

use crate::models::Language;
use globset::{Glob, GlobSet, GlobSetBuilder};
use ignore::gitignore::{Gitignore, GitignoreBuilder};
use std::path::{Path, PathBuf};
use thiserror::Error;

/// Configuration errors
#[derive(Error, Debug)]
pub enum ConfigError {
    #[error("Invalid glob pattern: {0}")]
    InvalidGlob(String),

    #[error("IO error: {0}")]
    IoError(#[from] std::io::Error),

    #[error("Invalid configuration: {0}")]
    InvalidConfig(String),
}

/// Filter for outline node types
#[derive(Debug, Clone, Default)]
pub struct NodeFilter {
    /// Include only named scopes (functions, classes, methods)
    pub named_scopes_only: bool,

    /// Minimum depth to include
    pub min_depth: Option<usize>,

    /// Maximum depth to include
    pub max_depth: Option<usize>,

    /// Exclude control flow nodes (if, for, while, etc.)
    pub exclude_control_flow: bool,
}

impl NodeFilter {
    /// Create a filter for named scopes only
    pub fn named_scopes() -> Self {
        Self {
            named_scopes_only: true,
            ..Default::default()
        }
    }

    /// Create a filter with max depth
    pub fn with_max_depth(depth: usize) -> Self {
        Self {
            max_depth: Some(depth),
            ..Default::default()
        }
    }
}

/// Configuration for the breadcrumbs scanner
#[derive(Debug, Clone)]
pub struct ScanConfig {
    /// Root directory to scan
    pub root: PathBuf,

    /// Language filter (None = all languages)
    pub language_filter: Option<Vec<Language>>,

    /// Custom ignore patterns
    pub ignore_patterns: Vec<String>,

    /// Path to custom ignore file
    pub ignore_file: Option<PathBuf>,

    /// Number of threads for parallel processing
    pub threads: usize,

    /// Maximum file size to process (bytes)
    pub max_file_size: usize,

    /// Whether to include preview text
    pub include_preview: bool,

    /// Maximum preview line length
    pub max_preview_length: usize,

    /// Node filter configuration
    pub node_filter: NodeFilter,

    /// Whether to follow symlinks
    pub follow_symlinks: bool,

    /// Whether to include hidden files
    pub include_hidden: bool,
}

impl Default for ScanConfig {
    fn default() -> Self {
        Self {
            root: PathBuf::from("."),
            language_filter: None,
            ignore_patterns: Vec::new(),
            ignore_file: None,
            threads: num_cpus(),
            max_file_size: 10 * 1024 * 1024, // 10 MB
            include_preview: true,
            max_preview_length: 120,
            node_filter: NodeFilter::default(),
            follow_symlinks: false,
            include_hidden: false,
        }
    }
}

impl ScanConfig {
    /// Create new config with root directory
    pub fn new(root: PathBuf) -> Self {
        Self {
            root,
            ..Default::default()
        }
    }

    /// Set language filter (builder pattern)
    pub fn with_language_filter(mut self, languages: Vec<Language>) -> Self {
        self.language_filter = Some(languages);
        self
    }

    /// Set ignore patterns (builder pattern)
    pub fn with_ignore_patterns(mut self, patterns: Vec<String>) -> Self {
        self.ignore_patterns = patterns;
        self
    }

    /// Set ignore file path (builder pattern)
    pub fn with_ignore_file(mut self, path: PathBuf) -> Self {
        self.ignore_file = Some(path);
        self
    }

    /// Set number of threads (builder pattern)
    pub fn with_threads(mut self, threads: usize) -> Self {
        self.threads = threads;
        self
    }

    /// Set max file size (builder pattern)
    pub fn with_max_file_size(mut self, size: usize) -> Self {
        self.max_file_size = size;
        self
    }

    /// Set preview options (builder pattern)
    pub fn with_preview(mut self, include: bool, max_length: usize) -> Self {
        self.include_preview = include;
        self.max_preview_length = max_length;
        self
    }

    /// Set node filter (builder pattern)
    pub fn with_node_filter(mut self, filter: NodeFilter) -> Self {
        self.node_filter = filter;
        self
    }

    /// Set follow symlinks (builder pattern)
    pub fn with_follow_symlinks(mut self, follow: bool) -> Self {
        self.follow_symlinks = follow;
        self
    }

    /// Set include hidden files (builder pattern)
    pub fn with_include_hidden(mut self, include: bool) -> Self {
        self.include_hidden = include;
        self
    }
}

/// Get number of available CPUs
fn num_cpus() -> usize {
    std::thread::available_parallelism()
        .map(|p| p.get())
        .unwrap_or(4)
}

/// Filter for ignoring files and directories
pub struct IgnoreFilter {
    /// Gitignore rules
    gitignore: Option<Gitignore>,

    /// Custom glob patterns
    custom_globs: GlobSet,

    /// Default ignore patterns
    default_ignores: GlobSet,

    /// Whether to include hidden files
    include_hidden: bool,
}

impl IgnoreFilter {
    /// Create a new ignore filter from config
    pub fn new(config: &ScanConfig) -> Result<Self, ConfigError> {
        // Build gitignore
        let gitignore = Self::build_gitignore(&config.root)?;

        // Build custom globs
        let custom_globs = Self::build_globset(&config.ignore_patterns)?;

        // Build default ignores
        let default_patterns = vec![
            "**/node_modules/**",
            "**/.git/**",
            "**/__pycache__/**",
            "**/.venv/**",
            "**/venv/**",
            "**/.env/**",
            "**/dist/**",
            "**/build/**",
            "**/target/**",
            "**/.tox/**",
            "**/.pytest_cache/**",
            "**/.mypy_cache/**",
            "**/.ruff_cache/**",
            "**/coverage/**",
            "**/.coverage/**",
            "**/htmlcov/**",
            "**/*.min.js",
            "**/*.bundle.js",
            "**/*.map",
            "**/vendor/**",
            "**/.next/**",
            "**/.nuxt/**",
        ];
        let default_ignores = Self::build_globset(
            &default_patterns.iter().map(|s| s.to_string()).collect(),
        )?;

        Ok(Self {
            gitignore,
            custom_globs,
            default_ignores,
            include_hidden: config.include_hidden,
        })
    }

    /// Build gitignore from root directory
    fn build_gitignore(root: &Path) -> Result<Option<Gitignore>, ConfigError> {
        let gitignore_path = root.join(".gitignore");
        if !gitignore_path.exists() {
            return Ok(None);
        }

        let mut builder = GitignoreBuilder::new(root);
        builder.add(&gitignore_path);

        match builder.build() {
            Ok(gi) => Ok(Some(gi)),
            Err(_) => Ok(None), // Ignore gitignore errors
        }
    }

    /// Build a globset from patterns
    fn build_globset(patterns: &Vec<String>) -> Result<GlobSet, ConfigError> {
        let mut builder = GlobSetBuilder::new();
        for pattern in patterns {
            let glob = Glob::new(pattern).map_err(|e| ConfigError::InvalidGlob(e.to_string()))?;
            builder.add(glob);
        }
        builder
            .build()
            .map_err(|e| ConfigError::InvalidGlob(e.to_string()))
    }

    /// Check if a path should be ignored
    pub fn should_ignore(&self, path: &Path, is_dir: bool) -> bool {
        let path_str = path.to_string_lossy();

        // Check hidden files
        if !self.include_hidden {
            if let Some(name) = path.file_name() {
                if name.to_string_lossy().starts_with('.') {
                    return true;
                }
            }
        }

        // Check default ignores
        if self.default_ignores.is_match(&*path_str) {
            return true;
        }

        // Check custom patterns
        if self.custom_globs.is_match(&*path_str) {
            return true;
        }

        // Check gitignore
        if let Some(ref gi) = self.gitignore {
            if gi.matched(path, is_dir).is_ignore() {
                return true;
            }
        }

        false
    }

    /// Check if path matches language filter
    pub fn matches_language_filter(
        &self,
        path: &Path,
        filter: &Option<Vec<Language>>,
    ) -> bool {
        let Some(ext) = path.extension() else {
            return false;
        };

        let ext_str = ext.to_string_lossy();
        let Some(lang) = Language::from_extension(&ext_str) else {
            return false;
        };

        match filter {
            Some(langs) => langs.contains(&lang),
            None => true,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_config_builder() {
        let config = ScanConfig::new(PathBuf::from("/test"))
            .with_threads(4)
            .with_language_filter(vec![Language::Python])
            .with_max_file_size(1024);

        assert_eq!(config.threads, 4);
        assert!(config.language_filter.is_some());
        assert_eq!(config.max_file_size, 1024);
    }

    #[test]
    fn test_language_filter() {
        let config = ScanConfig::new(PathBuf::from("."));
        let filter = IgnoreFilter::new(&config).unwrap();

        assert!(filter.matches_language_filter(
            Path::new("test.py"),
            &Some(vec![Language::Python])
        ));
        assert!(!filter.matches_language_filter(
            Path::new("test.js"),
            &Some(vec![Language::Python])
        ));
        assert!(filter.matches_language_filter(Path::new("test.ts"), &None));
    }
}
