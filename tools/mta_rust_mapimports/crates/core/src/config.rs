use crate::models::Language;
use globset::{Glob, GlobSet, GlobSetBuilder};
use ignore::gitignore::{Gitignore, GitignoreBuilder};
use std::path::{Path, PathBuf};
use thiserror::Error;

#[derive(Error, Debug)]
pub enum ConfigError {
    #[error("Failed to build glob pattern: {0}")]
    GlobError(#[from] globset::Error),
    #[error("Failed to parse gitignore: {0}")]
    GitignoreError(#[from] ignore::Error),
    #[error("IO error: {0}")]
    IoError(#[from] std::io::Error),
}

/// Configuration for scanning
#[derive(Debug, Clone)]
pub struct ScanConfig {
    /// Root directory to scan
    pub root: PathBuf,
    /// Filter to specific languages
    pub language_filter: Option<Vec<Language>>,
    /// Additional ignore patterns (glob style)
    pub ignore_patterns: Vec<String>,
    /// Custom ignore file path
    pub ignore_file: Option<PathBuf>,
    /// Include node_modules/.venv in scan
    pub include_deps: bool,
    /// Number of threads (0 = auto)
    pub threads: usize,
}

impl Default for ScanConfig {
    fn default() -> Self {
        Self {
            root: PathBuf::from("."),
            language_filter: None,
            ignore_patterns: vec![],
            ignore_file: None,
            include_deps: false,
            threads: 0,
        }
    }
}

impl ScanConfig {
    pub fn new(root: PathBuf) -> Self {
        Self {
            root,
            ..Default::default()
        }
    }

    pub fn with_language_filter(mut self, languages: Vec<Language>) -> Self {
        self.language_filter = Some(languages);
        self
    }

    pub fn with_ignore_patterns(mut self, patterns: Vec<String>) -> Self {
        self.ignore_patterns = patterns;
        self
    }

    pub fn with_ignore_file(mut self, path: PathBuf) -> Self {
        self.ignore_file = Some(path);
        self
    }

    pub fn with_include_deps(mut self, include: bool) -> Self {
        self.include_deps = include;
        self
    }

    pub fn with_threads(mut self, threads: usize) -> Self {
        self.threads = threads;
        self
    }
}

/// Filter for ignoring files and directories
pub struct IgnoreFilter {
    gitignore: Option<Gitignore>,
    custom_globs: GlobSet,
    default_ignores: GlobSet,
}

impl IgnoreFilter {
    pub fn new(config: &ScanConfig) -> Result<Self, ConfigError> {
        // Load .gitignore if present
        let gitignore = if let Some(ref ignore_file) = config.ignore_file {
            let mut builder = GitignoreBuilder::new(&config.root);
            builder.add(ignore_file);
            Some(builder.build()?)
        } else {
            let gitignore_path = config.root.join(".gitignore");
            if gitignore_path.exists() {
                let mut builder = GitignoreBuilder::new(&config.root);
                builder.add(&gitignore_path);
                Some(builder.build()?)
            } else {
                None
            }
        };

        // Build custom ignore globs
        let mut custom_builder = GlobSetBuilder::new();
        for pattern in &config.ignore_patterns {
            custom_builder.add(Glob::new(pattern)?);
        }
        let custom_globs = custom_builder.build()?;

        // Default ignores (unless include_deps is true)
        let mut default_builder = GlobSetBuilder::new();
        if !config.include_deps {
            default_builder.add(Glob::new("**/node_modules/**")?);
            default_builder.add(Glob::new("**/.venv/**")?);
            default_builder.add(Glob::new("**/venv/**")?);
            default_builder.add(Glob::new("**/__pycache__/**")?);
            default_builder.add(Glob::new("**/dist/**")?);
            default_builder.add(Glob::new("**/build/**")?);
            default_builder.add(Glob::new("**/.git/**")?);
            default_builder.add(Glob::new("**/target/**")?);
            default_builder.add(Glob::new("**/*.pyc")?);
            default_builder.add(Glob::new("**/*.pyo")?);
            default_builder.add(Glob::new("**/.DS_Store")?);
            // Project-specific directories to ignore
            default_builder.add(Glob::new("**/__SPECS__/**")?);
            default_builder.add(Glob::new("**/__STAGE__/**")?);
        }
        let default_ignores = default_builder.build()?;

        Ok(Self {
            gitignore,
            custom_globs,
            default_ignores,
        })
    }

    /// Check if a path should be ignored
    pub fn should_ignore(&self, path: &Path, is_dir: bool) -> bool {
        let path_str = path.to_string_lossy();

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

    /// Check if a file extension matches the language filter
    pub fn matches_language_filter(&self, path: &Path, filter: &Option<Vec<Language>>) -> bool {
        match filter {
            None => true,
            Some(languages) => {
                if let Some(ext) = path.extension() {
                    if let Some(lang) = Language::from_extension(&ext.to_string_lossy()) {
                        languages.contains(&lang)
                    } else {
                        false
                    }
                } else {
                    false
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_config() {
        let config = ScanConfig::default();
        assert_eq!(config.root, PathBuf::from("."));
        assert!(config.language_filter.is_none());
        assert!(!config.include_deps);
    }

    #[test]
    fn test_config_builder() {
        let config = ScanConfig::new(PathBuf::from("/test"))
            .with_language_filter(vec![Language::Python])
            .with_ignore_patterns(vec!["*.test.*".to_string()])
            .with_include_deps(true)
            .with_threads(4);

        assert_eq!(config.root, PathBuf::from("/test"));
        assert!(config.language_filter.is_some());
        assert!(config.include_deps);
        assert_eq!(config.threads, 4);
    }
}
