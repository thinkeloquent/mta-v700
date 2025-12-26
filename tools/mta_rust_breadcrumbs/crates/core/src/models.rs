//! Data models for structural code navigation
//!
//! This module defines the core data structures used throughout the breadcrumbs tool,
//! including AST node types, breadcrumb trails, and hierarchical outlines.

use serde::{Deserialize, Serialize};
use std::path::PathBuf;

/// Supported programming languages
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Language {
    Python,
    JavaScript,
    TypeScript,
}

impl Language {
    /// Determine language from file extension
    pub fn from_extension(ext: &str) -> Option<Self> {
        match ext.to_lowercase().as_str() {
            "py" | "pyi" => Some(Language::Python),
            "js" | "mjs" | "cjs" | "jsx" => Some(Language::JavaScript),
            "ts" | "mts" | "cts" | "tsx" => Some(Language::TypeScript),
            _ => None,
        }
    }

    /// Get display name for the language
    pub fn display_name(&self) -> &'static str {
        match self {
            Language::Python => "Python",
            Language::JavaScript => "JavaScript",
            Language::TypeScript => "TypeScript",
        }
    }

    /// Check if language belongs to Node.js ecosystem
    pub fn is_nodejs(&self) -> bool {
        matches!(self, Language::JavaScript | Language::TypeScript)
    }
}

/// Types of structural nodes that can appear in breadcrumbs
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum NodeType {
    // Common
    Module,
    Class,
    Function,
    Method,
    AsyncFunction,
    AsyncMethod,
    Property,
    Constructor,
    Getter,
    Setter,

    // Python-specific
    Decorator,
    Lambda,
    Comprehension,
    WithStatement,
    TryBlock,
    ExceptHandler,
    FinallyBlock,

    // JavaScript/TypeScript-specific
    ArrowFunction,
    Interface,
    TypeAlias,
    Enum,
    Namespace,
    ObjectLiteral,
    ArrayLiteral,

    // Control flow
    IfStatement,
    ElseClause,
    ElifClause,
    ForLoop,
    WhileLoop,
    SwitchStatement,
    CaseClause,

    // Error recovery
    ErrorNode,
    Unknown,
}

impl NodeType {
    /// Get human-readable label for the node type
    pub fn label(&self) -> &'static str {
        match self {
            NodeType::Module => "module",
            NodeType::Class => "class",
            NodeType::Function => "function",
            NodeType::Method => "method",
            NodeType::AsyncFunction => "async function",
            NodeType::AsyncMethod => "async method",
            NodeType::Property => "property",
            NodeType::Constructor => "constructor",
            NodeType::Getter => "getter",
            NodeType::Setter => "setter",
            NodeType::Decorator => "decorator",
            NodeType::Lambda => "lambda",
            NodeType::Comprehension => "comprehension",
            NodeType::WithStatement => "with",
            NodeType::TryBlock => "try",
            NodeType::ExceptHandler => "except",
            NodeType::FinallyBlock => "finally",
            NodeType::ArrowFunction => "arrow fn",
            NodeType::Interface => "interface",
            NodeType::TypeAlias => "type",
            NodeType::Enum => "enum",
            NodeType::Namespace => "namespace",
            NodeType::ObjectLiteral => "object",
            NodeType::ArrayLiteral => "array",
            NodeType::IfStatement => "if",
            NodeType::ElseClause => "else",
            NodeType::ElifClause => "elif",
            NodeType::ForLoop => "for",
            NodeType::WhileLoop => "while",
            NodeType::SwitchStatement => "switch",
            NodeType::CaseClause => "case",
            NodeType::ErrorNode => "error",
            NodeType::Unknown => "unknown",
        }
    }

    /// Check if this node type is a named scope (function, class, method)
    pub fn is_named_scope(&self) -> bool {
        matches!(
            self,
            NodeType::Class
                | NodeType::Function
                | NodeType::Method
                | NodeType::AsyncFunction
                | NodeType::AsyncMethod
                | NodeType::Constructor
                | NodeType::Getter
                | NodeType::Setter
                | NodeType::Interface
                | NodeType::Enum
                | NodeType::Namespace
        )
    }

    /// Check if this is a recoverable error node
    pub fn is_error(&self) -> bool {
        matches!(self, NodeType::ErrorNode)
    }
}

