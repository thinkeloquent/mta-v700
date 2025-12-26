mod json;
mod yaml;

pub use json::to_json;
pub use yaml::to_yaml;

use crate::models::{FoldMap, GroupedFoldMap};

/// Output format options
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum OutputFormat {
    Json,
    Yaml,
    Summary,
    Ansi,
}

/// Format a FoldMap according to the specified format (flat structure)
pub fn format_output(fold_map: &FoldMap, format: OutputFormat) -> Result<String, FormatError> {
    match format {
        OutputFormat::Json => to_json(fold_map),
        OutputFormat::Yaml => to_yaml(fold_map),
        OutputFormat::Summary => Ok(format_summary(fold_map)),
        OutputFormat::Ansi => Ok(format_summary_ansi(fold_map)),
    }
}

/// Format a FoldMap as grouped by language (python/nodejs sections)
pub fn format_output_grouped(
    fold_map: &FoldMap,
    format: OutputFormat,
) -> Result<String, FormatError> {
    let grouped = fold_map.to_grouped();
    match format {
        OutputFormat::Json => to_json_grouped(&grouped),
        OutputFormat::Yaml => to_yaml_grouped(&grouped),
        OutputFormat::Summary => Ok(format_summary_grouped(&grouped)),
        OutputFormat::Ansi => Ok(format_summary_grouped_ansi(&grouped)),
    }
}

fn to_json_grouped(grouped: &GroupedFoldMap) -> Result<String, FormatError> {
    serde_json::to_string_pretty(grouped).map_err(FormatError::from)
}

fn to_yaml_grouped(grouped: &GroupedFoldMap) -> Result<String, FormatError> {
    serde_yaml::to_string(grouped).map_err(FormatError::from)
}

fn format_summary_grouped(grouped: &GroupedFoldMap) -> String {
    let mut output = String::new();

    output.push_str(&format!(
        "Fold Analysis Summary (Grouped)\n\
         ================================\n\
         Root: {}\n\n",
        grouped.root.display()
    ));

    // Python section
    output.push_str("## Python\n");
    output.push_str(&format!(
        "Files: {} | Lines: {} | Foldable: {}\n\
         Folds: {} (blocks: {}, imports: {}, literals: {}, comments: {})\n",
        grouped.python.stats.total_files,
        grouped.python.stats.total_lines,
        grouped.python.stats.foldable_lines,
        grouped.python.stats.total_folds,
        grouped.python.stats.block_folds,
        grouped.python.stats.import_folds,
        grouped.python.stats.literal_folds,
        grouped.python.stats.comment_folds,
    ));

    // List files with most folds
    if !grouped.python.files.is_empty() {
        let mut files_by_folds: Vec<_> = grouped
            .python
            .files
            .iter()
            .filter(|f| !f.folds.is_empty())
            .collect();
        files_by_folds.sort_by(|a, b| b.folds.len().cmp(&a.folds.len()));

        if !files_by_folds.is_empty() {
            output.push_str("Top files by folds:\n");
            for file in files_by_folds.iter().take(5) {
                output.push_str(&format!(
                    "  {} ({} folds, {} lines)\n",
                    file.path.display(),
                    file.folds.len(),
                    file.line_count
                ));
            }
        }
    }
    output.push('\n');

    // Node.js section
    output.push_str("## Node.js (JavaScript + TypeScript)\n");
    output.push_str(&format!(
        "Files: {} | Lines: {} | Foldable: {}\n\
         Folds: {} (blocks: {}, imports: {}, literals: {}, comments: {})\n",
        grouped.nodejs.stats.total_files,
        grouped.nodejs.stats.total_lines,
        grouped.nodejs.stats.foldable_lines,
        grouped.nodejs.stats.total_folds,
        grouped.nodejs.stats.block_folds,
        grouped.nodejs.stats.import_folds,
        grouped.nodejs.stats.literal_folds,
        grouped.nodejs.stats.comment_folds,
    ));

    if !grouped.nodejs.files.is_empty() {
        let mut files_by_folds: Vec<_> = grouped
            .nodejs
            .files
            .iter()
            .filter(|f| !f.folds.is_empty())
            .collect();
        files_by_folds.sort_by(|a, b| b.folds.len().cmp(&a.folds.len()));

        if !files_by_folds.is_empty() {
            output.push_str("Top files by folds:\n");
            for file in files_by_folds.iter().take(5) {
                output.push_str(&format!(
                    "  {} ({} folds, {} lines)\n",
                    file.path.display(),
                    file.folds.len(),
                    file.line_count
                ));
            }
        }
    }
    output.push('\n');

    // Metadata
    output.push_str(&format!(
        "Scan Duration: {}ms ({:.2} files/sec)\n\
         Timestamp: {}\n\
         Tool Version: {}\n",
        grouped.metadata.scan_duration_ms,
        grouped.metadata.files_per_second,
        grouped.metadata.timestamp,
        grouped.metadata.tool_version
    ));

    output
}

