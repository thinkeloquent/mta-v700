use serde::{Deserialize, Serialize};
use std::path::PathBuf;

/// Type of foldable code region
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum FoldType {
    /// Function/method body
    Block,
    /// Import/include statements
    Import,
    /// Function arguments or parameters
    ArgList,
    /// Chained method calls (builder pattern)
    ChainedCall,
    /// String/numeric literals
    Literal,
    /// Comments (single or multi-line)
    Comment,
    /// Documentation comments (docstrings, JSDoc)
    DocComment,
    /// Class/struct body
    ClassBody,
    /// Array/list literals
    ArrayLiteral,
    /// Object/dict literals
    ObjectLiteral,
}

impl FoldType {
    pub fn as_str(&self) -> &'static str {
        match self {
            FoldType::Block => "block",
            FoldType::Import => "import",
            FoldType::ArgList => "arglist",
            FoldType::ChainedCall => "chain",
            FoldType::Literal => "literal",
            FoldType::Comment => "comment",
            FoldType::DocComment => "doc",
            FoldType::ClassBody => "class",
            FoldType::ArrayLiteral => "array",
            FoldType::ObjectLiteral => "object",
        }
    }
}

/// Preview mode for fold summaries
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum PreviewMode {
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

impl PreviewMode {
    pub fn as_str(&self) -> &'static str {
        match self {
            PreviewMode::Minimal => "minimal",
            PreviewMode::Names => "names",
            PreviewMode::Flow => "flow",
            PreviewMode::Source => "source",
        }
    }
}

/// Language of the source file
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Language {
    Python,
    JavaScript,
    TypeScript,
}

impl Language {
    pub fn from_extension(ext: &str) -> Option<Self> {
        match ext.to_lowercase().as_str() {
            "py" | "pyi" => Some(Language::Python),
            "js" | "mjs" | "cjs" | "jsx" => Some(Language::JavaScript),
            "ts" | "mts" | "cts" | "tsx" => Some(Language::TypeScript),
            _ => None,
        }
    }

    pub fn as_str(&self) -> &'static str {
        match self {
            Language::Python => "python",
            Language::JavaScript => "javascript",
            Language::TypeScript => "typescript",
        }
    }
}

/// A foldable region in source code
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FoldRegion {
    /// Type of fold
    pub fold_type: FoldType,
    /// Start byte offset in source
    pub start_byte: usize,
    /// End byte offset in source
    pub end_byte: usize,
    /// Start line (1-indexed)
    pub start_line: usize,
    /// End line (1-indexed)
    pub end_line: usize,
    /// Start column (0-indexed)
    pub start_column: usize,
    /// End column (0-indexed)
    pub end_column: usize,
    /// Number of lines spanned
    pub line_count: usize,
    /// Preview text (first N chars or signature)
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub preview: Option<String>,
    /// Whether this fold is currently applied
    #[serde(default)]
    pub is_folded: bool,
    /// Nested folds within this region
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub children: Vec<FoldRegion>,
}

impl FoldRegion {
    pub fn new(
        fold_type: FoldType,
        start_byte: usize,
        end_byte: usize,
        start_line: usize,
        end_line: usize,
        start_column: usize,
        end_column: usize,
    ) -> Self {
        let line_count = if end_line >= start_line {
            end_line - start_line + 1
        } else {
            1
        };

        Self {
            fold_type,
            start_byte,
            end_byte,
            start_line,
            end_line,
            start_column,
            end_column,
            line_count,
            preview: None,
            is_folded: false,
            children: Vec::new(),
        }
    }

    /// Check if this region contains another
    pub fn contains(&self, other: &FoldRegion) -> bool {
        self.start_byte <= other.start_byte && self.end_byte >= other.end_byte
    }

    /// Check if this region overlaps with another
    pub fn overlaps(&self, other: &FoldRegion) -> bool {
        self.start_byte < other.end_byte && self.end_byte > other.start_byte
    }
}

