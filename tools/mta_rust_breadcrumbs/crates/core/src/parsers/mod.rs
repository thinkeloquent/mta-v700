//! Parsers module for structural code analysis
//!
//! This module provides resilient parsing using Tree-sitter to extract
//! hierarchical structure from source code, even when it contains syntax errors.

mod python;
mod javascript;

pub use javascript::JavaScriptParser;
pub use python::PythonParser;

use crate::config::ScanConfig;
use crate::models::{Breadcrumb, Language, NodeType, OutlineNode, ParseError};
use thiserror::Error;

/// Parser errors
#[derive(Error, Debug)]
pub enum ParserError {
    #[error("Failed to initialize parser: {0}")]
    InitError(String),

    #[error("Failed to parse source code: {0}")]
    ParseError(String),

    #[error("Unsupported language: {0:?}")]
    UnsupportedLanguage(Language),

    #[error("File too large: {0} bytes")]
    FileTooLarge(usize),
}

/// Trait for language-specific parsers
pub trait BreadcrumbParser: Send + Sync {
    /// Get the language this parser handles
    fn language(&self) -> Language;

    /// Parse source code and extract outline
    fn parse_outline(
        &mut self,
        source: &str,
        config: &ScanConfig,
    ) -> Result<Vec<OutlineNode>, ParserError>;

    /// Get breadcrumb at a specific byte offset
    fn get_breadcrumb_at(
        &mut self,
        source: &str,
        byte_offset: usize,
        config: &ScanConfig,
    ) -> Result<Breadcrumb, ParserError>;

    /// Extract parse errors from the tree
    fn extract_errors(&self, source: &str, tree: &tree_sitter::Tree) -> Vec<ParseError>;
}

/// Create a parser for the specified language
pub fn create_parser(language: &Language) -> Result<Box<dyn BreadcrumbParser>, ParserError> {
    match language {
        Language::Python => Ok(Box::new(PythonParser::new()?)),
        Language::JavaScript => Ok(Box::new(JavaScriptParser::new(false)?)),
        Language::TypeScript => Ok(Box::new(JavaScriptParser::new(true)?)),
    }
}

/// Parse a source file and return its outline
pub fn parse_file(
    source: &str,
    language: &Language,
    config: &ScanConfig,
) -> Result<(Vec<OutlineNode>, Vec<ParseError>), ParserError> {
    let mut parser = create_parser(language)?;
    let nodes = parser.parse_outline(source, config)?;

    // Create a temporary tree to extract errors
    let mut ts_parser = tree_sitter::Parser::new();
    let ts_lang = match language {
        Language::Python => tree_sitter_python::LANGUAGE.into(),
        Language::JavaScript => tree_sitter_javascript::LANGUAGE.into(),
        Language::TypeScript => tree_sitter_typescript::LANGUAGE_TYPESCRIPT.into(),
    };
    ts_parser.set_language(&ts_lang).ok();
    let errors = if let Some(tree) = ts_parser.parse(source, None) {
        parser.extract_errors(source, &tree)
    } else {
        Vec::new()
    };

    Ok((nodes, errors))
}

/// Get breadcrumb at a specific line and column
pub fn get_breadcrumb_at_position(
    source: &str,
    language: &Language,
    line: usize,
    column: usize,
    config: &ScanConfig,
) -> Result<Breadcrumb, ParserError> {
    // Convert line/column to byte offset
    let byte_offset = line_column_to_byte(source, line, column);
    let mut parser = create_parser(language)?;
    parser.get_breadcrumb_at(source, byte_offset, config)
}

/// Convert line/column (1-indexed) to byte offset
fn line_column_to_byte(source: &str, line: usize, column: usize) -> usize {
    let mut current_line = 1;
    let mut current_byte = 0;

    for (idx, ch) in source.char_indices() {
        if current_line == line {
            // Found the line, now count columns
            let mut col = 0;
            for (col_idx, col_ch) in source[idx..].char_indices() {
                if col == column {
                    return idx + col_idx;
                }
                if col_ch == '\n' {
                    break;
                }
                col += 1;
            }
            return idx + column.min(source[idx..].find('\n').unwrap_or(source[idx..].len()));
        }
        if ch == '\n' {
            current_line += 1;
        }
        current_byte = idx;
    }

    current_byte
}

