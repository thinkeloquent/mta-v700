use crate::categorizer::ImportCategorizer;
use crate::config::{IgnoreFilter, ScanConfig};
use crate::manifest::find_manifests;
use crate::models::{
    DependencyInfo, ImportMap, ImportStats, Language, PackageManifest, ScanMetadata, SourceFile,
};
use crate::parsers::create_parser;
use rayon::prelude::*;
use std::collections::HashMap;
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

/// Main scanner for analyzing imports across a project
pub struct ImportScanner {
    config: ScanConfig,
    ignore_filter: IgnoreFilter,
}

impl ImportScanner {
    pub fn new(config: ScanConfig) -> Result<Self, ScanError> {
        let ignore_filter = IgnoreFilter::new(&config)?;
        Ok(Self {
            config,
            ignore_filter,
        })
    }

    /// Scan the project and return the import map
    pub fn scan(&self) -> Result<ImportMap, ScanError> {
        let start = Instant::now();

        // 1. Find all manifest files first
        let manifests = find_manifests(&self.config.root);

        // 2. Create categorizer from manifests
        let categorizer = ImportCategorizer::new(&manifests);

        // 3. Find all source files
        let source_files = self.find_source_files()?;

        // 4. Parse all files in parallel
        let files: Vec<SourceFile> = if self.config.threads == 1 {
            // Sequential processing
            source_files
                .into_iter()
                .filter_map(|(path, lang)| self.parse_file(&path, &lang, &categorizer, &manifests))
                .collect()
        } else {
            // Parallel processing with rayon
            let pool = if self.config.threads > 0 {
                rayon::ThreadPoolBuilder::new()
                    .num_threads(self.config.threads)
                    .build()
                    .ok()
            } else {
                None
            };

            let result: Vec<SourceFile> = match pool {
                Some(pool) => pool.install(|| {
                    source_files
                        .par_iter()
                        .filter_map(|(path, lang)| {
                            self.parse_file(path, lang, &categorizer, &manifests)
                        })
                        .collect()
                }),
                None => source_files
                    .par_iter()
                    .filter_map(|(path, lang)| {
                        self.parse_file(path, lang, &categorizer, &manifests)
                    })
                    .collect(),
            };
            result
        };

        // 5. Aggregate statistics
        let stats = self.calculate_stats(&files);

        // 6. Collect external dependencies with versions
        let external_dependencies = self.collect_external_dependencies(&manifests);

        // 7. Build metadata
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

        Ok(ImportMap {
            root: self.config.root.clone(),
            files,
            manifests,
            external_dependencies,
            internal_packages: categorizer.internal_packages(),
            stats,
            metadata,
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
    fn parse_file(
        &self,
        path: &Path,
        language: &Language,
        categorizer: &ImportCategorizer,
        manifests: &[PackageManifest],
    ) -> Option<SourceFile> {
        // Read file content
        let content = fs::read_to_string(path).ok()?;

        // Create parser for this language
        let mut parser = create_parser(language).ok()?;

        // Parse imports
        let mut imports = parser.parse(&content);

        // Categorize each import
        for import in &mut imports {
            import.import_type = categorizer.categorize(&import.module, language);
        }

        // Find associated package
        let package = self.find_package_for_file(path, manifests);

        // Calculate relative path
        let relative_path = path
            .strip_prefix(&self.config.root)
            .unwrap_or(path)
            .to_path_buf();

        Some(SourceFile {
            path: relative_path,
            absolute_path: path.to_path_buf(),
            language: language.clone(),
            imports,
            package,
        })
    }

    /// Find which package a file belongs to
    fn find_package_for_file(&self, file_path: &Path, manifests: &[PackageManifest]) -> Option<String> {
        let file_path_str = file_path.to_string_lossy();

        for manifest in manifests {
            if let Some(manifest_dir) = manifest.path.parent() {
                let manifest_dir_str = manifest_dir.to_string_lossy();
                if file_path_str.starts_with(manifest_dir_str.as_ref()) {
                    return Some(manifest.name.clone());
                }
            }
        }

        None
    }

    /// Calculate import statistics
    fn calculate_stats(&self, files: &[SourceFile]) -> ImportStats {
        let mut stats = ImportStats::default();

        stats.total_files = files.len();

        for file in files {
            match file.language {
                Language::Python => stats.python_files += 1,
                Language::JavaScript => stats.javascript_files += 1,
                Language::TypeScript => stats.typescript_files += 1,
            }

            for import in &file.imports {
                stats.total_imports += 1;
                match import.import_type {
                    crate::models::ImportType::External => stats.external_imports += 1,
                    crate::models::ImportType::Internal => stats.internal_imports += 1,
                    crate::models::ImportType::Local => stats.local_imports += 1,
                    crate::models::ImportType::Stdlib => stats.stdlib_imports += 1,
                    crate::models::ImportType::Unknown => stats.unknown_imports += 1,
                }
            }
        }

        stats
    }

    /// Collect all external dependencies from manifests
    fn collect_external_dependencies(
        &self,
        manifests: &[PackageManifest],
    ) -> HashMap<String, DependencyInfo> {
        let mut deps = HashMap::new();

        for manifest in manifests {
            for (name, info) in &manifest.dependencies {
                if !info.is_workspace {
                    deps.insert(name.clone(), info.clone());
                }
            }
            for (name, info) in &manifest.dev_dependencies {
                if !info.is_workspace && !deps.contains_key(name) {
                    deps.insert(name.clone(), info.clone());
                }
            }
        }

        deps
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_scanner_creation() {
        let config = ScanConfig::default();
        let scanner = ImportScanner::new(config);
        assert!(scanner.is_ok());
    }
}