/// A source file with its fold regions
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SourceFile {
    /// Relative path from project root
    pub path: PathBuf,
    /// Absolute path
    pub absolute_path: PathBuf,
    /// Detected language
    pub language: Language,
    /// All fold regions in this file
    pub folds: Vec<FoldRegion>,
    /// Total line count
    pub line_count: usize,
    /// Whether the file was parsed successfully
    pub parsed: bool,
    /// Parse error message if any
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub error: Option<String>,
}

/// Statistics about fold analysis
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct FoldStats {
    pub total_files: usize,
    pub total_folds: usize,
    pub block_folds: usize,
    pub import_folds: usize,
    pub arglist_folds: usize,
    pub chain_folds: usize,
    pub literal_folds: usize,
    pub comment_folds: usize,
    pub doc_folds: usize,
    pub class_folds: usize,
    pub array_folds: usize,
    pub object_folds: usize,
    pub python_files: usize,
    pub javascript_files: usize,
    pub typescript_files: usize,
    pub total_lines: usize,
    pub foldable_lines: usize,
}

impl FoldStats {
    pub fn add_fold(&mut self, fold_type: &FoldType) {
        self.total_folds += 1;
        match fold_type {
            FoldType::Block => self.block_folds += 1,
            FoldType::Import => self.import_folds += 1,
            FoldType::ArgList => self.arglist_folds += 1,
            FoldType::ChainedCall => self.chain_folds += 1,
            FoldType::Literal => self.literal_folds += 1,
            FoldType::Comment => self.comment_folds += 1,
            FoldType::DocComment => self.doc_folds += 1,
            FoldType::ClassBody => self.class_folds += 1,
            FoldType::ArrayLiteral => self.array_folds += 1,
            FoldType::ObjectLiteral => self.object_folds += 1,
        }
    }
}

/// Scan metadata
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScanMetadata {
    pub scan_duration_ms: u64,
    pub files_per_second: f64,
    pub timestamp: String,
    pub tool_version: String,
}

impl Default for ScanMetadata {
    fn default() -> Self {
        Self {
            scan_duration_ms: 0,
            files_per_second: 0.0,
            timestamp: chrono::Utc::now().to_rfc3339(),
            tool_version: env!("CARGO_PKG_VERSION").to_string(),
        }
    }
}

/// Language-specific section of the fold map
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LanguageSection {
    /// Source files for this language
    pub files: Vec<SourceFile>,
    /// Fold statistics for this language
    pub stats: LanguageFoldStats,
}

/// Statistics for a single language
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct LanguageFoldStats {
    pub total_files: usize,
    pub total_folds: usize,
    pub block_folds: usize,
    pub import_folds: usize,
    pub arglist_folds: usize,
    pub chain_folds: usize,
    pub literal_folds: usize,
    pub comment_folds: usize,
    pub doc_folds: usize,
    pub class_folds: usize,
    pub array_folds: usize,
    pub object_folds: usize,
    pub total_lines: usize,
    pub foldable_lines: usize,
}

/// Aggregated fold analysis results
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FoldMap {
    /// Project root path
    pub root: PathBuf,
    /// All source files analyzed
    pub files: Vec<SourceFile>,
    /// Fold statistics
    pub stats: FoldStats,
    /// Scan metadata
    pub metadata: ScanMetadata,
}

impl FoldMap {
    /// Convert to grouped format (python/nodejs sections)
    pub fn to_grouped(&self) -> GroupedFoldMap {
        // Separate files by language
        let python_files: Vec<SourceFile> = self
            .files
            .iter()
            .filter(|f| f.language == Language::Python)
            .cloned()
            .collect();

        let nodejs_files: Vec<SourceFile> = self
            .files
            .iter()
            .filter(|f| f.language == Language::JavaScript || f.language == Language::TypeScript)
            .cloned()
            .collect();

        // Calculate stats for each language
        let python_stats = Self::calculate_language_stats(&python_files);
        let nodejs_stats = Self::calculate_language_stats(&nodejs_files);

        GroupedFoldMap {
            root: self.root.clone(),
            python: LanguageSection {
                files: python_files,
                stats: python_stats,
            },
            nodejs: LanguageSection {
                files: nodejs_files,
                stats: nodejs_stats,
            },
            metadata: self.metadata.clone(),
        }
    }

