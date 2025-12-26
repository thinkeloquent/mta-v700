//! JavaScript/TypeScript parser for structural code analysis
//!
//! This module implements resilient parsing of JavaScript and TypeScript source code
//! using Tree-sitter, with robust error recovery to handle incomplete or malformed code.

use crate::config::ScanConfig;
use crate::models::{Breadcrumb, BreadcrumbComponent, Language, NodeType, OutlineNode, ParseError};
use crate::parsers::{extract_node_name, extract_preview, map_js_node_kind, BreadcrumbParser, ParserError};
use tree_sitter::{Node, Parser, Tree};

/// JavaScript/TypeScript parser implementation
pub struct JavaScriptParser {
    parser: Parser,
    is_typescript: bool,
}

impl JavaScriptParser {
    /// Create a new JavaScript/TypeScript parser
    pub fn new(typescript: bool) -> Result<Self, ParserError> {
        let mut parser = Parser::new();

        let language = if typescript {
            tree_sitter_typescript::LANGUAGE_TYPESCRIPT.into()
        } else {
            tree_sitter_javascript::LANGUAGE.into()
        };

        parser
            .set_language(&language)
            .map_err(|e| ParserError::InitError(e.to_string()))?;

        Ok(Self {
            parser,
            is_typescript: typescript,
        })
    }

    /// Parse source code into a tree
    fn parse_tree(&mut self, source: &str) -> Result<Tree, ParserError> {
        self.parser
            .parse(source, None)
            .ok_or_else(|| ParserError::ParseError("Failed to parse source".to_string()))
    }

    /// Traverse the tree and extract outline nodes
    fn traverse_node(
        &self,
        node: &Node,
        source: &[u8],
        source_str: &str,
        depth: usize,
        config: &ScanConfig,
    ) -> Vec<OutlineNode> {
        let mut results = Vec::new();

        // Check if this node should be included
        if let Some(node_type) = map_js_node_kind(node.kind()) {
            // Apply node filter
            if let Some(max_depth) = config.node_filter.max_depth {
                if depth > max_depth {
                    return results;
                }
            }

            if config.node_filter.named_scopes_only && !node_type.is_named_scope() {
                // Skip non-named scopes but still traverse children
                let mut cursor = node.walk();
                for child in node.children(&mut cursor) {
                    results.extend(self.traverse_node(&child, source, source_str, depth, config));
                }
                return results;
            }

            if config.node_filter.exclude_control_flow {
                match node_type {
                    NodeType::IfStatement
                    | NodeType::ElseClause
                    | NodeType::ForLoop
                    | NodeType::WhileLoop
                    | NodeType::SwitchStatement
                    | NodeType::CaseClause
                    | NodeType::TryBlock
                    | NodeType::ExceptHandler
                    | NodeType::FinallyBlock => {
                        let mut cursor = node.walk();
                        for child in node.children(&mut cursor) {
                            results.extend(self.traverse_node(&child, source, source_str, depth, config));
                        }
                        return results;
                    }
                    _ => {}
                }
            }

            let name = self.extract_js_name(node, source);
            let node_type = self.refine_node_type(node, &node_type, source);
            let start_line = node.start_position().row + 1;
            let end_line = node.end_position().row + 1;

            let mut outline_node = OutlineNode::new(node_type, name, start_line, end_line);
            outline_node.depth = depth;
            outline_node.has_error = node.has_error();

            if config.include_preview {
                outline_node.preview = extract_preview(node, source_str, config.max_preview_length);
            }

            // Traverse children
            let mut cursor = node.walk();
            for child in node.children(&mut cursor) {
                outline_node
                    .children
                    .extend(self.traverse_node(&child, source, source_str, depth + 1, config));
            }

            results.push(outline_node);
        } else {
            // Check for special cases that need name extraction
            if self.is_variable_with_function(node, source) {
                if let Some(outline) = self.extract_variable_function(node, source, source_str, depth, config) {
                    results.push(outline);
                    return results; // Don't double-traverse
                }
            }

            // Not a tracked node type, but traverse children
            let mut cursor = node.walk();
            for child in node.children(&mut cursor) {
                results.extend(self.traverse_node(&child, source, source_str, depth, config));
            }
        }

        results
    }

