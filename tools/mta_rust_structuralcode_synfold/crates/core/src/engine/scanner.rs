use crate::config::{IgnoreFilter, ScanConfig};
use crate::models::{FoldMap, FoldStats, Language, ScanMetadata, SourceFile};
use crate::parsers::create_parser;
use rayon::prelude::*;
use std::fs;
use std::path::{Path, PathBuf};
use std::time::Instant;
use thiserror::Error;
use walkdir::WalkDir;

#[derive(Error, Debug)]
pub enum ScanError {
    #[error("IO error: {0}")]
    IoError(#[from] std::io::Error),
    #[error("Config error: {0}")]
    ConfigError(#[from] crate::config::ConfigError),
    #[error("Parser error: {0}")]
    ParserError(#[from] crate::parsers::ParserError),
}

/// Main scanner for analyzing foldable regions across a project
pub struct FoldScanner {
    config: ScanConfig,
    ignore_filter: IgnoreFilter,
}

impl FoldScanner {
    pub fn new(config: ScanConfig) -> Result<Self, ScanError> {
        let ignore_filter = IgnoreFilter::new(&config)?;
        Ok(Self {
            config,
            ignore_filter,
        })
    }

    /// Scan the project and return the fold map
    pub fn scan(&self) -> Result<FoldMap, ScanError> {
        let start = Instant::now();

        // Find all source files
        let source_files = self.find_source_files()?;

        // Parse all files in parallel
        let files: Vec<SourceFile> = if self.config.threads == 1 {
            source_files
                .into_iter()
                .filter_map(|(path, lang)| self.parse_file(&path, &lang))
                .collect()
        } else {
            let pool = if self.config.threads > 0 {
                rayon::ThreadPoolBuilder::new()
                    .num_threads(self.config.threads)
                    .build()
                    .ok()
            } else {
                None
            };

            match pool {
                Some(pool) => pool.install(|| {
                    source_files
                        .par_iter()
                        .filter_map(|(path, lang)| self.parse_file(path, lang))
                        .collect()
                }),
                None => source_files
                    .par_iter()
                    .filter_map(|(path, lang)| self.parse_file(path, lang))
                    .collect(),
            }
        };

        // Calculate statistics
        let stats = self.calculate_stats(&files);

        // Build metadata
        let duration = start.elapsed();
        let metadata = ScanMetadata {
            scan_duration_ms: duration.as_millis() as u64,
            files_per_second: if duration.as_secs_f64() > 0.0 {
                files.len() as f64 / duration.as_secs_f64()
            } else {
                0.0
            },
            timestamp: chrono::Utc::now().to_rfc3339(),
            tool_version: env!("CARGO_PKG_VERSION").to_string(),
        };

        Ok(FoldMap {
            root: self.config.root.clone(),
            files,
            stats,
            metadata,
        })
    }

    /// Scan a single file
    pub fn scan_file(&self, path: &Path) -> Result<SourceFile, ScanError> {
        let ext = path
            .extension()
            .map(|e| e.to_string_lossy().to_string())
            .unwrap_or_default();

        let lang = Language::from_extension(&ext).ok_or_else(|| {
            ScanError::IoError(std::io::Error::new(
                std::io::ErrorKind::InvalidInput,
                format!("Unsupported file extension: {}", ext),
            ))
        })?;

        self.parse_file(path, &lang).ok_or_else(|| {
            ScanError::IoError(std::io::Error::new(
                std::io::ErrorKind::Other,
                "Failed to parse file",
            ))
        })
    }

    /// Find all source files matching the language filter
    fn find_source_files(&self) -> Result<Vec<(PathBuf, Language)>, ScanError> {
        let mut files = Vec::new();

        for entry in WalkDir::new(&self.config.root)
            .into_iter()
            .filter_map(|e| e.ok())
        {
            let path = entry.path();

            // Skip directories
            if entry.file_type().is_dir() {
                continue;
            }

            // Check ignore filter
            if self.ignore_filter.should_ignore(path, false) {
                continue;
            }

            // Check language filter
            if !self
                .ignore_filter
                .matches_language_filter(path, &self.config.language_filter)
            {
                continue;
            }

            // Get language from extension
            if let Some(ext) = path.extension() {
                if let Some(lang) = Language::from_extension(&ext.to_string_lossy()) {
                    files.push((path.to_path_buf(), lang));
                }
            }
        }

        Ok(files)
    }

    /// Parse a single source file
    fn parse_file(&self, path: &Path, language: &Language) -> Option<SourceFile> {
        // Read file content
        let content = match fs::read_to_string(path) {
            Ok(c) => c,
            Err(e) => {
                return Some(SourceFile {
                    path: path
                        .strip_prefix(&self.config.root)
                        .unwrap_or(path)
                        .to_path_buf(),
                    absolute_path: path.to_path_buf(),
                    language: language.clone(),
                    folds: vec![],
                    line_count: 0,
                    parsed: false,
                    error: Some(e.to_string()),
                });
            }
        };

        let line_count = content.lines().count();

        // Create parser for this language
        let mut parser = match create_parser(language) {
            Ok(p) => p,
            Err(e) => {
                return Some(SourceFile {
                    path: path
                        .strip_prefix(&self.config.root)
                        .unwrap_or(path)
                        .to_path_buf(),
                    absolute_path: path.to_path_buf(),
                    language: language.clone(),
                    folds: vec![],
                    line_count,
                    parsed: false,
                    error: Some(e.to_string()),
                });
            }
        };

        // Parse folds
        let folds = parser.parse(&content, &self.config);

        // Calculate relative path
        let relative_path = path
            .strip_prefix(&self.config.root)
            .unwrap_or(path)
            .to_path_buf();

        Some(SourceFile {
            path: relative_path,
            absolute_path: path.to_path_buf(),
            language: language.clone(),
            folds,
            line_count,
            parsed: true,
            error: None,
        })
    }

    /// Calculate fold statistics
    fn calculate_stats(&self, files: &[SourceFile]) -> FoldStats {
        let mut stats = FoldStats::default();

        stats.total_files = files.len();

        for file in files {
            match file.language {
                Language::Python => stats.python_files += 1,
                Language::JavaScript => stats.javascript_files += 1,
                Language::TypeScript => stats.typescript_files += 1,
            }

            stats.total_lines += file.line_count;

            for fold in &file.folds {
                stats.add_fold(&fold.fold_type);
                stats.foldable_lines += fold.line_count;
            }
        }

        stats
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_scanner_creation() {
        let config = ScanConfig::default();
        let scanner = FoldScanner::new(config);
        assert!(scanner.is_ok());
    }
}