    fn calculate_language_stats(files: &[SourceFile]) -> LanguageFoldStats {
        let mut stats = LanguageFoldStats::default();
        stats.total_files = files.len();

        for file in files {
            stats.total_lines += file.line_count;
            for fold in &file.folds {
                stats.total_folds += 1;
                stats.foldable_lines += fold.line_count;
                match fold.fold_type {
                    FoldType::Block => stats.block_folds += 1,
                    FoldType::Import => stats.import_folds += 1,
                    FoldType::ArgList => stats.arglist_folds += 1,
                    FoldType::ChainedCall => stats.chain_folds += 1,
                    FoldType::Literal => stats.literal_folds += 1,
                    FoldType::Comment => stats.comment_folds += 1,
                    FoldType::DocComment => stats.doc_folds += 1,
                    FoldType::ClassBody => stats.class_folds += 1,
                    FoldType::ArrayLiteral => stats.array_folds += 1,
                    FoldType::ObjectLiteral => stats.object_folds += 1,
                }
            }
        }

        stats
    }
}

/// Grouped fold map with separate sections for Python and Node.js
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GroupedFoldMap {
    /// Project root path
    pub root: PathBuf,
    /// Python folds
    pub python: LanguageSection,
    /// Node.js (JavaScript + TypeScript) folds
    pub nodejs: LanguageSection,
    /// Scan metadata
    pub metadata: ScanMetadata,
}

/// Rendered output for a single file
#[derive(Debug, Clone)]
pub struct RenderedFile {
    pub path: PathBuf,
    pub content: String,
    pub fold_count: usize,
    pub lines_hidden: usize,
}

/// Configuration for which fold types to apply
#[derive(Debug, Clone, Default)]
pub struct FoldFilter {
    pub fold_blocks: bool,
    pub fold_imports: bool,
    pub fold_arglists: bool,
    pub fold_chains: bool,
    pub fold_literals: bool,
    pub fold_comments: bool,
    pub fold_docs: bool,
    pub fold_classes: bool,
    pub fold_arrays: bool,
    pub fold_objects: bool,
}

impl FoldFilter {
    /// Create a filter that folds everything
    pub fn all() -> Self {
        Self {
            fold_blocks: true,
            fold_imports: true,
            fold_arglists: true,
            fold_chains: true,
            fold_literals: true,
            fold_comments: true,
            fold_docs: true,
            fold_classes: true,
            fold_arrays: true,
            fold_objects: true,
        }
    }

    /// Create a default filter (blocks, imports, comments)
    pub fn default_set() -> Self {
        Self {
            fold_blocks: true,
            fold_imports: true,
            fold_arglists: false,
            fold_chains: false,
            fold_literals: true,
            fold_comments: true,
            fold_docs: false,
            fold_classes: false,
            fold_arrays: true,
            fold_objects: true,
        }
    }

    /// Check if a fold type should be applied
    pub fn should_fold(&self, fold_type: &FoldType) -> bool {
        match fold_type {
            FoldType::Block => self.fold_blocks,
            FoldType::Import => self.fold_imports,
            FoldType::ArgList => self.fold_arglists,
            FoldType::ChainedCall => self.fold_chains,
            FoldType::Literal => self.fold_literals,
            FoldType::Comment => self.fold_comments,
            FoldType::DocComment => self.fold_docs,
            FoldType::ClassBody => self.fold_classes,
            FoldType::ArrayLiteral => self.fold_arrays,
            FoldType::ObjectLiteral => self.fold_objects,
        }
    }
}