fn format_summary_grouped_ansi(grouped: &GroupedFoldMap) -> String {
    let mut output = String::new();

    // ANSI codes
    let bold = "\x1b[1m";
    let reset = "\x1b[0m";
    let cyan = "\x1b[36m";
    let green = "\x1b[32m";
    let yellow = "\x1b[33m";
    let dim = "\x1b[2m";

    output.push_str(&format!(
        "{}{}Fold Analysis Summary (Grouped){}\n\
         {}================================{}\n\
         {}Root:{} {}\n\n",
        bold, cyan, reset, cyan, reset, dim, reset,
        grouped.root.display()
    ));

    // Python section
    output.push_str(&format!("{}{}## Python{}\n", bold, green, reset));
    output.push_str(&format!(
        "{}Files:{} {} | {}Lines:{} {} | {}Foldable:{} {}\n\
         {}Folds:{} {} (blocks: {}, imports: {}, literals: {}, comments: {})\n",
        dim, reset, grouped.python.stats.total_files,
        dim, reset, grouped.python.stats.total_lines,
        dim, reset, grouped.python.stats.foldable_lines,
        dim, reset, grouped.python.stats.total_folds,
        grouped.python.stats.block_folds,
        grouped.python.stats.import_folds,
        grouped.python.stats.literal_folds,
        grouped.python.stats.comment_folds,
    ));

    if !grouped.python.files.is_empty() {
        let mut files_by_folds: Vec<_> = grouped
            .python
            .files
            .iter()
            .filter(|f| !f.folds.is_empty())
            .collect();
        files_by_folds.sort_by(|a, b| b.folds.len().cmp(&a.folds.len()));

        if !files_by_folds.is_empty() {
            output.push_str(&format!("{}Top files by folds:{}\n", dim, reset));
            for file in files_by_folds.iter().take(5) {
                output.push_str(&format!(
                    "  {}{}{} ({}{} folds{}, {} lines)\n",
                    yellow,
                    file.path.display(),
                    reset,
                    cyan,
                    file.folds.len(),
                    reset,
                    file.line_count
                ));
            }
        }
    }
    output.push('\n');

    // Node.js section
    output.push_str(&format!(
        "{}{}## Node.js (JavaScript + TypeScript){}\n",
        bold, yellow, reset
    ));
    output.push_str(&format!(
        "{}Files:{} {} | {}Lines:{} {} | {}Foldable:{} {}\n\
         {}Folds:{} {} (blocks: {}, imports: {}, literals: {}, comments: {})\n",
        dim, reset, grouped.nodejs.stats.total_files,
        dim, reset, grouped.nodejs.stats.total_lines,
        dim, reset, grouped.nodejs.stats.foldable_lines,
        dim, reset, grouped.nodejs.stats.total_folds,
        grouped.nodejs.stats.block_folds,
        grouped.nodejs.stats.import_folds,
        grouped.nodejs.stats.literal_folds,
        grouped.nodejs.stats.comment_folds,
    ));

    if !grouped.nodejs.files.is_empty() {
        let mut files_by_folds: Vec<_> = grouped
            .nodejs
            .files
            .iter()
            .filter(|f| !f.folds.is_empty())
            .collect();
        files_by_folds.sort_by(|a, b| b.folds.len().cmp(&a.folds.len()));

        if !files_by_folds.is_empty() {
            output.push_str(&format!("{}Top files by folds:{}\n", dim, reset));
            for file in files_by_folds.iter().take(5) {
                output.push_str(&format!(
                    "  {}{}{} ({}{} folds{}, {} lines)\n",
                    yellow,
                    file.path.display(),
                    reset,
                    cyan,
                    file.folds.len(),
                    reset,
                    file.line_count
                ));
            }
        }
    }
    output.push('\n');

    // Metadata
    output.push_str(&format!(
        "{}Scan Duration:{} {}ms ({:.2} files/sec)\n\
         {}Timestamp:{} {}\n\
         {}Tool Version:{} {}\n",
        dim, reset,
        grouped.metadata.scan_duration_ms,
        grouped.metadata.files_per_second,
        dim, reset,
        grouped.metadata.timestamp,
        dim, reset,
        grouped.metadata.tool_version
    ));

    output
}

