use clap::{Parser, ValueEnum};
use indicatif::{ProgressBar, ProgressStyle};
use mta_rust_mapimports_core::{
    format_output, format_output_grouped, ImportScanner, Language, OutputFormat, ScanConfig,
};
use std::fs;
use std::path::PathBuf;
use std::time::Duration;

#[derive(Parser)]
#[command(name = "mapimports")]
#[command(version = env!("CARGO_PKG_VERSION"))]
#[command(about = "Map and categorize imports in Python and Node.js/TypeScript projects")]
#[command(long_about = "A Rust-based tool that scans project directories to analyze and categorize \
    import statements. It identifies external dependencies, internal packages, local relative \
    imports, and standard library modules. Supports Python (.py), JavaScript (.js, .mjs, .cjs), \
    and TypeScript (.ts, .tsx) files.\n\n\
    Output is grouped by language (python/nodejs) by default. Use --flat for ungrouped output.")]
pub struct Args {
    /// Project root directory to scan
    #[arg(default_value = ".")]
    pub path: PathBuf,

    /// Output format
    #[arg(short, long, value_enum, default_value_t = OutputFormatArg::Json)]
    pub format: OutputFormatArg,

    /// Output file (defaults to stdout)
    #[arg(short, long)]
    pub output: Option<PathBuf>,

    /// Only scan specific language
    #[arg(long, value_enum)]
    pub language: Option<LanguageFilter>,

    /// Additional ignore patterns (gitignore style)
    #[arg(long, action = clap::ArgAction::Append)]
    pub ignore: Vec<String>,

    /// Ignore file path (defaults to .gitignore)
    #[arg(long)]
    pub ignore_file: Option<PathBuf>,

    /// Include node_modules / .venv in scan
    #[arg(long)]
    pub include_deps: bool,

    /// Show only external dependencies with versions
    #[arg(long)]
    pub deps_only: bool,

    /// Show only unresolved/unknown imports
    #[arg(long)]
    pub unknown_only: bool,

    /// Use flat output structure (not grouped by language)
    #[arg(long)]
    pub flat: bool,

    /// Show verbose progress
    #[arg(short, long)]
    pub verbose: bool,

    /// Parallel threads (0 = auto)
    #[arg(long, default_value_t = 0)]
    pub threads: usize,
}

#[derive(ValueEnum, Clone, Debug)]
pub enum OutputFormatArg {
    Json,
    Yaml,
    Summary,
}

impl From<OutputFormatArg> for OutputFormat {
    fn from(arg: OutputFormatArg) -> Self {
        match arg {
            OutputFormatArg::Json => OutputFormat::Json,
            OutputFormatArg::Yaml => OutputFormat::Yaml,
            OutputFormatArg::Summary => OutputFormat::Summary,
        }
    }
}

#[derive(ValueEnum, Clone, Debug)]
pub enum LanguageFilter {
    Python,
    JavaScript,
    TypeScript,
    /// Alias for JS + TS
    Node,
}

fn main() -> anyhow::Result<()> {
    let args = Args::parse();

    // Convert language filter
    let language_filter = args.language.map(|l| match l {
        LanguageFilter::Python => vec![Language::Python],
        LanguageFilter::JavaScript => vec![Language::JavaScript],
        LanguageFilter::TypeScript => vec![Language::TypeScript],
        LanguageFilter::Node => vec![Language::JavaScript, Language::TypeScript],
    });

    // Build config
    let mut config = ScanConfig::new(args.path.clone())
        .with_ignore_patterns(args.ignore.clone())
        .with_include_deps(args.include_deps)
        .with_threads(args.threads);

    if let Some(languages) = language_filter {
        config = config.with_language_filter(languages);
    }

    if let Some(ignore_file) = args.ignore_file {
        config = config.with_ignore_file(ignore_file);
    }

    // Show progress if verbose
    let spinner = if args.verbose {
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

    // Create scanner and run
    let scanner = ImportScanner::new(config)?;
    let result = scanner.scan()?;

    if let Some(ref pb) = spinner {
        pb.finish_with_message(format!(
            "Scanned {} files in {}ms",
            result.stats.total_files, result.metadata.scan_duration_ms
        ));
    }

    // Apply filters
    let filtered_result = if args.deps_only {
        result.filter_to_dependencies()
    } else if args.unknown_only {
        result.filter_to_unknown()
    } else {
        result
    };

    // Format output (grouped by default, flat with --flat flag)
    let output = if args.flat {
        format_output(&filtered_result, args.format.into())?
    } else {
        format_output_grouped(&filtered_result, args.format.into())?
    };

    // Write output
    if let Some(path) = args.output {
        fs::write(&path, &output)?;
        if args.verbose {
            eprintln!("Output written to: {}", path.display());
        }
    } else {
        println!("{}", output);
    }

    Ok(())
}
