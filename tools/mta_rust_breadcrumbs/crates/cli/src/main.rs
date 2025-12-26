//! mta-breadcrumbs CLI
//!
//! Enterprise-grade CLI for structural code navigation.
//! Provides breadcrumbs and outlines for Python and Node.js applications.

use anyhow::{Context, Result};
use clap::{Parser, Subcommand, ValueEnum};
use indicatif::{ProgressBar, ProgressStyle};
use mta_breadcrumbs_core::{
    format_output, format_output_grouped, get_breadcrumb, scan_file, BreadcrumbScanner, Language,
    NodeFilter, OutputFormat, ScanConfig,
};
use std::fs;
use std::path::PathBuf;
use std::time::Duration;

/// Enterprise-grade CLI for structural code navigation
#[derive(Parser)]
#[command(name = "mta-breadcrumbs")]
#[command(version = env!("CARGO_PKG_VERSION"))]
#[command(about = "Structural code navigation - breadcrumbs and outlines for Python and Node.js")]
#[command(long_about = r#"
mta-breadcrumbs: Enterprise-Grade Structural Code Navigation

Provides accurate hierarchical context (breadcrumbs and outlines) for source code
in any state of validity. Uses Tree-sitter for resilient parsing that works even
with incomplete or malformed code.

Supports:
  - Python (.py, .pyi)
  - JavaScript (.js, .mjs, .cjs, .jsx)
  - TypeScript (.ts, .mts, .cts, .tsx)

Output formats:
  - JSON (default) - Structured JSON for programmatic use
  - YAML - Human-readable YAML format
  - ANSI - Colorful terminal output with icons

Examples:
  mta-breadcrumbs .                           # Scan current directory
  mta-breadcrumbs --format ansi               # Colorful terminal output
  mta-breadcrumbs --language python           # Only Python files
  mta-breadcrumbs --grouped                   # Group by language
  mta-breadcrumbs file src/main.py            # Single file outline
  mta-breadcrumbs breadcrumb src/main.py 10 5 # Breadcrumb at line 10, col 5
"#)]
pub struct Args {
    /// Subcommand to run
    #[command(subcommand)]
    pub command: Option<Commands>,

    /// Path to scan (default: current directory)
    #[arg(default_value = ".")]
    pub path: PathBuf,

    /// Output format
    #[arg(short, long, value_enum, default_value_t = OutputFormatArg::Json)]
    pub format: OutputFormatArg,

    /// Language filter
    #[arg(short, long, value_enum)]
    pub language: Option<LanguageFilter>,

    /// Output file (default: stdout)
    #[arg(short, long)]
    pub output: Option<PathBuf>,

    /// Group output by language (python/nodejs)
    #[arg(long)]
    pub grouped: bool,

    /// Only include named scopes (classes, functions, methods)
    #[arg(long)]
    pub named_only: bool,

    /// Maximum depth to include
    #[arg(long)]
    pub max_depth: Option<usize>,

    /// Exclude control flow nodes (if, for, while, etc.)
    #[arg(long)]
    pub no_control_flow: bool,

    /// Include preview text
    #[arg(long, default_value_t = true)]
    pub preview: bool,

    /// Maximum preview length
    #[arg(long, default_value_t = 120)]
    pub preview_length: usize,

    /// Ignore patterns (can be specified multiple times)
    #[arg(long, action = clap::ArgAction::Append)]
    pub ignore: Vec<String>,

    /// Number of threads for parallel processing (default: auto)
    #[arg(long)]
    pub threads: Option<usize>,

    /// Verbose output
    #[arg(short, long)]
    pub verbose: bool,
}

/// Available subcommands
#[derive(Subcommand)]
pub enum Commands {
    /// Scan a directory for outlines
    Scan {
        /// Path to scan
        #[arg(default_value = ".")]
        path: PathBuf,
    },

    /// Get outline for a single file
    File {
        /// Path to file
        path: PathBuf,
    },

    /// Get breadcrumbs for file(s) - accepts file or directory
    Breadcrumb {
        /// Path to file or directory (recursive)
        #[arg(default_value = ".")]
        path: PathBuf,

        /// Line number (1-indexed) - only for single file
        #[arg(short, long)]
        line: Option<usize>,

        /// Column number (0-indexed) - only for single file
        #[arg(short, long, default_value_t = 0)]
        column: usize,
    },
}

/// Output format argument
#[derive(ValueEnum, Clone, Debug)]
pub enum OutputFormatArg {
    Json,
    Yaml,
    Ansi,
    Summary,
}

