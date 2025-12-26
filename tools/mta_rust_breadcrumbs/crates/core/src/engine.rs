//! Breadcrumb engine module
//!
//! This module provides the main scanner and engine for extracting
//! structural outlines from source code files.

use crate::config::{IgnoreFilter, ScanConfig};
use crate::models::{
    FileOutline, Language, OutlineMap, ScanMetadata, ScanStats,
};
use crate::parsers::{create_parser, parse_file, ParserError};
use rayon::prelude::*;
use std::fs;
use std::path::{Path, PathBuf};
use std::time::Instant;
use thiserror::Error;
use walkdir::WalkDir;

/// Scanner errors
#[derive(Error, Debug)]
pub enum ScanError {
    #[error("IO error: {0}")]
    IoError(#[from] std::io::Error),

    #[error("Config error: {0}")]
    ConfigError(#[from] crate::config::ConfigError),

    #[error("Parser error: {0}")]
    ParserError(#[from] ParserError),

    #[error("Thread pool error: {0}")]
    ThreadPoolError(String),
}

/// Main breadcrumb scanner
pub struct BreadcrumbScanner {
    config: ScanConfig,
    ignore_filter: IgnoreFilter,
}

impl BreadcrumbScanner {
    /// Create a new scanner with the given configuration
    pub fn new(config: ScanConfig) -> Result<Self, ScanError> {
        let ignore_filter = IgnoreFilter::new(&config)?;
        Ok(Self {
            config,
            ignore_filter,
        })
    }

    /// Scan the configured directory and return outline map
    pub fn scan(&self) -> Result<OutlineMap, ScanError> {
        let start = Instant::now();

        // Find all source files
        let source_files = self.find_source_files()?;

        // Parse files (in parallel if configured)
        let files: Vec<FileOutline> = if self.config.threads == 1 {
            source_files
                .into_iter()
                .filter_map(|(path, lang)| self.parse_file(&path, &lang))
                .collect()
        } else {
            let pool = rayon::ThreadPoolBuilder::new()
                .num_threads(self.config.threads)
                .build()
                .map_err(|e| ScanError::ThreadPoolError(e.to_string()))?;

            pool.install(|| {
                source_files
                    .par_iter()
                    .filter_map(|(path, lang)| self.parse_file(path, lang))
                    .collect()
            })
        };

        // Calculate stats
        let stats = self.calculate_stats(&files);

        // Build metadata
        let duration = start.elapsed();
        let file_count = files.len();
        let metadata = ScanMetadata {
            scan_duration_ms: duration.as_millis() as u64,
            files_per_second: if duration.as_secs_f64() > 0.0 {
                file_count as f64 / duration.as_secs_f64()
            } else {
                file_count as f64
            },
            timestamp: chrono::Utc::now().to_rfc3339(),
            tool_version: env!("CARGO_PKG_VERSION").to_string(),
        };

        Ok(OutlineMap {
            root: self.config.root.clone(),
            files,
            stats,
            metadata,
        })
    }

    /// Find all source files matching the configuration
    fn find_source_files(&self) -> Result<Vec<(PathBuf, Language)>, ScanError> {
        let mut files = Vec::new();

        let walker = WalkDir::new(&self.config.root)
            .follow_links(self.config.follow_symlinks)
            .into_iter()
            .filter_entry(|e| {
                // Skip ignored directories
                if e.file_type().is_dir() {
                    return !self.ignore_filter.should_ignore(e.path(), true);
                }
                true
            });

        for entry in walker.filter_map(|e| e.ok()) {
            if entry.file_type().is_dir() {
                continue;
            }

            let path = entry.path();

            // Skip ignored files
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

            // Check file size
            if let Ok(metadata) = entry.metadata() {
                if metadata.len() as usize > self.config.max_file_size {
                    continue;
                }
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

    /// Parse a single file and return its outline
    fn parse_file(&self, path: &Path, language: &Language) -> Option<FileOutline> {
        // Read file content
        let source = match fs::read_to_string(path) {
            Ok(s) => s,
            Err(_) => return None,
        };

        let total_lines = source.lines().count();

        // Parse the file
        let (nodes, errors) = match parse_file(&source, language, &self.config) {
            Ok(result) => result,
            Err(_) => (Vec::new(), Vec::new()),
        };

        // Calculate absolute path
        let absolute_path = path.canonicalize().unwrap_or_else(|_| path.to_path_buf());

        // Calculate relative path
        let relative_path = path
            .strip_prefix(&self.config.root)
            .unwrap_or(path)
            .to_path_buf();

        Some(FileOutline {
            path: relative_path,
            absolute_path,
            language: language.clone(),
            total_lines,
            nodes,
            errors,
        })
    }

    /// Calculate scan statistics
    fn calculate_stats(&self, files: &[FileOutline]) -> ScanStats {
        let total_files = files.len();
        let total_lines: usize = files.iter().map(|f| f.total_lines).sum();
        let total_nodes: usize = files.iter().map(|f| f.total_nodes()).sum();

        let python_files = files
            .iter()
            .filter(|f| f.language == Language::Python)
            .count();
        let javascript_files = files
            .iter()
            .filter(|f| f.language == Language::JavaScript)
            .count();
        let typescript_files = files
            .iter()
            .filter(|f| f.language == Language::TypeScript)
            .count();

        let files_with_errors = files.iter().filter(|f| f.has_errors()).count();

        ScanStats {
            total_files,
            total_lines,
            total_nodes,
            python_files,
            javascript_files,
            typescript_files,
            files_with_errors,
        }
    }
}

/// Scan a single file and return its outline
pub fn scan_file(path: &Path, config: &ScanConfig) -> Result<FileOutline, ScanError> {
    let ext = path
        .extension()
        .and_then(|e| e.to_str())
        .ok_or_else(|| ScanError::ParserError(ParserError::ParseError("No extension".to_string())))?;

    let language = Language::from_extension(ext)
        .ok_or_else(|| ScanError::ParserError(ParserError::UnsupportedLanguage(Language::Python)))?;

    let source = fs::read_to_string(path)?;
    let total_lines = source.lines().count();

    let (nodes, errors) = parse_file(&source, &language, config)?;

    let absolute_path = path.canonicalize().unwrap_or_else(|_| path.to_path_buf());

    Ok(FileOutline {
        path: path.to_path_buf(),
        absolute_path,
        language,
        total_lines,
        nodes,
        errors,
    })
}

/// Get breadcrumb at a specific position in a file
pub fn get_breadcrumb(
    path: &Path,
    line: usize,
    column: usize,
    config: &ScanConfig,
) -> Result<crate::models::Breadcrumb, ScanError> {
    let ext = path
        .extension()
        .and_then(|e| e.to_str())
        .ok_or_else(|| ScanError::ParserError(ParserError::ParseError("No extension".to_string())))?;

    let language = Language::from_extension(ext)
        .ok_or_else(|| ScanError::ParserError(ParserError::UnsupportedLanguage(Language::Python)))?;

    let source = fs::read_to_string(path)?;

    let mut parser = create_parser(&language)?;

    // Convert line/column to byte offset
    let byte_offset = line_column_to_byte(&source, line, column);

    parser
        .get_breadcrumb_at(&source, byte_offset, config)
        .map_err(ScanError::from)
}

/// Convert line/column (1-indexed) to byte offset
fn line_column_to_byte(source: &str, line: usize, column: usize) -> usize {
    let mut current_line = 1;

    for (idx, ch) in source.char_indices() {
        if current_line == line {
            let line_start = idx;
            let mut col = 0;
            for (col_idx, col_ch) in source[idx..].char_indices() {
                if col == column {
                    return line_start + col_idx;
                }
                if col_ch == '\n' {
                    break;
                }
                col += 1;
            }
            return line_start + column.min(source[idx..].find('\n').unwrap_or(source[idx..].len()));
        }
        if ch == '\n' {
            current_line += 1;
        }
    }

    source.len()
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;
    use tempfile::TempDir;

    fn create_test_project() -> (TempDir, PathBuf) {
        let dir = TempDir::new().unwrap();
        let root = dir.path().to_path_buf();

        // Create Python file
        let py_path = root.join("test.py");
        let mut py_file = fs::File::create(&py_path).unwrap();
        writeln!(
            py_file,
            r#"
class MyClass:
    def my_method(self):
        pass

def hello():
    print("Hello, World!")
"#
        )
        .unwrap();

        // Create JavaScript file
        let js_path = root.join("test.js");
        let mut js_file = fs::File::create(&js_path).unwrap();
        writeln!(
            js_file,
            r#"
function greet(name) {{
    console.log(`Hello, ${{name}}!`);
}}

class UserService {{
    constructor() {{}}

    getUser(id) {{
        return {{ id }};
    }}
}}
"#
        )
        .unwrap();

        (dir, root)
    }

    #[test]
    fn test_scan_directory() {
        let (dir, root) = create_test_project();
        let config = ScanConfig::new(root);
        let scanner = BreadcrumbScanner::new(config).unwrap();
        let result = scanner.scan().unwrap();

        assert_eq!(result.stats.total_files, 2);
        assert!(result.stats.python_files > 0);
        assert!(result.stats.javascript_files > 0);
    }

    #[test]
    fn test_scan_single_file() {
        let (dir, root) = create_test_project();
        let py_path = root.join("test.py");
        let config = ScanConfig::default();

        let result = scan_file(&py_path, &config).unwrap();

        assert_eq!(result.language, Language::Python);
        assert!(!result.nodes.is_empty());
    }

    #[test]
    fn test_language_filter() {
        let (dir, root) = create_test_project();
        let config = ScanConfig::new(root).with_language_filter(vec![Language::Python]);
        let scanner = BreadcrumbScanner::new(config).unwrap();
        let result = scanner.scan().unwrap();

        assert_eq!(result.stats.javascript_files, 0);
        assert!(result.stats.python_files > 0);
    }
}