    /// Refine node type based on context (e.g., method vs function)
    fn refine_node_type(&self, node: &Node, base_type: &NodeType, source: &[u8]) -> NodeType {
        match node.kind() {
            "method_definition" => {
                // Check for getter/setter/constructor
                if let Some(kind_node) = node.child_by_field_name("kind") {
                    let kind_text = kind_node.utf8_text(source).unwrap_or("");
                    match kind_text {
                        "get" => return NodeType::Getter,
                        "set" => return NodeType::Setter,
                        _ => {}
                    }
                }
                if let Some(name_node) = node.child_by_field_name("name") {
                    let name = name_node.utf8_text(source).unwrap_or("");
                    if name == "constructor" {
                        return NodeType::Constructor;
                    }
                }
                // Check if async
                for i in 0..node.child_count() as usize {
                    if let Some(child) = node.child(i as u32) {
                        if child.kind() == "async" {
                            return NodeType::AsyncMethod;
                        }
                    }
                }
                NodeType::Method
            }
            "function_declaration" | "function" => {
                // Check if async
                for i in 0..node.child_count() as usize {
                    if let Some(child) = node.child(i as u32) {
                        if child.kind() == "async" {
                            return NodeType::AsyncFunction;
                        }
                    }
                }
                base_type.clone()
            }
            _ => base_type.clone(),
        }
    }

    /// Extract name for JavaScript-specific nodes
    fn extract_js_name(&self, node: &Node, source: &[u8]) -> Option<String> {
        match node.kind() {
            "class_declaration" | "function_declaration" => {
                node.child_by_field_name("name")
                    .and_then(|n| n.utf8_text(source).ok())
                    .map(|s| s.to_string())
            }
            "method_definition" => {
                node.child_by_field_name("name")
                    .and_then(|n| n.utf8_text(source).ok())
                    .map(|s| s.to_string())
            }
            "interface_declaration" | "type_alias_declaration" | "enum_declaration" => {
                node.child_by_field_name("name")
                    .and_then(|n| n.utf8_text(source).ok())
                    .map(|s| s.to_string())
            }
            "arrow_function" => {
                // Arrow functions often assigned to variables
                // Check parent for variable name
                if let Some(parent) = node.parent() {
                    if parent.kind() == "variable_declarator" {
                        return parent
                            .child_by_field_name("name")
                            .and_then(|n| n.utf8_text(source).ok())
                            .map(|s| s.to_string());
                    }
                }
                None
            }
            _ => extract_node_name(node, source),
        }
    }

    /// Check if this is a variable declaration with a function value
    fn is_variable_with_function(&self, node: &Node, _source: &[u8]) -> bool {
        if node.kind() != "lexical_declaration" && node.kind() != "variable_declaration" {
            return false;
        }

        let mut cursor = node.walk();
        for child in node.children(&mut cursor) {
            if child.kind() == "variable_declarator" {
                if let Some(value) = child.child_by_field_name("value") {
                    let kind = value.kind();
                    if kind == "arrow_function" || kind == "function" {
                        return true;
                    }
                }
            }
        }

        false
    }

    /// Extract a variable declaration with function value as an outline node
    fn extract_variable_function(
        &self,
        node: &Node,
        source: &[u8],
        source_str: &str,
        depth: usize,
        config: &ScanConfig,
    ) -> Option<OutlineNode> {
        let mut cursor = node.walk();
        for child in node.children(&mut cursor) {
            if child.kind() == "variable_declarator" {
                let name = child
                    .child_by_field_name("name")
                    .and_then(|n| n.utf8_text(source).ok())
                    .map(|s| s.to_string());

                if let Some(value) = child.child_by_field_name("value") {
                    let node_type = match value.kind() {
                        "arrow_function" => NodeType::ArrowFunction,
                        "function" => NodeType::Function,
                        _ => return None,
                    };

                    // Check for async
                    let node_type = if self.is_async_function(&value) {
                        NodeType::AsyncFunction
                    } else {
                        node_type
                    };

                    let start_line = node.start_position().row + 1;
                    let end_line = node.end_position().row + 1;

                    let mut outline = OutlineNode::new(node_type, name, start_line, end_line);
                    outline.depth = depth;
                    outline.has_error = node.has_error();

                    if config.include_preview {
                        outline.preview = extract_preview(node, source_str, config.max_preview_length);
                    }

                    // Traverse the function body for children
                    let mut inner_cursor = value.walk();
                    for inner_child in value.children(&mut inner_cursor) {
                        outline
                            .children
                            .extend(self.traverse_node(&inner_child, source, source_str, depth + 1, config));
                    }

                    return Some(outline);
                }
            }
        }

        None
    }