impl From<OutputFormatArg> for OutputFormat {
    fn from(arg: OutputFormatArg) -> Self {
        match arg {
            OutputFormatArg::Json => OutputFormat::Json,
            OutputFormatArg::Yaml => OutputFormat::Yaml,
            OutputFormatArg::Ansi => OutputFormat::Ansi,
            OutputFormatArg::Summary => OutputFormat::Summary,
        }
    }
}

/// Language filter argument
#[derive(ValueEnum, Clone, Debug)]
pub enum LanguageFilter {
    Python,
    Node,
    Javascript,
    Typescript,
}

fn main() -> Result<()> {
    let args = Args::parse();

    match &args.command {
        Some(Commands::Scan { path }) => run_scan(path, &args),
        Some(Commands::File { path }) => run_file(path, &args),
        Some(Commands::Breadcrumb { path, line, column }) => {
            run_breadcrumb(path, *line, *column, &args)
        }
        None => run_scan(&args.path, &args),
    }
}

/// Build common configuration from args
fn build_config(path: &PathBuf, args: &Args) -> ScanConfig {
    // Build language filter
    let language_filter = args.language.as_ref().map(|l| match l {
        LanguageFilter::Python => vec![Language::Python],
        LanguageFilter::Node => vec![Language::JavaScript, Language::TypeScript],
        LanguageFilter::Javascript => vec![Language::JavaScript],
        LanguageFilter::Typescript => vec![Language::TypeScript],
    });

    // Build node filter
    let mut node_filter = NodeFilter::default();
    if args.named_only {
        node_filter.named_scopes_only = true;
    }
    if let Some(max_depth) = args.max_depth {
        node_filter.max_depth = Some(max_depth);
    }
    if args.no_control_flow {
        node_filter.exclude_control_flow = true;
    }

    // Build config
    let mut config = ScanConfig::new(path.clone())
        .with_ignore_patterns(args.ignore.clone())
        .with_node_filter(node_filter)
        .with_preview(args.preview, args.preview_length);

    if let Some(threads) = args.threads {
        config = config.with_threads(threads);
    }

    if let Some(languages) = language_filter {
        config = config.with_language_filter(languages);
    }

    config
}

fn run_scan(path: &PathBuf, args: &Args) -> Result<()> {
    let config = build_config(path, args);

    // Show progress spinner
    let spinner = if args.verbose && atty::is(atty::Stream::Stderr) {
        let pb = ProgressBar::new_spinner();
        pb.set_style(
            ProgressStyle::default_spinner()
                .template("{spinner:.green} {msg}")
                .unwrap(),
        );
        pb.enable_steady_tick(Duration::from_millis(100));
        pb.set_message("Scanning project...");
        Some(pb)
    } else {
        None
    };

    // Run scan
    let scanner = BreadcrumbScanner::new(config).context("Failed to create scanner")?;
    let result = scanner.scan().context("Failed to scan directory")?;

    // Finish spinner
    if let Some(ref pb) = spinner {
        pb.finish_with_message(format!(
            "Scanned {} files in {}ms",
            result.stats.total_files, result.metadata.scan_duration_ms
        ));
    }

    // Format output
    let format: OutputFormat = args.format.clone().into();
    let output = if args.grouped {
        format_output_grouped(&result, format)?
    } else {
        format_output(&result, format)?
    };

    // Write output
    write_output(&output, args.output.as_ref())?;

    Ok(())
}

fn run_file(path: &PathBuf, args: &Args) -> Result<()> {
    let config = build_config(path, args);

    let outline = scan_file(path, &config).context("Failed to parse file")?;

    // Format output
    let format: OutputFormat = args.format.clone().into();
    let output = match format {
        OutputFormat::Json => serde_json::to_string_pretty(&outline)?,
        OutputFormat::Yaml => serde_yaml::to_string(&outline)?,
        OutputFormat::Ansi => format_file_ansi(&outline),
        OutputFormat::Summary => format_file_summary(&outline),
    };

    write_output(&output, args.output.as_ref())?;

    Ok(())
}

