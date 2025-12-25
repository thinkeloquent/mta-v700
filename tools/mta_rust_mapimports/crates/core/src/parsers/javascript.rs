use crate::models::{ImportStatement, ImportType, Language};
use tree_sitter::{Node, Parser};

use super::{ImportParser, ParserError};

pub struct JavaScriptParser {
    parser: Parser,
    is_typescript: bool,
}

impl JavaScriptParser {
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

    fn extract_imports(&self, source: &str, tree: &tree_sitter::Tree) -> Vec<ImportStatement> {
        let mut imports = Vec::new();
        let root = tree.root_node();

        self.traverse_node(&root, source, &mut imports);

        imports
    }

    fn traverse_node(&self, node: &Node, source: &str, imports: &mut Vec<ImportStatement>) {
        match node.kind() {
            "import_statement" => {
                self.parse_import_statement(node, source, imports);
            }
            "call_expression" => {
                self.parse_call_expression(node, source, imports);
            }
            "export_statement" => {
                // Handle `export { x } from 'module'`
                self.parse_export_statement(node, source, imports);
            }
            _ => {
                let mut cursor = node.walk();
                for child in node.children(&mut cursor) {
                    self.traverse_node(&child, source, imports);
                }
            }
        }
    }

    /// Parse ESM import statements
    fn parse_import_statement(
        &self,
        node: &Node,
        source: &str,
        imports: &mut Vec<ImportStatement>,
    ) {
        let mut module = String::new();
        let mut items = Vec::new();
        let mut is_default = false;
        let mut alias: Option<String> = None;

        let mut cursor = node.walk();
        for child in node.children(&mut cursor) {
            match child.kind() {
                "string" | "string_fragment" => {
                    module = self.extract_string_value(&child, source);
                }
                "import_clause" => {
                    self.parse_import_clause(&child, source, &mut items, &mut is_default, &mut alias);
                }
                _ => {}
            }
        }

        if !module.is_empty() {
            imports.push(ImportStatement {
                module,
                items,
                is_default,
                line: node.start_position().row + 1,
                column: node.start_position().column,
                raw: self.get_node_text(node, source),
                import_type: ImportType::Unknown,
                alias,
            });
        }
    }

    fn parse_import_clause(
        &self,
        node: &Node,
        source: &str,
        items: &mut Vec<String>,
        is_default: &mut bool,
        alias: &mut Option<String>,
    ) {
        let mut cursor = node.walk();
        for child in node.children(&mut cursor) {
            match child.kind() {
                "identifier" => {
                    // Default import
                    *is_default = true;
                    items.push(self.get_node_text(&child, source));
                }
                "namespace_import" => {
                    // import * as name
                    self.parse_namespace_import(&child, source, items, alias);
                }
                "named_imports" => {
                    self.parse_named_imports(&child, source, items);
                }
                _ => {}
            }
        }
    }

    fn parse_namespace_import(
        &self,
        node: &Node,
        source: &str,
        items: &mut Vec<String>,
        alias: &mut Option<String>,
    ) {
        items.push("*".to_string());
        let mut cursor = node.walk();
        for child in node.children(&mut cursor) {
            if child.kind() == "identifier" {
                *alias = Some(self.get_node_text(&child, source));
            }
        }
    }

    fn parse_named_imports(&self, node: &Node, source: &str, items: &mut Vec<String>) {
        let mut cursor = node.walk();
        for child in node.children(&mut cursor) {
            if child.kind() == "import_specifier" {
                self.parse_import_specifier(&child, source, items);
            }
        }
    }

    fn parse_import_specifier(&self, node: &Node, source: &str, items: &mut Vec<String>) {
        let mut cursor = node.walk();
        for child in node.children(&mut cursor) {
            if child.kind() == "identifier" {
                items.push(self.get_node_text(&child, source));
                break; // Take only the first identifier (original name)
            }
        }
    }

    /// Parse require() calls and dynamic import()
    fn parse_call_expression(
        &self,
        node: &Node,
        source: &str,
        imports: &mut Vec<ImportStatement>,
    ) {
        let mut cursor = node.walk();
        let mut is_require = false;
        let mut is_import = false;
        let mut module = String::new();

        for child in node.children(&mut cursor) {
            match child.kind() {
                "identifier" => {
                    let name = self.get_node_text(&child, source);
                    if name == "require" {
                        is_require = true;
                    }
                }
                "import" => {
                    is_import = true;
                }
                "arguments" => {
                    if is_require || is_import {
                        module = self.extract_first_string_arg(&child, source);
                    }
                }
                _ => {}
            }
        }

        if (is_require || is_import) && !module.is_empty() {
            imports.push(ImportStatement {
                module,
                items: vec![],
                is_default: true,
                line: node.start_position().row + 1,
                column: node.start_position().column,
                raw: self.get_node_text(node, source),
                import_type: ImportType::Unknown,
                alias: None,
            });
        }
    }