    /// Check if a function node is async
    fn is_async_function(&self, node: &Node) -> bool {
        for i in 0..node.child_count() as usize {
            if let Some(child) = node.child(i as u32) {
                if child.kind() == "async" {
                    return true;
                }
            }
        }
        false
    }

    /// Build breadcrumb trail from node to root
    fn build_breadcrumb_from_node(
        &self,
        node: &Node,
        source: &[u8],
        line: usize,
        column: usize,
        byte_offset: usize,
    ) -> Breadcrumb {
        let mut stack = Vec::new();
        let mut current = Some(*node);

        // Collect nodes from leaf to root
        while let Some(n) = current {
            if let Some(node_type) = map_js_node_kind(n.kind()) {
                // Skip error nodes unless they're the innermost
                if node_type != NodeType::ErrorNode || stack.is_empty() {
                    let refined_type = self.refine_node_type(&n, &node_type, source);
                    stack.push((n, refined_type));
                }
            }
            current = n.parent();
        }

        // Reverse to get root-to-leaf order
        stack.reverse();

        let components = stack
            .into_iter()
            .enumerate()
            .map(|(idx, (n, node_type))| {
                let name = self.extract_js_name(&n, source);
                BreadcrumbComponent {
                    node_type,
                    name,
                    start_line: n.start_position().row + 1,
                    end_line: n.end_position().row + 1,
                    start_byte: n.start_byte(),
                    end_byte: n.end_byte(),
                    depth: idx,
                    has_error: n.has_error(),
                }
            })
            .collect();

        Breadcrumb {
            components,
            line,
            column,
            byte_offset,
        }
    }

    /// Find the node at a specific byte offset
    fn find_node_at_offset<'a>(&self, tree: &'a Tree, offset: usize) -> Option<Node<'a>> {
        let root = tree.root_node();
        self.find_deepest_node_at(&root, offset)
    }

    /// Recursively find the deepest node containing the offset
    fn find_deepest_node_at<'a>(&self, node: &Node<'a>, offset: usize) -> Option<Node<'a>> {
        if offset < node.start_byte() || offset > node.end_byte() {
            return None;
        }

        let mut cursor = node.walk();
        for child in node.children(&mut cursor) {
            if let Some(deeper) = self.find_deepest_node_at(&child, offset) {
                return Some(deeper);
            }
        }

        Some(*node)
    }

    /// Find nearest named scope when inside an error node
    fn bubble_up_to_named_scope<'a>(&self, node: &Node<'a>) -> Option<Node<'a>> {
        let mut current = Some(*node);

        while let Some(n) = current {
            if let Some(node_type) = map_js_node_kind(n.kind()) {
                if node_type.is_named_scope() {
                    return Some(n);
                }
            }
            current = n.parent();
        }

        None
    }

    /// Convert byte offset to line/column
    fn byte_to_line_column(&self, source: &str, offset: usize) -> (usize, usize) {
        let mut line = 1;
        let mut column = 0;

        for (idx, ch) in source.char_indices() {
            if idx >= offset {
                break;
            }
            if ch == '\n' {
                line += 1;
                column = 0;
            } else {
                column += 1;
            }
        }

        (line, column)
    }

    /// Collect all error nodes from the tree
    fn collect_errors(&self, node: &Node, source: &str, errors: &mut Vec<ParseError>) {
        if node.is_error() || node.is_missing() {
            let pos = node.start_position();
            errors.push(ParseError {
                line: pos.row + 1,
                column: pos.column,
                message: if node.is_missing() {
                    format!("Missing: {}", node.kind())
                } else {
                    format!("Syntax error at: {}", node.kind())
                },
                error_type: if node.is_missing() {
                    "missing".to_string()
                } else {
                    "error".to_string()
                },
            });
        }

        let mut cursor = node.walk();
        for child in node.children(&mut cursor) {
            self.collect_errors(&child, source, errors);
        }
    }
}

