//! Synfold Core Library
//!
//! A structural code folding library using Tree-sitter AST analysis.
//! Supports Python and Node.js (JavaScript/TypeScript) applications.
//!
//! # Features
//!
//! - Parse Python code to identify foldable regions (functions, classes, imports, etc.)
//! - Parse JavaScript/TypeScript code with full ES6+ and TypeScript support
//! - Intelligent folding based on syntax structure, not line-based heuristics
//! - Configurable minimum fold lines and fold type filters
//! - Output in JSON, YAML, or ANSI-colored terminal format
//! - Grouped output by language (python/nodejs)
//!
//! # Example
//!
//! ```no_run
//! use synfold_core::{FoldScanner, ScanConfig, OutputFormat, format_output_grouped};
//! use std::path::PathBuf;
//!
//! let config = ScanConfig::new(PathBuf::from("."));
//! let scanner = FoldScanner::new(config).unwrap();
//! let fold_map = scanner.scan().unwrap();
//!
//! let output = format_output_grouped(&fold_map, OutputFormat::Json).unwrap();
//! println!("{}", output);
//! ```

pub mod config;
pub mod engine;
pub mod models;
pub mod output;
pub mod parsers;

// Re-exports for convenience
pub use config::ScanConfig;
pub use engine::{render_file, render_file_ansi, FoldScanner, Renderer, ScanError};
pub use models::*;
pub use output::{format_output, format_output_grouped, format_summary, FormatError, OutputFormat};
pub use parsers::{create_parser, FoldParser, ParserError};