/// A single component in a breadcrumb trail
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BreadcrumbComponent {
    /// Type of the structural node
    pub node_type: NodeType,

    /// Name of the node (function name, class name, etc.)
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub name: Option<String>,

    /// Starting line number (1-indexed)
    pub start_line: usize,

    /// Ending line number (1-indexed)
    pub end_line: usize,

    /// Starting byte offset
    pub start_byte: usize,

    /// Ending byte offset
    pub end_byte: usize,

    /// Depth in the hierarchy (0 = root)
    pub depth: usize,

    /// Whether this node contains syntax errors
    #[serde(default)]
    pub has_error: bool,
}

impl BreadcrumbComponent {
    /// Get display text for this component
    pub fn display(&self) -> String {
        match &self.name {
            Some(name) => format!("{} {}", self.node_type.label(), name),
            None => self.node_type.label().to_string(),
        }
    }

    /// Get short display (name only or type)
    pub fn short_display(&self) -> String {
        match &self.name {
            Some(name) => name.clone(),
            None => self.node_type.label().to_string(),
        }
    }
}

/// A breadcrumb trail representing the hierarchy at a specific location
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Breadcrumb {
    /// The components of the breadcrumb trail (from root to current)
    pub components: Vec<BreadcrumbComponent>,

    /// Line number where the breadcrumb applies
    pub line: usize,

    /// Column number (0-indexed)
    pub column: usize,

    /// Byte offset in the source
    pub byte_offset: usize,
}

impl Breadcrumb {
    /// Create an empty breadcrumb
    pub fn empty(line: usize, column: usize, byte_offset: usize) -> Self {
        Self {
            components: Vec::new(),
            line,
            column,
            byte_offset,
        }
    }

    /// Get the formatted path string
    pub fn path(&self) -> String {
        self.components
            .iter()
            .map(|c| c.short_display())
            .collect::<Vec<_>>()
            .join(" > ")
    }

    /// Get the depth of the current location
    pub fn depth(&self) -> usize {
        self.components.len()
    }

    /// Get the innermost (current) scope
    pub fn current_scope(&self) -> Option<&BreadcrumbComponent> {
        self.components.last()
    }

    /// Get the nearest named scope (function, class, etc.)
    pub fn nearest_named_scope(&self) -> Option<&BreadcrumbComponent> {
        self.components.iter().rev().find(|c| c.node_type.is_named_scope())
    }
}

/// An outline node representing a structural element
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OutlineNode {
    /// Type of the structural node
    pub node_type: NodeType,

    /// Name of the node
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub name: Option<String>,

    /// Starting line number (1-indexed)
    pub start_line: usize,

    /// Ending line number (1-indexed)
    pub end_line: usize,

    /// Number of lines in this node
    pub line_count: usize,

    /// Depth in the hierarchy
    pub depth: usize,

    /// Preview of the first line (signature)
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub preview: Option<String>,

    /// Child nodes
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub children: Vec<OutlineNode>,

    /// Whether this node contains syntax errors
    #[serde(default)]
    pub has_error: bool,
}

impl OutlineNode {
    /// Create a new outline node
    pub fn new(node_type: NodeType, name: Option<String>, start_line: usize, end_line: usize) -> Self {
        Self {
            node_type,
            name,
            start_line,
            end_line,
            line_count: end_line.saturating_sub(start_line) + 1,
            depth: 0,
            preview: None,
            children: Vec::new(),
            has_error: false,
        }
    }

    /// Get display text
    pub fn display(&self) -> String {
        match &self.name {
            Some(name) => format!("{} {}", self.node_type.label(), name),
            None => self.node_type.label().to_string(),
        }
    }

    /// Flatten the tree into a list with depth information
    pub fn flatten(&self) -> Vec<&OutlineNode> {
        let mut result = vec![self];
        for child in &self.children {
            result.extend(child.flatten());
        }
        result
    }

    /// Count total nodes in this subtree
    pub fn total_nodes(&self) -> usize {
        1 + self.children.iter().map(|c| c.total_nodes()).sum::<usize>()
    }
}

