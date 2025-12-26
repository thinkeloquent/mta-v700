use clap::{Parser, Subcommand, ValueEnum};
use indicatif::{ProgressBar, ProgressStyle};
use synfold_core::{
    format_output, format_output_grouped, render_file, render_file_ansi, FoldFilter, FoldScanner,
    Language, OutputFormat, PreviewMode, ScanConfig,
};
use std::fs;
use std::path::PathBuf;
use std::time::Duration;

#[derive(Parser)]
#[command(name = "mta_rust_structuralcode_synfold")]
#[command(version = env!("CARGO_PKG_VERSION"))]
#[command(about = "Structural code folding utility for Python and Node.js/TypeScript")]
#[command(long_about = "A Rust-based tool that performs syntax-aware code folding using Tree-sitter AST analysis. \
    Unlike regex-based tools, synfold understands code structure and can intelligently fold:\n\n\
    - Function and class bodies\n\
    - Import statement blocks\n\
    - Argument/parameter lists\n\
    - Chained method calls (builder pattern)\n\
    - Multi-line string literals\n\
    - Comments and documentation\n\
    - Array and object literals\n\n\
    Output is grouped by language (python/nodejs) by default.")]
pub struct Args {
    #[command(subcommand)]
    pub command: Option<Commands>,

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

    /// Minimum lines for a region to be foldable
    #[arg(long, default_value_t = 4)]
    pub min_lines: usize,

    /// Use flat output structure (not grouped by language)
    #[arg(long)]
    pub flat: bool,

    /// Disable syntax highlighting in ANSI output
    #[arg(long)]
    pub no_color: bool,

    /// Show verbose progress
    #[arg(short, long)]
    pub verbose: bool,

    /// Parallel threads (0 = auto)
    #[arg(long, default_value_t = 0)]
    pub threads: usize,

    /// Fold only specific types (comma-separated: block,import,arglist,chain,literal,comment,doc,class,array,object)
    #[arg(long)]
    pub fold_types: Option<String>,

    /// Exclude specific fold types
    #[arg(long)]
    pub no_fold: Option<String>,

    /// Preview mode for fold summaries
    #[arg(long, value_enum, default_value_t = PreviewModeArg::Flow)]
    pub preview_mode: PreviewModeArg,
}

#[derive(Subcommand)]
pub enum Commands {
    /// Analyze a project and show fold statistics
    Analyze {
        /// Project root directory
        #[arg(default_value = ".")]
        path: PathBuf,

        /// Output format
        #[arg(short, long, value_enum, default_value_t = OutputFormatArg::Ansi)]
        format: OutputFormatArg,

        /// Output file (defaults to stdout)
        #[arg(short, long)]
        output: Option<PathBuf>,

        /// Preview mode for fold summaries
        #[arg(long, value_enum, default_value_t = PreviewModeArg::Flow)]
        preview_mode: PreviewModeArg,
    },

    /// Render a single file with folds applied
    Render {
        /// File to render
        file: PathBuf,

        /// Output with ANSI colors
        #[arg(long)]
        ansi: bool,

        /// Minimum lines for folding
        #[arg(long, default_value_t = 4)]
        min_lines: usize,
    },

    /// List all foldable regions in a file
    List {
        /// File to analyze
        file: PathBuf,

        /// Output format
        #[arg(short, long, value_enum, default_value_t = OutputFormatArg::Json)]
        format: OutputFormatArg,

        /// Preview mode for fold summaries
        #[arg(long, value_enum, default_value_t = PreviewModeArg::Flow)]
        preview_mode: PreviewModeArg,
    },
}

#[derive(ValueEnum, Clone, Debug)]
pub enum OutputFormatArg {
    Json,
    Yaml,
    Summary,
    Ansi,
}

