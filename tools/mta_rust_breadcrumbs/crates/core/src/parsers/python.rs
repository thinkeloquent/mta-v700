//! Python parser for structural code analysis
//!
//! This module implements resilient parsing of Python source code using Tree-sitter,
//! with robust error recovery to handle incomplete or malformed code.

use crate::config::ScanConfig;
use crate::models::{Breadcrumb, BreadcrumbComponent, Language, NodeType, OutlineNode, ParseError};
use crate::parsers::{extract_node_name, extract_preview, map_python_node_kind, BreadcrumbParser, ParserError};
use tree_sitter::{Node, Parser, Tree};

/// Python parser implementation
pub struct PythonParser {
    parser: Parser,
}

impl PythonParser {
    /// Create a new Python parser
    pub fn new() -> Result<Self, ParserError> {
        let mut parser = Parser::new();
        parser
            .set_language(&tree_sitter_python::LANGUAGE.into())
            .map_err(|e| ParserError::InitError(e.to_string()))?;
        Ok(Self { parser })
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
        if let Some(node_type) = map_python_node_kind(node.kind()) {
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
                    | NodeType::ElifClause
                    | NodeType::ElseClause
                    | NodeType::ForLoop
                    | NodeType::WhileLoop
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

            // Handle decorated definitions specially
            let actual_node = if node.kind() == "decorated_definition" {
                // Get the actual definition (function or class) inside
                node.child_by_field_name("definition").unwrap_or(*node)
            } else {
                *node
            };

            let name = self.extract_python_name(&actual_node, source);
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
            // Not a tracked node type, but traverse children
            let mut cursor = node.walk();
            for child in node.children(&mut cursor) {
                results.extend(self.traverse_node(&child, source, source_str, depth, config));
            }
        }

        results
    }

    /// Extract name for Python-specific nodes
    fn extract_python_name(&self, node: &Node, source: &[u8]) -> Option<String> {
        match node.kind() {
            "class_definition" | "function_definition" | "async_function_definition" => {
                node.child_by_field_name("name")
                    .and_then(|n| n.utf8_text(source).ok())
                    .map(|s| s.to_string())
            }
            "decorated_definition" => {
                // Get the inner definition
                node.child_by_field_name("definition")
                    .and_then(|def| self.extract_python_name(&def, source))
            }
            _ => extract_node_name(node, source),
        }
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
        let mut components = Vec::new();
        let mut current = Some(*node);

        // Build stack of nodes from leaf to root
        let mut stack = Vec::new();
        while let Some(n) = current {
            if let Some(node_type) = map_python_node_kind(n.kind()) {
                // Skip error nodes unless they're the innermost
                if node_type != NodeType::ErrorNode || stack.is_empty() {
                    stack.push((n, node_type));
                }
            }
            current = n.parent();
        }

        // Reverse to get root-to-leaf order
        stack.reverse();

        for (idx, (n, node_type)) in stack.into_iter().enumerate() {
            let name = self.extract_python_name(&n, source);
            components.push(BreadcrumbComponent {
                node_type,
                name,
                start_line: n.start_position().row + 1,
                end_line: n.end_position().row + 1,
                start_byte: n.start_byte(),
                end_byte: n.end_byte(),
                depth: idx,
                has_error: n.has_error(),
            });
        }

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

        // Check children first for a more specific match
        let mut cursor = node.walk();
        for child in node.children(&mut cursor) {
            if let Some(deeper) = self.find_deepest_node_at(&child, offset) {
                return Some(deeper);
            }
        }

        // If no child contains the offset, this node is the deepest
        Some(*node)
    }

    /// Find nearest named scope when inside an error node
    fn bubble_up_to_named_scope<'a>(&self, node: &Node<'a>, _source: &[u8]) -> Option<Node<'a>> {
        let mut current = Some(*node);

        while let Some(n) = current {
            if let Some(node_type) = map_python_node_kind(n.kind()) {
                if node_type.is_named_scope() {
                    return Some(n);
                }
            }
            current = n.parent();
        }

        None
    }
}

impl BreadcrumbParser for PythonParser {
    fn language(&self) -> Language {
        Language::Python
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

        // Find node at offset
        let node = self
            .find_node_at_offset(&tree, byte_offset)
            .ok_or_else(|| ParserError::ParseError("No node found at offset".to_string()))?;

        // If we're in an error node, bubble up to nearest named scope
        let effective_node = if node.has_error() || node.kind() == "ERROR" {
            self.bubble_up_to_named_scope(&node, source_bytes)
                .unwrap_or(node)
        } else {
            node
        };

        // Calculate line/column from offset
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

impl PythonParser {
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_simple_function() {
        let source = r#"
def hello():
    print("Hello, World!")

class MyClass:
    def method(self):
        pass
"#;

        let mut parser = PythonParser::new().unwrap();
        let config = ScanConfig::default();
        let nodes = parser.parse_outline(source, &config).unwrap();

        assert!(!nodes.is_empty());
        // Should have function and class at top level
        assert!(nodes.iter().any(|n| n.node_type == NodeType::Function));
        assert!(nodes.iter().any(|n| n.node_type == NodeType::Class));
    }

    #[test]
    fn test_parse_with_errors() {
        let source = r#"
def broken_func(
    # Missing closing paren and colon
    print("test")

class ValidClass:
    def method(self):
        pass
"#;

        let mut parser = PythonParser::new().unwrap();
        let config = ScanConfig::default();
        // Should not panic on broken code
        let result = parser.parse_outline(source, &config);
        assert!(result.is_ok());
    }

    #[test]
    fn test_breadcrumb_at_position() {
        let source = r#"
class MyClass:
    def my_method(self):
        x = 1
"#;

        let mut parser = PythonParser::new().unwrap();
        let config = ScanConfig::default();

        // Position inside the method body (line 4)
        let breadcrumb = parser.get_breadcrumb_at(source, 50, &config).unwrap();

        assert!(!breadcrumb.components.is_empty());
        // Should include class and method
        let path = breadcrumb.path();
        assert!(path.contains("MyClass") || path.contains("my_method"));
    }
}