impl BreadcrumbParser for JavaScriptParser {
    fn language(&self) -> Language {
        if self.is_typescript {
            Language::TypeScript
        } else {
            Language::JavaScript
        }
    }

    fn parse_outline(
        &mut self,
        source: &str,
        config: &ScanConfig,
    ) -> Result<Vec<OutlineNode>, ParserError> {
        let tree = self.parse_tree(source)?;
        let root = tree.root_node();
        let source_bytes = source.as_bytes();

        Ok(self.traverse_node(&root, source_bytes, source, 0, config))
    }

    fn get_breadcrumb_at(
        &mut self,
        source: &str,
        byte_offset: usize,
        _config: &ScanConfig,
    ) -> Result<Breadcrumb, ParserError> {
        let tree = self.parse_tree(source)?;
        let source_bytes = source.as_bytes();

        let node = self
            .find_node_at_offset(&tree, byte_offset)
            .ok_or_else(|| ParserError::ParseError("No node found at offset".to_string()))?;

        // If we're in an error node, bubble up to nearest named scope
        let effective_node = if node.has_error() || node.kind() == "ERROR" {
            self.bubble_up_to_named_scope(&node).unwrap_or(node)
        } else {
            node
        };

        let (line, column) = self.byte_to_line_column(source, byte_offset);

        Ok(self.build_breadcrumb_from_node(
            &effective_node,
            source_bytes,
            line,
            column,
            byte_offset,
        ))
    }

    fn extract_errors(&self, source: &str, tree: &Tree) -> Vec<ParseError> {
        let mut errors = Vec::new();
        self.collect_errors(&tree.root_node(), source, &mut errors);
        errors
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_simple_function() {
        let source = r#"
function hello() {
    console.log("Hello, World!");
}

class MyClass {
    constructor() {}

    myMethod() {
        return 42;
    }
}
"#;

        let mut parser = JavaScriptParser::new(false).unwrap();
        let config = ScanConfig::default();
        let nodes = parser.parse_outline(source, &config).unwrap();

        assert!(!nodes.is_empty());
        assert!(nodes.iter().any(|n| n.node_type == NodeType::Function));
        assert!(nodes.iter().any(|n| n.node_type == NodeType::Class));
    }

    #[test]
    fn test_parse_typescript() {
        let source = r#"
interface User {
    name: string;
    age: number;
}

type ID = string | number;

enum Status {
    Active,
    Inactive
}

class UserService {
    getUser(id: ID): User {
        return { name: "John", age: 30 };
    }
}
"#;

        let mut parser = JavaScriptParser::new(true).unwrap();
        let config = ScanConfig::default();
        let nodes = parser.parse_outline(source, &config).unwrap();

        assert!(!nodes.is_empty());
        assert!(nodes.iter().any(|n| n.node_type == NodeType::Interface));
        assert!(nodes.iter().any(|n| n.node_type == NodeType::TypeAlias));
        assert!(nodes.iter().any(|n| n.node_type == NodeType::Enum));
        assert!(nodes.iter().any(|n| n.node_type == NodeType::Class));
    }

    #[test]
    fn test_parse_arrow_functions() {
        let source = r#"
const greet = (name) => {
    console.log(`Hello, ${name}!`);
};

const add = (a, b) => a + b;
"#;

        let mut parser = JavaScriptParser::new(false).unwrap();
        let config = ScanConfig::default();
        let nodes = parser.parse_outline(source, &config).unwrap();

        assert!(!nodes.is_empty());
        // Arrow functions assigned to variables should be captured
        assert!(nodes
            .iter()
            .any(|n| n.node_type == NodeType::ArrowFunction));
    }

    #[test]
    fn test_parse_with_errors() {
        let source = r#"
function broken(
    // Missing closing paren
    console.log("test");
}

class ValidClass {
    method() {}
}
"#;

        let mut parser = JavaScriptParser::new(false).unwrap();
        let config = ScanConfig::default();
        // Should not panic on broken code
        let result = parser.parse_outline(source, &config);
        assert!(result.is_ok());
    }
}