/// Generate a human-readable summary
pub fn format_summary(fold_map: &FoldMap) -> String {
    let mut output = String::new();

    output.push_str(&format!(
        "Fold Analysis Summary\n\
         =====================\n\
         Root: {}\n\n",
        fold_map.root.display()
    ));

    // Statistics
    output.push_str(&format!(
        "Files Scanned: {}\n\
         - Python: {}\n\
         - JavaScript: {}\n\
         - TypeScript: {}\n\n",
        fold_map.stats.total_files,
        fold_map.stats.python_files,
        fold_map.stats.javascript_files,
        fold_map.stats.typescript_files
    ));

    output.push_str(&format!(
        "Total Lines: {} | Foldable Lines: {} ({:.1}%)\n\n",
        fold_map.stats.total_lines,
        fold_map.stats.foldable_lines,
        if fold_map.stats.total_lines > 0 {
            (fold_map.stats.foldable_lines as f64 / fold_map.stats.total_lines as f64) * 100.0
        } else {
            0.0
        }
    ));

    output.push_str(&format!(
        "Total Folds: {}\n\
         - Blocks: {}\n\
         - Imports: {}\n\
         - Arg Lists: {}\n\
         - Chains: {}\n\
         - Literals: {}\n\
         - Comments: {}\n\
         - Doc Comments: {}\n\
         - Classes: {}\n\
         - Arrays: {}\n\
         - Objects: {}\n\n",
        fold_map.stats.total_folds,
        fold_map.stats.block_folds,
        fold_map.stats.import_folds,
        fold_map.stats.arglist_folds,
        fold_map.stats.chain_folds,
        fold_map.stats.literal_folds,
        fold_map.stats.comment_folds,
        fold_map.stats.doc_folds,
        fold_map.stats.class_folds,
        fold_map.stats.array_folds,
        fold_map.stats.object_folds
    ));

    // Metadata
    output.push_str(&format!(
        "Scan Duration: {}ms ({:.2} files/sec)\n\
         Timestamp: {}\n\
         Tool Version: {}\n",
        fold_map.metadata.scan_duration_ms,
        fold_map.metadata.files_per_second,
        fold_map.metadata.timestamp,
        fold_map.metadata.tool_version
    ));

    output
}

fn format_summary_ansi(fold_map: &FoldMap) -> String {
    let mut output = String::new();

    let bold = "\x1b[1m";
    let reset = "\x1b[0m";
    let cyan = "\x1b[36m";
    let dim = "\x1b[2m";

    output.push_str(&format!(
        "{}{}Fold Analysis Summary{}\n\
         {}====================={}\n\
         {}Root:{} {}\n\n",
        bold, cyan, reset, cyan, reset, dim, reset,
        fold_map.root.display()
    ));

    output.push_str(&format!(
        "{}Files Scanned:{} {} (Python: {}, JavaScript: {}, TypeScript: {})\n\n",
        dim, reset,
        fold_map.stats.total_files,
        fold_map.stats.python_files,
        fold_map.stats.javascript_files,
        fold_map.stats.typescript_files
    ));

    output.push_str(&format!(
        "{}Total Lines:{} {} | {}Foldable:{} {} ({:.1}%)\n\n",
        dim, reset,
        fold_map.stats.total_lines,
        dim, reset,
        fold_map.stats.foldable_lines,
        if fold_map.stats.total_lines > 0 {
            (fold_map.stats.foldable_lines as f64 / fold_map.stats.total_lines as f64) * 100.0
        } else {
            0.0
        }
    ));

    output.push_str(&format!(
        "{}Total Folds:{} {}\n\
         {}  Blocks:{} {} | {}Imports:{} {} | {}ArgLists:{} {} | {}Chains:{} {}\n\
         {}  Literals:{} {} | {}Comments:{} {} | {}Docs:{} {} | {}Classes:{} {}\n\n",
        dim, reset, fold_map.stats.total_folds,
        dim, reset, fold_map.stats.block_folds,
        dim, reset, fold_map.stats.import_folds,
        dim, reset, fold_map.stats.arglist_folds,
        dim, reset, fold_map.stats.chain_folds,
        dim, reset, fold_map.stats.literal_folds,
        dim, reset, fold_map.stats.comment_folds,
        dim, reset, fold_map.stats.doc_folds,
        dim, reset, fold_map.stats.class_folds
    ));

    output.push_str(&format!(
        "{}Scan:{} {}ms ({:.2} files/sec)\n",
        dim, reset,
        fold_map.metadata.scan_duration_ms,
        fold_map.metadata.files_per_second,
    ));

    output
}

#[derive(Debug, thiserror::Error)]
pub enum FormatError {
    #[error("JSON serialization error: {0}")]
    JsonError(#[from] serde_json::Error),
    #[error("YAML serialization error: {0}")]
    YamlError(#[from] serde_yaml::Error),
}