fn run_breadcrumb(path: &PathBuf, line: Option<usize>, column: usize, args: &Args) -> Result<()> {
    let config = build_config(path, args);

    // Check if path is a file or directory
    if path.is_file() {
        // Single file mode
        if let Some(line) = line {
            // Get breadcrumb at specific position
            let breadcrumb =
                get_breadcrumb(path, line, column, &config).context("Failed to get breadcrumb")?;

            let format: OutputFormat = args.format.clone().into();
            let output = match format {
                OutputFormat::Json => serde_json::to_string_pretty(&breadcrumb)?,
                OutputFormat::Yaml => serde_yaml::to_string(&breadcrumb)?,
                OutputFormat::Ansi => format_breadcrumb_ansi(&breadcrumb),
                OutputFormat::Summary => breadcrumb.path(),
            };

            write_output(&output, args.output.as_ref())?;
        } else {
            // Get full outline for the file
            let outline = scan_file(path, &config).context("Failed to parse file")?;

            let format: OutputFormat = args.format.clone().into();
            let output = match format {
                OutputFormat::Json => serde_json::to_string_pretty(&outline)?,
                OutputFormat::Yaml => serde_yaml::to_string(&outline)?,
                OutputFormat::Ansi => format_file_ansi(&outline),
                OutputFormat::Summary => format_file_summary(&outline),
            };

            write_output(&output, args.output.as_ref())?;
        }
    } else if path.is_dir() {
        // Directory mode - scan recursively
        let spinner = if args.verbose && atty::is(atty::Stream::Stderr) {
            let pb = ProgressBar::new_spinner();
            pb.set_style(
                ProgressStyle::default_spinner()
                    .template("{spinner:.green} {msg}")
                    .unwrap(),
            );
            pb.enable_steady_tick(Duration::from_millis(100));
            pb.set_message("Scanning directory...");
            Some(pb)
        } else {
            None
        };

        let scanner = BreadcrumbScanner::new(config).context("Failed to create scanner")?;
        let result = scanner.scan().context("Failed to scan directory")?;

        if let Some(ref pb) = spinner {
            pb.finish_with_message(format!(
                "Scanned {} files in {}ms",
                result.stats.total_files, result.metadata.scan_duration_ms
            ));
        }

        let format: OutputFormat = args.format.clone().into();
        let output = if args.grouped {
            format_output_grouped(&result, format)?
        } else {
            format_output(&result, format)?
        };

        write_output(&output, args.output.as_ref())?;
    } else {
        anyhow::bail!("Path does not exist: {}", path.display());
    }

    Ok(())
}

fn write_output(output: &str, path: Option<&PathBuf>) -> Result<()> {
    if let Some(path) = path {
        fs::write(path, output).context("Failed to write output file")?;
    } else {
        println!("{}", output);
    }
    Ok(())
}

fn format_file_ansi(outline: &mta_breadcrumbs_core::FileOutline) -> String {
    use mta_breadcrumbs_core::output::format_ansi;
    use mta_breadcrumbs_core::{OutlineMap, ScanMetadata, ScanStats};

    // Wrap in OutlineMap for consistent formatting
    let map = OutlineMap {
        root: outline.path.parent().unwrap_or(&outline.path).to_path_buf(),
        files: vec![outline.clone()],
        stats: ScanStats {
            total_files: 1,
            total_lines: outline.total_lines,
            total_nodes: outline.total_nodes(),
            python_files: if outline.language == mta_breadcrumbs_core::Language::Python {
                1
            } else {
                0
            },
            javascript_files: if outline.language == mta_breadcrumbs_core::Language::JavaScript {
                1
            } else {
                0
            },
            typescript_files: if outline.language == mta_breadcrumbs_core::Language::TypeScript {
                1
            } else {
                0
            },
            files_with_errors: if outline.has_errors() { 1 } else { 0 },
        },
        metadata: ScanMetadata {
            scan_duration_ms: 0,
            files_per_second: 0.0,
            timestamp: String::new(),
            tool_version: env!("CARGO_PKG_VERSION").to_string(),
        },
    };

    format_ansi(&map)
}

fn format_file_summary(outline: &mta_breadcrumbs_core::FileOutline) -> String {
    let mut output = String::new();

    output.push_str(&format!("File: {}\n", outline.path.display()));
    output.push_str(&format!("Language: {}\n", outline.language.display_name()));
    output.push_str(&format!("Lines: {}\n", outline.total_lines));
    output.push_str(&format!("Nodes: {}\n", outline.total_nodes()));

    if outline.has_errors() {
        output.push_str(&format!("Errors: {}\n", outline.errors.len()));
    }

    output.push_str("\nOutline:\n");
    for node in &outline.nodes {
        output.push_str(&format_node_summary(node, 0));
    }

    output
}

fn format_node_summary(node: &mta_breadcrumbs_core::OutlineNode, indent: usize) -> String {
    let mut output = String::new();
    let indent_str = "  ".repeat(indent);

    let name = node.name.as_deref().unwrap_or("");
    output.push_str(&format!(
        "{}{} {} ({}:{})\n",
        indent_str,
        node.node_type.label(),
        name,
        node.start_line,
        node.end_line
    ));

    for child in &node.children {
        output.push_str(&format_node_summary(child, indent + 1));
    }

    output
}

fn format_breadcrumb_ansi(breadcrumb: &mta_breadcrumbs_core::Breadcrumb) -> String {
    mta_breadcrumbs_core::output::format_breadcrumb_ansi(&breadcrumb.components)
}
