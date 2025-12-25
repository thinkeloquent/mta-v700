//! MTA Rust MapImports Core Library
//!
//! This library provides functionality for scanning Python and Node.js/TypeScript
//! projects to map all imports, categorize them, and extract dependency versions.
//!
//! # Features
//!
//! - Parse Python imports (import, from...import)
//! - Parse JavaScript/TypeScript imports (ESM, CommonJS require, dynamic import)
//! - Extract dependency versions from package.json, pyproject.toml, requirements.txt
//! - Categorize imports as External, Internal, Local, Stdlib, or Unknown
//! - Output results in JSON or YAML format
//!
//! # Example
//!
//! ```no_run
//! use mta_rust_mapimports_core::{ImportScanner, ScanConfig, OutputFormat, format_output};
//! use std::path::PathBuf;
//!
//! let config = ScanConfig::new(PathBuf::from("."));
//! let scanner = ImportScanner::new(config).unwrap();
//! let import_map = scanner.scan().unwrap();
//!
//! let json = format_output(&import_map, OutputFormat::Json).unwrap();
//! println!("{}", json);
//! ```

pub mod categorizer;
pub mod config;
pub mod manifest;
pub mod models;
pub mod output;
pub mod parsers;
pub mod scanner;

// Re-exports for convenience
pub use config::ScanConfig;
pub use models::*;
pub use output::{format_output, format_output_grouped, format_summary, OutputFormat};
pub use scanner::{ImportScanner, ScanError};