/// Complete outline for a source file
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FileOutline {
    /// Path to the source file
    pub path: PathBuf,

    /// Absolute path to the source file
    pub absolute_path: PathBuf,

    /// Language of the source file
    pub language: Language,

    /// Total number of lines in the file
    pub total_lines: usize,

    /// Root-level outline nodes
    pub nodes: Vec<OutlineNode>,

    /// Parse errors encountered (if any)
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub errors: Vec<ParseError>,
}

impl FileOutline {
    /// Get total number of structural nodes
    pub fn total_nodes(&self) -> usize {
        self.nodes.iter().map(|n| n.total_nodes()).sum()
    }

    /// Flatten all nodes into a list
    pub fn flatten(&self) -> Vec<&OutlineNode> {
        self.nodes.iter().flat_map(|n| n.flatten()).collect()
    }

    /// Check if file has parse errors
    pub fn has_errors(&self) -> bool {
        !self.errors.is_empty()
    }
}

/// Parse error information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ParseError {
    /// Line number where error occurred
    pub line: usize,

    /// Column number
    pub column: usize,

    /// Error message
    pub message: String,

    /// Error type (missing, unexpected, etc.)
    pub error_type: String,
}

/// Language-grouped section for output
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LanguageSection {
    /// Language name
    pub language: String,

    /// Files in this section
    pub files: Vec<FileOutline>,

    /// Total files in section
    pub file_count: usize,

    /// Total structural nodes across all files
    pub total_nodes: usize,

    /// Total lines across all files
    pub total_lines: usize,

    /// Files with errors
    pub files_with_errors: usize,
}

impl LanguageSection {
    /// Create a new language section
    pub fn new(language: &str, files: Vec<FileOutline>) -> Self {
        let file_count = files.len();
        let total_nodes = files.iter().map(|f| f.total_nodes()).sum();
        let total_lines = files.iter().map(|f| f.total_lines).sum();
        let files_with_errors = files.iter().filter(|f| f.has_errors()).count();

        Self {
            language: language.to_string(),
            files,
            file_count,
            total_nodes,
            total_lines,
            files_with_errors,
        }
    }
}

/// Grouped output structure by language
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GroupedOutlineMap {
    /// Project root directory
    pub root: PathBuf,

    /// Python files section
    pub python: LanguageSection,

    /// Node.js files section (JavaScript + TypeScript)
    pub nodejs: LanguageSection,

    /// Scan metadata
    pub metadata: ScanMetadata,
}

/// Flat output structure
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OutlineMap {
    /// Project root directory
    pub root: PathBuf,

    /// All source files
    pub files: Vec<FileOutline>,

    /// Summary statistics
    pub stats: ScanStats,

    /// Scan metadata
    pub metadata: ScanMetadata,
}

impl OutlineMap {
    /// Convert to grouped format by language
    pub fn to_grouped(&self) -> GroupedOutlineMap {
        let python_files: Vec<FileOutline> = self
            .files
            .iter()
            .filter(|f| f.language == Language::Python)
            .cloned()
            .collect();

        let nodejs_files: Vec<FileOutline> = self
            .files
            .iter()
            .filter(|f| f.language.is_nodejs())
            .cloned()
            .collect();

        GroupedOutlineMap {
            root: self.root.clone(),
            python: LanguageSection::new("python", python_files),
            nodejs: LanguageSection::new("nodejs", nodejs_files),
            metadata: self.metadata.clone(),
        }
    }
}

/// Summary statistics for a scan
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScanStats {
    /// Total files scanned
    pub total_files: usize,

    /// Total lines across all files
    pub total_lines: usize,

    /// Total structural nodes found
    pub total_nodes: usize,

    /// Python files count
    pub python_files: usize,

    /// JavaScript files count
    pub javascript_files: usize,

    /// TypeScript files count
    pub typescript_files: usize,

    /// Files with parse errors
    pub files_with_errors: usize,
}

/// Metadata about the scan operation
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScanMetadata {
    /// Duration of scan in milliseconds
    pub scan_duration_ms: u64,

    /// Files processed per second
    pub files_per_second: f64,

    /// ISO timestamp of scan
    pub timestamp: String,

    /// Tool version
    pub tool_version: String,
}