/// Helper to map tree-sitter node kind to NodeType
pub fn map_node_kind(kind: &str, language: &Language) -> Option<NodeType> {
    match language {
        Language::Python => map_python_node_kind(kind),
        Language::JavaScript | Language::TypeScript => map_js_node_kind(kind),
    }
}

fn map_python_node_kind(kind: &str) -> Option<NodeType> {
    match kind {
        "module" => Some(NodeType::Module),
        "class_definition" => Some(NodeType::Class),
        "function_definition" => Some(NodeType::Function),
        "async_function_definition" => Some(NodeType::AsyncFunction),
        "decorated_definition" => Some(NodeType::Decorator),
        "lambda" => Some(NodeType::Lambda),
        "list_comprehension" | "dict_comprehension" | "set_comprehension" | "generator_expression" => {
            Some(NodeType::Comprehension)
        }
        "with_statement" => Some(NodeType::WithStatement),
        "try_statement" => Some(NodeType::TryBlock),
        "except_clause" => Some(NodeType::ExceptHandler),
        "finally_clause" => Some(NodeType::FinallyBlock),
        "if_statement" => Some(NodeType::IfStatement),
        "elif_clause" => Some(NodeType::ElifClause),
        "else_clause" => Some(NodeType::ElseClause),
        "for_statement" => Some(NodeType::ForLoop),
        "while_statement" => Some(NodeType::WhileLoop),
        "ERROR" => Some(NodeType::ErrorNode),
        _ => None,
    }
}

fn map_js_node_kind(kind: &str) -> Option<NodeType> {
    match kind {
        "program" => Some(NodeType::Module),
        "class_declaration" | "class" => Some(NodeType::Class),
        "function_declaration" | "function" => Some(NodeType::Function),
        "method_definition" => Some(NodeType::Method),
        "arrow_function" => Some(NodeType::ArrowFunction),
        "generator_function_declaration" | "generator_function" => Some(NodeType::Function),
        "interface_declaration" => Some(NodeType::Interface),
        "type_alias_declaration" => Some(NodeType::TypeAlias),
        "enum_declaration" => Some(NodeType::Enum),
        "namespace_declaration" | "module" => Some(NodeType::Namespace),
        "object" | "object_pattern" => Some(NodeType::ObjectLiteral),
        "array" | "array_pattern" => Some(NodeType::ArrayLiteral),
        "if_statement" => Some(NodeType::IfStatement),
        "else_clause" => Some(NodeType::ElseClause),
        "for_statement" | "for_in_statement" => Some(NodeType::ForLoop),
        "while_statement" => Some(NodeType::WhileLoop),
        "switch_statement" => Some(NodeType::SwitchStatement),
        "switch_case" => Some(NodeType::CaseClause),
        "try_statement" => Some(NodeType::TryBlock),
        "catch_clause" => Some(NodeType::ExceptHandler),
        "finally_clause" => Some(NodeType::FinallyBlock),
        "ERROR" => Some(NodeType::ErrorNode),
        _ => None,
    }
}

/// Extract name from a tree-sitter node
pub fn extract_node_name(node: &tree_sitter::Node, source: &[u8]) -> Option<String> {
    // Look for name child node
    for i in 0..node.child_count() as usize {
        if let Some(child) = node.child(i as u32) {
            let kind = child.kind();
            if kind == "identifier"
                || kind == "name"
                || kind == "property_identifier"
                || kind == "type_identifier"
            {
                return Some(child.utf8_text(source).ok()?.to_string());
            }
        }
    }

    // Try named children
    if let Some(name_node) = node.child_by_field_name("name") {
        return Some(name_node.utf8_text(source).ok()?.to_string());
    }

    None
}

/// Extract preview line from source
pub fn extract_preview(node: &tree_sitter::Node, source: &str, max_length: usize) -> Option<String> {
    let start = node.start_byte();
    let end = node.end_byte().min(source.len());

    if start >= source.len() {
        return None;
    }

    let slice = &source[start..end];
    let first_line = slice.lines().next()?;
    let trimmed = first_line.trim();

    if trimmed.len() > max_length {
        Some(format!("{}...", &trimmed[..max_length - 3]))
    } else {
        Some(trimmed.to_string())
    }
}