    /// Parse export ... from 'module' statements
    fn parse_export_statement(
        &self,
        node: &Node,
        source: &str,
        imports: &mut Vec<ImportStatement>,
    ) {
        let raw = self.get_node_text(node, source);

        // Only process if it's an export from another module
        if !raw.contains(" from ") {
            return;
        }

        let mut module = String::new();
        let mut items = Vec::new();

        let mut cursor = node.walk();
        for child in node.children(&mut cursor) {
            match child.kind() {
                "string" | "string_fragment" => {
                    module = self.extract_string_value(&child, source);
                }
                "export_clause" => {
                    self.parse_export_clause(&child, source, &mut items);
                }
                _ => {}
            }
        }

        if !module.is_empty() {
            imports.push(ImportStatement {
                module,
                items,
                is_default: false,
                line: node.start_position().row + 1,
                column: node.start_position().column,
                raw,
                import_type: ImportType::Unknown,
                alias: None,
            });
        }
    }

    fn parse_export_clause(&self, node: &Node, source: &str, items: &mut Vec<String>) {
        let mut cursor = node.walk();
        for child in node.children(&mut cursor) {
            if child.kind() == "export_specifier" {
                let mut inner_cursor = child.walk();
                for inner_child in child.children(&mut inner_cursor) {
                    if inner_child.kind() == "identifier" {
                        items.push(self.get_node_text(&inner_child, source));
                        break;
                    }
                }
            }
        }
    }

    fn extract_string_value(&self, node: &Node, source: &str) -> String {
        let text = self.get_node_text(node, source);
        // Remove quotes
        text.trim_matches(|c| c == '"' || c == '\'' || c == '`')
            .to_string()
    }

    fn extract_first_string_arg(&self, node: &Node, source: &str) -> String {
        let mut cursor = node.walk();
        for child in node.children(&mut cursor) {
            if child.kind() == "string" {
                return self.extract_string_value(&child, source);
            }
        }
        String::new()
    }

    fn get_node_text(&self, node: &Node, source: &str) -> String {
        source[node.byte_range()].to_string()
    }
}

impl ImportParser for JavaScriptParser {
    fn parse(&mut self, source: &str) -> Vec<ImportStatement> {
        match self.parser.parse(source, None) {
            Some(tree) => self.extract_imports(source, &tree),
            None => vec![],
        }
    }

    fn language(&self) -> Language {
        if self.is_typescript {
            Language::TypeScript
        } else {
            Language::JavaScript
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_esm_import() {
        let mut parser = JavaScriptParser::new(false).unwrap();
        let imports = parser.parse("import express from 'express';");

        assert_eq!(imports.len(), 1);
        assert_eq!(imports[0].module, "express");
        assert!(imports[0].is_default);
    }

    #[test]
    fn test_named_imports() {
        let mut parser = JavaScriptParser::new(false).unwrap();
        let imports = parser.parse("import { useState, useEffect } from 'react';");

        assert_eq!(imports.len(), 1);
        assert_eq!(imports[0].module, "react");
        assert!(imports[0].items.contains(&"useState".to_string()));
        assert!(imports[0].items.contains(&"useEffect".to_string()));
    }

    #[test]
    fn test_namespace_import() {
        let mut parser = JavaScriptParser::new(false).unwrap();
        let imports = parser.parse("import * as path from 'path';");

        assert_eq!(imports.len(), 1);
        assert_eq!(imports[0].module, "path");
        assert!(imports[0].items.contains(&"*".to_string()));
        assert_eq!(imports[0].alias, Some("path".to_string()));
    }

    #[test]
    fn test_require() {
        let mut parser = JavaScriptParser::new(false).unwrap();
        let imports = parser.parse("const fs = require('fs');");

        assert_eq!(imports.len(), 1);
        assert_eq!(imports[0].module, "fs");
    }

    #[test]
    fn test_relative_import() {
        let mut parser = JavaScriptParser::new(false).unwrap();
        let imports = parser.parse("import { helper } from './utils/helper';");

        assert_eq!(imports.len(), 1);
        assert_eq!(imports[0].module, "./utils/helper");
    }

    #[test]
    fn test_typescript_import() {
        let mut parser = JavaScriptParser::new(true).unwrap();
        let imports = parser.parse("import type { User } from './types';");

        assert_eq!(imports.len(), 1);
        assert_eq!(imports[0].module, "./types");
    }
}
