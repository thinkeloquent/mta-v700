//! Output formatting module
//!
//! This module provides formatters for JSON, YAML, and ANSI output of
//! outline and breadcrumb data structures.

pub mod ansi;
mod json;
mod yaml;

pub use ansi::{format_ansi, format_breadcrumb_ansi};
pub use json::format_json;
pub use yaml::format_yaml;

use crate::models::{GroupedOutlineMap, OutlineMap};
use thiserror::Error;

/// Output format errors
#[derive(Error, Debug)]
pub enum FormatError {
    #[error("JSON serialization error: {0}")]
    JsonError(#[from] serde_json::Error),

    #[error("YAML serialization error: {0}")]
    YamlError(#[from] serde_yaml::Error),

    #[error("Formatting error: {0}")]
    FormattingError(String),
}

/// Available output formats
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum OutputFormat {
    /// JSON format
    Json,
    /// YAML format
    Yaml,
    /// ANSI colored text
    Ansi,
    /// Plain text summary
    Summary,
}

impl Default for OutputFormat {
    fn default() -> Self {
        OutputFormat::Json
    }
}

/// Format outline data in the specified format
pub fn format_output(data: &OutlineMap, format: OutputFormat) -> Result<String, FormatError> {
    match format {
        OutputFormat::Json => format_json(data),
        OutputFormat::Yaml => format_yaml(data),
        OutputFormat::Ansi => Ok(format_ansi(data)),
        OutputFormat::Summary => Ok(format_summary(data)),
    }
}

/// Format grouped outline data (by language)
pub fn format_output_grouped(
    data: &OutlineMap,
    format: OutputFormat,
) -> Result<String, FormatError> {
    let grouped = data.to_grouped();
    match format {
        OutputFormat::Json => format_json_grouped(&grouped),
        OutputFormat::Yaml => format_yaml_grouped(&grouped),
        OutputFormat::Ansi => Ok(format_ansi_grouped(&grouped)),
        OutputFormat::Summary => Ok(format_summary_grouped(&grouped)),
    }
}

/// Format grouped data as JSON
fn format_json_grouped(data: &GroupedOutlineMap) -> Result<String, FormatError> {
    serde_json::to_string_pretty(data).map_err(FormatError::from)
}

/// Format grouped data as YAML
fn format_yaml_grouped(data: &GroupedOutlineMap) -> Result<String, FormatError> {
    serde_yaml::to_string(data).map_err(FormatError::from)
}

/// Format grouped data as ANSI
fn format_ansi_grouped(data: &GroupedOutlineMap) -> String {
    ansi::format_grouped_ansi(data)
}

/// Format as plain text summary
fn format_summary(data: &OutlineMap) -> String {
    let mut output = String::new();

    output.push_str(&format!("Breadcrumbs Scan Results\n"));
    output.push_str(&format!("========================\n\n"));
    output.push_str(&format!("Root: {}\n", data.root.display()));
    output.push_str(&format!("Total Files: {}\n", data.stats.total_files));
    output.push_str(&format!("Total Lines: {}\n", data.stats.total_lines));
    output.push_str(&format!("Total Nodes: {}\n", data.stats.total_nodes));
    output.push_str(&format!("\nLanguage Breakdown:\n"));
    output.push_str(&format!("  Python: {} files\n", data.stats.python_files));
    output.push_str(&format!(
        "  JavaScript: {} files\n",
        data.stats.javascript_files
    ));
    output.push_str(&format!(
        "  TypeScript: {} files\n",
        data.stats.typescript_files
    ));

    if data.stats.files_with_errors > 0 {
        output.push_str(&format!(
            "\nFiles with parse errors: {}\n",
            data.stats.files_with_errors
        ));
    }

    output.push_str(&format!("\nScan Duration: {}ms\n", data.metadata.scan_duration_ms));
    output.push_str(&format!(
        "Processing Speed: {:.2} files/sec\n",
        data.metadata.files_per_second
    ));

    output
}

/// Format grouped data as plain text summary
fn format_summary_grouped(data: &GroupedOutlineMap) -> String {
    let mut output = String::new();

    output.push_str(&format!("Breadcrumbs Scan Results (Grouped)\n"));
    output.push_str(&format!("===================================\n\n"));
    output.push_str(&format!("Root: {}\n\n", data.root.display()));

    // Python section
    output.push_str(&format!("Python\n"));
    output.push_str(&format!("------\n"));
    output.push_str(&format!("  Files: {}\n", data.python.file_count));
    output.push_str(&format!("  Nodes: {}\n", data.python.total_nodes));
    output.push_str(&format!("  Lines: {}\n", data.python.total_lines));
    if data.python.files_with_errors > 0 {
        output.push_str(&format!(
            "  Errors: {} files\n",
            data.python.files_with_errors
        ));
    }

    output.push_str(&format!("\nNode.js (JavaScript + TypeScript)\n"));
    output.push_str(&format!("---------------------------------\n"));
    output.push_str(&format!("  Files: {}\n", data.nodejs.file_count));
    output.push_str(&format!("  Nodes: {}\n", data.nodejs.total_nodes));
    output.push_str(&format!("  Lines: {}\n", data.nodejs.total_lines));
    if data.nodejs.files_with_errors > 0 {
        output.push_str(&format!(
            "  Errors: {} files\n",
            data.nodejs.files_with_errors
        ));
    }

    output.push_str(&format!("\nScan Duration: {}ms\n", data.metadata.scan_duration_ms));
    output.push_str(&format!(
        "Processing Speed: {:.2} files/sec\n",
        data.metadata.files_per_second
    ));

    output
}