impl From<OutputFormatArg> for OutputFormat {
    fn from(arg: OutputFormatArg) -> Self {
        match arg {
            OutputFormatArg::Json => OutputFormat::Json,
            OutputFormatArg::Yaml => OutputFormat::Yaml,
            OutputFormatArg::Summary => OutputFormat::Summary,
            OutputFormatArg::Ansi => OutputFormat::Ansi,
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

#[derive(ValueEnum, Clone, Debug, Default)]
pub enum PreviewModeArg {
    /// Minimal info: "5 imports", "def foo()"
    Minimal,
    /// Names only: "os, sys, typing.List"
    Names,
    /// Signature + control flow (default): "def foo() -> if/for/return"
    #[default]
    Flow,
    /// First N chars of actual source code
    Source,
}

impl From<PreviewModeArg> for PreviewMode {
    fn from(arg: PreviewModeArg) -> Self {
        match arg {
            PreviewModeArg::Minimal => PreviewMode::Minimal,
            PreviewModeArg::Names => PreviewMode::Names,
            PreviewModeArg::Flow => PreviewMode::Flow,
            PreviewModeArg::Source => PreviewMode::Source,
        }
    }
}

fn main() -> anyhow::Result<()> {
    let args = Args::parse();

    // Handle subcommands
    match &args.command {
        Some(Commands::Analyze { path, format, output, preview_mode }) => {
            run_analyze(path.clone(), format.clone(), output.clone(), preview_mode.clone(), &args)
        }
        Some(Commands::Render {
            file,
            ansi,
            min_lines,
        }) => run_render(file.clone(), *ansi, *min_lines, &args),
        Some(Commands::List { file, format, preview_mode }) => run_list(file.clone(), format.clone(), preview_mode.clone(), &args),
        None => run_scan(&args),
    }
}

fn run_scan(args: &Args) -> anyhow::Result<()> {
    // Convert language filter
    let language_filter = args.language.as_ref().map(|l| match l {
        LanguageFilter::Python => vec![Language::Python],
        LanguageFilter::JavaScript => vec![Language::JavaScript],
        LanguageFilter::TypeScript => vec![Language::TypeScript],
        LanguageFilter::Node => vec![Language::JavaScript, Language::TypeScript],
    });

    // Parse fold type filters
    let fold_filter = build_fold_filter(&args.fold_types, &args.no_fold);

    // Build config
    let mut config = ScanConfig::new(args.path.clone())
        .with_ignore_patterns(args.ignore.clone())
        .with_include_deps(args.include_deps)
        .with_threads(args.threads)
        .with_min_fold_lines(args.min_lines)
        .with_fold_filter(fold_filter)
        .with_syntax_highlight(!args.no_color)
        .with_preview_mode(args.preview_mode.clone().into());

    if let Some(languages) = language_filter {
        config = config.with_language_filter(languages);
    }

    if let Some(ref ignore_file) = args.ignore_file {
        config = config.with_ignore_file(ignore_file.clone());
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
    let scanner = FoldScanner::new(config)?;
    let result = scanner.scan()?;

    if let Some(ref pb) = spinner {
        pb.finish_with_message(format!(
            "Scanned {} files in {}ms",
            result.stats.total_files, result.metadata.scan_duration_ms
        ));
    }

    // Format output (grouped by default, flat with --flat flag)
    let output = if args.flat {
        format_output(&result, args.format.clone().into())?
    } else {
        format_output_grouped(&result, args.format.clone().into())?
    };

    // Write output
    if let Some(ref path) = args.output {
        fs::write(path, &output)?;
        if args.verbose {
            eprintln!("Output written to: {}", path.display());
        }
    } else {
        println!("{}", output);
    }

    Ok(())
}

fn run_analyze(
    path: PathBuf,
    format: OutputFormatArg,
    output_file: Option<PathBuf>,
    preview_mode: PreviewModeArg,
    args: &Args,
) -> anyhow::Result<()> {
    let config = ScanConfig::new(path)
        .with_min_fold_lines(args.min_lines)
        .with_threads(args.threads)
        .with_preview_mode(preview_mode.into());

    let scanner = FoldScanner::new(config)?;
    let result = scanner.scan()?;

    // Use specified format, or ANSI for terminal if not specified
    let output_format: OutputFormat = format.into();
    let output = format_output_grouped(&result, output_format)?;

    // Write output
    if let Some(ref path) = output_file {
        fs::write(path, &output)?;
        if args.verbose {
            eprintln!("Output written to: {}", path.display());
        }
    } else {
        println!("{}", output);
    }

    Ok(())
}

fn run_render(file: PathBuf, ansi: bool, min_lines: usize, args: &Args) -> anyhow::Result<()> {
    let fold_filter = build_fold_filter(&args.fold_types, &args.no_fold);

    let config = ScanConfig::default()
        .with_min_fold_lines(min_lines)
        .with_fold_filter(fold_filter)
        .with_syntax_highlight(!args.no_color)
        .with_preview_mode(args.preview_mode.clone().into());

    let rendered = if ansi || (atty::is(atty::Stream::Stdout) && !args.no_color) {
        render_file_ansi(&file, &config)?
    } else {
        render_file(&file, &config)?
    };

    println!("{}", rendered.content);

    if args.verbose {
        eprintln!(
            "\n--- {} folds applied, {} lines hidden ---",
            rendered.fold_count, rendered.lines_hidden
        );
    }

    Ok(())
}

fn run_list(file: PathBuf, format: OutputFormatArg, preview_mode: PreviewModeArg, args: &Args) -> anyhow::Result<()> {
    let config = ScanConfig::default()
        .with_min_fold_lines(args.min_lines)
        .with_preview_mode(preview_mode.into());

    let scanner = FoldScanner::new(config.clone())?;
    let source_file = scanner.scan_file(&file)?;

    let output = match format {
        OutputFormatArg::Json => serde_json::to_string_pretty(&source_file)?,
        OutputFormatArg::Yaml => serde_yaml::to_string(&source_file)?,
        OutputFormatArg::Summary | OutputFormatArg::Ansi => {
            let mut out = String::new();
            out.push_str(&format!(
                "File: {}\nLanguage: {:?}\nLine Count: {}\nFolds: {}\n\n",
                source_file.path.display(),
                source_file.language,
                source_file.line_count,
                source_file.folds.len()
            ));

            for (i, fold) in source_file.folds.iter().enumerate() {
                out.push_str(&format!(
                    "{}. {} (lines {}-{}, {} lines)\n",
                    i + 1,
                    fold.fold_type.as_str(),
                    fold.start_line,
                    fold.end_line,
                    fold.line_count
                ));
                if let Some(ref preview) = fold.preview {
                    out.push_str(&format!("   Preview: {}\n", preview));
                }
            }

            out
        }
    };

    println!("{}", output);
    Ok(())
}

fn build_fold_filter(include: &Option<String>, exclude: &Option<String>) -> FoldFilter {
    let mut filter = if include.is_some() {
        // Start with nothing enabled
        FoldFilter::default()
    } else {
        // Start with defaults
        FoldFilter::default_set()
    };

    // Enable specific types
    if let Some(ref types) = include {
        for t in types.split(',') {
            match t.trim() {
                "block" => filter.fold_blocks = true,
                "import" => filter.fold_imports = true,
                "arglist" => filter.fold_arglists = true,
                "chain" => filter.fold_chains = true,
                "literal" => filter.fold_literals = true,
                "comment" => filter.fold_comments = true,
                "doc" => filter.fold_docs = true,
                "class" => filter.fold_classes = true,
                "array" => filter.fold_arrays = true,
                "object" => filter.fold_objects = true,
                "all" => filter = FoldFilter::all(),
                _ => {}
            }
        }
    }

    // Exclude specific types
    if let Some(ref types) = exclude {
        for t in types.split(',') {
            match t.trim() {
                "block" => filter.fold_blocks = false,
                "import" => filter.fold_imports = false,
                "arglist" => filter.fold_arglists = false,
                "chain" => filter.fold_chains = false,
                "literal" => filter.fold_literals = false,
                "comment" => filter.fold_comments = false,
                "doc" => filter.fold_docs = false,
                "class" => filter.fold_classes = false,
                "array" => filter.fold_arrays = false,
                "object" => filter.fold_objects = false,
                _ => {}
            }
        }
    }

    filter
}
