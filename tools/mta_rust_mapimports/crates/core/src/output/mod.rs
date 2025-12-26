mod json;
mod yaml;

use colored::*;

pub use json::to_json;
pub use yaml::to_yaml;

use crate::models::{GroupedImportMap, ImportMap};

/// Output format options
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum OutputFormat {
    Json,
    Yaml,
    Summary,
}

/// Format an ImportMap according to the specified format (flat structure)
pub fn format_output(import_map: &ImportMap, format: OutputFormat) -> Result<String, FormatError> {
    match format {
        OutputFormat::Json => to_json(import_map),
        OutputFormat::Yaml => to_yaml(import_map),
        OutputFormat::Summary => Ok(format_summary(import_map)),
    }
}

/// Format an ImportMap as grouped by language (python/nodejs sections)
pub fn format_output_grouped(import_map: &ImportMap, format: OutputFormat) -> Result<String, FormatError> {
    let grouped = import_map.to_grouped();
    match format {
        OutputFormat::Json => to_json_grouped(&grouped),
        OutputFormat::Yaml => to_yaml_grouped(&grouped),
        OutputFormat::Summary => Ok(format_summary_grouped(&grouped)),
    }
}

fn to_json_grouped(grouped: &GroupedImportMap) -> Result<String, FormatError> {
    serde_json::to_string_pretty(grouped).map_err(FormatError::from)
}

fn to_yaml_grouped(grouped: &GroupedImportMap) -> Result<String, FormatError> {
    serde_yaml::to_string(grouped).map_err(FormatError::from)
}

fn format_summary_grouped(grouped: &GroupedImportMap) -> String {
    let mut output = String::new();

    output.push_str(&format!(
        "{}\n{}\nRoot: {}\n\n",
        "Import Analysis Summary (Grouped)".bold().green(),
        "==================================".bold().green(),
        grouped.root.display().to_string().cyan()
    ));

    // Python section
    output.push_str(&format!("{}\n", "## Python".bold().yellow()));
    output.push_str(&format!(
        "Files: {}\n\
         Imports: {} (external: {}, internal: {}, local: {}, stdlib: {}, unknown: {})\n",
        grouped.python.stats.total_files.to_string().cyan(),
        grouped.python.stats.total_imports.to_string().cyan(),
        grouped.python.stats.external_imports.to_string().yellow(),
        grouped.python.stats.internal_imports.to_string().blue(),
        grouped.python.stats.local_imports,
        grouped.python.stats.stdlib_imports,
        if grouped.python.stats.unknown_imports > 0 {
            grouped.python.stats.unknown_imports.to_string().red()
        } else {
            grouped.python.stats.unknown_imports.to_string().normal()
        },
    ));
    if !grouped.python.external_dependencies.is_empty() {
        output.push_str(&format!("{}\n", "Dependencies:".bold()));
        let mut deps: Vec<_> = grouped.python.external_dependencies.iter().collect();
        deps.sort_by(|a, b| a.0.cmp(b.0));
        for (name, info) in deps.iter().take(20) {
            output.push_str(&format!("  {} @ {}\n", name.cyan(), info.version.yellow()));
        }
        if deps.len() > 20 {
            output.push_str(&format!("  ... and {} more\n", deps.len() - 20));
        }
    }
    output.push('\n');

    // Node.js section
    output.push_str(&format!("{}\n", "## Node.js (JavaScript + TypeScript)".bold().yellow()));
    output.push_str(&format!(
        "Files: {}\n\
         Imports: {} (external: {}, internal: {}, local: {}, stdlib: {}, unknown: {})\n",
        grouped.nodejs.stats.total_files.to_string().cyan(),
        grouped.nodejs.stats.total_imports.to_string().cyan(),
        grouped.nodejs.stats.external_imports.to_string().yellow(),
        grouped.nodejs.stats.internal_imports.to_string().blue(),
        grouped.nodejs.stats.local_imports,
        grouped.nodejs.stats.stdlib_imports,
        if grouped.nodejs.stats.unknown_imports > 0 {
            grouped.nodejs.stats.unknown_imports.to_string().red()
        } else {
            grouped.nodejs.stats.unknown_imports.to_string().normal()
        },
    ));
    if !grouped.nodejs.external_dependencies.is_empty() {
        output.push_str(&format!("{}\n", "Dependencies:".bold()));
        let mut deps: Vec<_> = grouped.nodejs.external_dependencies.iter().collect();
        deps.sort_by(|a, b| a.0.cmp(b.0));
        for (name, info) in deps.iter().take(20) {
            output.push_str(&format!("  {} @ {}\n", name.cyan(), info.version.yellow()));
        }
        if deps.len() > 20 {
            output.push_str(&format!("  ... and {} more\n", deps.len() - 20));
        }
    }
    output.push('\n');

    // Metadata
    output.push_str(&format!(
        "Scan Duration: {}ms ({:.2} files/sec)\n\
         Timestamp: {}\n\
         Tool Version: {}\n",
        grouped.metadata.scan_duration_ms.to_string().yellow(),
        grouped.metadata.files_per_second,
        grouped.metadata.timestamp,
        grouped.metadata.tool_version
    ));

    output
}

/// Generate a human-readable summary
pub fn format_summary(import_map: &ImportMap) -> String {
    let mut output = String::new();

    output.push_str(&format!(
        "{}\n{}\nRoot: {}\n\n",
        "Import Analysis Summary".bold().green(),
        "=======================".bold().green(),
        import_map.root.display().to_string().cyan()
    ));

    // Statistics
    output.push_str(&format!(
        "Files Scanned: {}\n\
         - Python: {}\n\
         - JavaScript: {}\n\
         - TypeScript: {}\n\n",
        import_map.stats.total_files.to_string().cyan(),
        import_map.stats.python_files,
        import_map.stats.javascript_files,
        import_map.stats.typescript_files
    ));

    output.push_str(&format!(
        "Total Imports: {}\n\
         - External: {}\n\
         - Internal: {}\n\
         - Local: {}\n\
         - Stdlib: {}\n\
         - Unknown: {}\n\n",
        import_map.stats.total_imports.to_string().cyan(),
        import_map.stats.external_imports.to_string().yellow(),
        import_map.stats.internal_imports.to_string().blue(),
        import_map.stats.local_imports,
        import_map.stats.stdlib_imports,
        if import_map.stats.unknown_imports > 0 {
            import_map.stats.unknown_imports.to_string().red()
        } else {
            import_map.stats.unknown_imports.to_string().normal()
        },
    ));

    // External dependencies
    if !import_map.external_dependencies.is_empty() {
        output.push_str(&format!("{}\n", "External Dependencies:".bold()));
        let mut deps: Vec<_> = import_map.external_dependencies.iter().collect();
        deps.sort_by(|a, b| a.0.cmp(b.0));

        for (name, info) in deps {
            output.push_str(&format!("  {} @ {}\n", name.cyan(), info.version.yellow()));
        }
        output.push('\n');
    }

    // Internal packages
    if !import_map.internal_packages.is_empty() {
        output.push_str(&format!("{}\n", "Internal Packages:".bold()));
        for pkg in &import_map.internal_packages {
            output.push_str(&format!("  {}\n", pkg.blue()));
        }
        output.push('\n');
    }

    // Metadata
    output.push_str(&format!(
        "Scan Duration: {}ms ({:.2} files/sec)\n\
         Timestamp: {}\n\
         Tool Version: {}\n",
        import_map.metadata.scan_duration_ms.to_string().yellow(),
        import_map.metadata.files_per_second,
        import_map.metadata.timestamp,
        import_map.metadata.tool_version
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
