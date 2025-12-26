//! mta_breadcrumbs_core - Core library for structural code navigation
//!
//! This crate provides the core functionality for extracting hierarchical
//! structure (breadcrumbs and outlines) from Python and JavaScript/TypeScript
//! source code using Tree-sitter for resilient parsing.
//!
//! # Features
//!
//! - **Resilient Parsing**: Uses Tree-sitter for error-tolerant parsing that
//!   works even with incomplete or malformed code.
//! - **Multi-language Support**: Python, JavaScript, and TypeScript.
//! - **Hierarchical Extraction**: Extract classes, functions, methods, and
//!   control flow structures.
//! - **Breadcrumb Navigation**: Get the structural context at any position.
//! - **Multiple Output Formats**: JSON, YAML, and ANSI-colored terminal output.
//!
//! # Example
//!
//! ```rust,no_run
//! use mta_breadcrumbs_core::{BreadcrumbScanner, ScanConfig, OutputFormat, format_output};
//! use std::path::PathBuf;
//!
//! // Create a scanner
//! let config = ScanConfig::new(PathBuf::from("."));
//! let scanner = BreadcrumbScanner::new(config).unwrap();
//!
//! // Scan the directory
//! let result = scanner.scan().unwrap();
//!
//! // Format output
//! let json = format_output(&result, OutputFormat::Json).unwrap();
//! println!("{}", json);
//! ```

pub mod config;
pub mod engine;
pub mod models;
pub mod output;
pub mod parsers;

// Re-exports for convenience
pub use config::{NodeFilter, ScanConfig};
pub use engine::{get_breadcrumb, scan_file, BreadcrumbScanner, ScanError};
pub use models::{
    Breadcrumb, BreadcrumbComponent, FileOutline, GroupedOutlineMap, Language, LanguageSection,
    NodeType, OutlineMap, OutlineNode, ParseError, ScanMetadata, ScanStats,
};
pub use output::{format_output, format_output_grouped, FormatError, OutputFormat};
pub use parsers::{create_parser, BreadcrumbParser, ParserError};
