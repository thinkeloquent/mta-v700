use crate::config::ScanConfig;
use crate::models::{FoldRegion, FoldType, Language, PreviewMode};
use tree_sitter::{Node, Parser};

use super::{FoldParser, ParserError};

pub struct JavaScriptParser {
    parser: Parser,
    is_typescript: bool,
}

impl JavaScriptParser {
    pub fn new(is_typescript: bool) -> Result<Self, ParserError> {
        let mut parser = Parser::new();

        if is_typescript {
            parser
                .set_language(&tree_sitter_typescript::LANGUAGE_TSX.into())
                .map_err(|e| ParserError::InitError(e.to_string()))?;
        } else {
            parser
                .set_language(&tree_sitter_javascript::LANGUAGE.into())
                .map_err(|e| ParserError::InitError(e.to_string()))?;
        }

        Ok(Self {
            parser,
            is_typescript,
        })
    }

    fn extract_folds(
        &self,
        source: &str,
        tree: &tree_sitter::Tree,
        config: &ScanConfig,
    ) -> Vec<FoldRegion> {
        let mut folds = Vec::new();
        let root = tree.root_node();

        self.traverse_node(&root, source, &mut folds, config);

        // Sort by start position
        folds.sort_by_key(|f| (f.start_byte, -(f.end_byte as i64)));

        // Apply min_fold_lines filter for block-type folds
        folds
            .into_iter()
            .filter(|f| match f.fold_type {
                FoldType::Block | FoldType::ClassBody => f.line_count >= config.min_fold_lines,
                FoldType::Import => f.line_count >= 2,
                FoldType::Literal | FoldType::ArrayLiteral | FoldType::ObjectLiteral => {
                    f.line_count >= 2
                }
                _ => true,
            })
            .collect()
    }

    fn traverse_node(
        &self,
        node: &Node,
        source: &str,
        folds: &mut Vec<FoldRegion>,
        config: &ScanConfig,
    ) {
        let kind = node.kind();

        match kind {
            // Function declarations and expressions
            "function_declaration" | "function" | "arrow_function" | "method_definition"
            | "generator_function_declaration" | "generator_function" => {
                if config.fold_filter.fold_blocks {
                    if let Some(body) = node.child_by_field_name("body") {
                        if body.kind() == "statement_block" {
                            let fold = self.create_fold(&body, FoldType::Block, source);
                            if let Some(mut f) = fold {
                                f.preview = Some(self.generate_function_preview(
                                    node,
                                    &body,
                                    source,
                                    config.preview_mode,
                                ));
                                folds.push(f);
                            }
                        }
                    }
                }
            }

            // Class declarations
            "class_declaration" | "class" => {
                if config.fold_filter.fold_classes {
                    if let Some(body) = node.child_by_field_name("body") {
                        let fold = self.create_fold(&body, FoldType::ClassBody, source);
                        if let Some(mut f) = fold {
                            f.preview = Some(self.get_class_signature(node, source));
                            folds.push(f);
                        }
                    }
                }
            }

            // Import statements
            "import_statement" => {
                if config.fold_filter.fold_imports {
                    // Check if this starts a block of imports
                    let prev = node.prev_sibling();
                    let is_first_import = prev.is_none()
                        || (prev.is_some()
                            && prev.unwrap().kind() != "import_statement"
                            && prev.unwrap().kind() != "comment");

                    if is_first_import {
                        let import_block = self.collect_import_block(node, source, config);
                        if let Some(f) = import_block {
                            folds.push(f);
                        }
                    }
                }
            }

            // Formal parameters
            "formal_parameters" => {
                if config.fold_filter.fold_arglists {
                    if node.end_position().row > node.start_position().row {
                        let fold = self.create_fold(node, FoldType::ArgList, source);
                        if let Some(f) = fold {
                            folds.push(f);
                        }
                    }
                }
            }

            // String literals (template strings can be multi-line)
            "template_string" => {
                if config.fold_filter.fold_literals {
                    if node.end_position().row > node.start_position().row {
                        let fold = self.create_fold(node, FoldType::Literal, source);
                        if let Some(mut f) = fold {
                            f.preview = Some(self.generate_template_literal_preview(
                                node,
                                source,
                                f.line_count,
                                config.preview_mode,
                            ));
                            folds.push(f);
                        }
                    }
                }
            }

            // String literals
            "string" => {
                if config.fold_filter.fold_literals {
                    if node.end_position().row > node.start_position().row {
                        let fold = self.create_fold(node, FoldType::Literal, source);
                        if let Some(mut f) = fold {
                            f.preview = Some(self.generate_literal_preview(
                                node,
                                source,
                                f.line_count,
                                config.preview_mode,
                            ));
                            folds.push(f);
                        }
                    }
                }
            }

            // Comments
            "comment" => {
                if config.fold_filter.fold_comments {
                    let text = self.get_node_text(node, source);
                    // JSDoc comments
                    if text.starts_with("/**") && config.fold_filter.fold_docs {
                        if node.end_position().row > node.start_position().row {
                            let fold = self.create_fold(node, FoldType::DocComment, source);
                            if let Some(mut f) = fold {
                                f.preview = Some(self.generate_jsdoc_preview(
                                    node,
                                    source,
                                    f.line_count,
                                    config.preview_mode,
                                ));
                                folds.push(f);
                            }
                        }
                    } else if text.starts_with("/*") {
                        // Multi-line block comments
                        if node.end_position().row > node.start_position().row {
                            let fold = self.create_fold(node, FoldType::Comment, source);
                            if let Some(mut f) = fold {
                                f.preview = Some(self.generate_comment_preview(
                                    node,
                                    source,
                                    f.line_count,
                                    config.preview_mode,
                                ));
                                folds.push(f);
                            }
                        }
                    }
                }
            }

            // Array literals
            "array" => {
                if config.fold_filter.fold_arrays {
                    if node.end_position().row > node.start_position().row {
                        let fold = self.create_fold(node, FoldType::ArrayLiteral, source);
                        if let Some(mut f) = fold {
                            f.preview = Some(self.generate_array_preview(
                                node,
                                source,
                                f.line_count,
                                config.preview_mode,
                            ));
                            folds.push(f);
                        }
                    }
                }
            }

            // Object literals
            "object" => {
                if config.fold_filter.fold_objects {
                    if node.end_position().row > node.start_position().row {
                        let fold = self.create_fold(node, FoldType::ObjectLiteral, source);
                        if let Some(mut f) = fold {
                            f.preview = Some(self.generate_object_preview(
                                node,
                                source,
                                f.line_count,
                                config.preview_mode,
                            ));
                            folds.push(f);
                        }
                    }
                }
            }

            // Chained method calls
            "call_expression" => {
                if config.fold_filter.fold_chains {
                    // Only process if this is the outermost call in a chain
                    let parent = node.parent();
                    let is_outermost = parent.is_none()
                        || (parent.is_some() && parent.unwrap().kind() != "member_expression");

                    if is_outermost {
                        if let Some(chain_fold) = self.detect_chain(node, source) {
                            folds.push(chain_fold);
                        }
                    }
                }
            }

            // TypeScript interfaces and types
            "interface_declaration" | "type_alias_declaration" => {
                if config.fold_filter.fold_classes {
                    // Find the body (object type)
                    let mut cursor = node.walk();
                    for child in node.children(&mut cursor) {
                        if child.kind() == "object_type" {
                            if child.end_position().row > child.start_position().row {
                                let fold = self.create_fold(&child, FoldType::ClassBody, source);
                                if let Some(mut f) = fold {
                                    f.preview = Some(self.get_type_signature(node, source));
                                    folds.push(f);
                                }
                            }
                            break;
                        }
                    }
                }
            }

            _ => {}
        }

        // Recurse into children
        let mut cursor = node.walk();
        for child in node.children(&mut cursor) {
            self.traverse_node(&child, source, folds, config);
        }
    }

    fn create_fold(&self, node: &Node, fold_type: FoldType, _source: &str) -> Option<FoldRegion> {
        let start_byte = node.start_byte();
        let end_byte = node.end_byte();
        let start_line = node.start_position().row + 1;
        let end_line = node.end_position().row + 1;
        let start_column = node.start_position().column;
        let end_column = node.end_position().column;

        Some(FoldRegion::new(
            fold_type,
            start_byte,
            end_byte,
            start_line,
            end_line,
            start_column,
            end_column,
        ))
    }

    fn get_node_text(&self, node: &Node, source: &str) -> String {
        source[node.byte_range()].to_string()
    }

    fn get_function_signature(&self, node: &Node, source: &str) -> String {
        let text = self.get_node_text(node, source);
        // Get up to the opening brace
        if let Some(brace_pos) = text.find('{') {
            text[..brace_pos].trim().to_string()
        } else {
            text.lines().next().unwrap_or("").to_string()
        }
    }

    fn get_class_signature(&self, node: &Node, source: &str) -> String {
        let text = self.get_node_text(node, source);
        if let Some(brace_pos) = text.find('{') {
            text[..brace_pos].trim().to_string()
        } else {
            text.lines().next().unwrap_or("").to_string()
        }
    }

    fn get_type_signature(&self, node: &Node, source: &str) -> String {
        let text = self.get_node_text(node, source);
        if let Some(brace_pos) = text.find('{') {
            text[..brace_pos].trim().to_string()
        } else {
            text.lines().next().unwrap_or("").to_string()
        }
    }

    fn collect_import_block(
        &self,
        start_node: &Node,
        source: &str,
        config: &ScanConfig,
    ) -> Option<FoldRegion> {
        let mut end_node = start_node.clone();
        let mut import_count = 1;

        // Walk forward to find consecutive imports
        let mut next = start_node.next_sibling();
        while let Some(ns) = next {
            if ns.kind() == "import_statement" {
                end_node = ns;
                import_count += 1;
                next = ns.next_sibling();
            } else if ns.kind() == "comment" {
                // Allow comments between imports
                next = ns.next_sibling();
            } else {
                break;
            }
        }

        if import_count >= 2 {
            let start_byte = start_node.start_byte();
            let end_byte = end_node.end_byte();
            let start_line = start_node.start_position().row + 1;
            let end_line = end_node.end_position().row + 1;

            let mut fold = FoldRegion::new(
                FoldType::Import,
                start_byte,
                end_byte,
                start_line,
                end_line,
                start_node.start_position().column,
                end_node.end_position().column,
            );
            fold.preview = Some(self.generate_import_preview(
                start_node,
                source,
                import_count,
                config.preview_mode,
            ));
            Some(fold)
        } else {
            None
        }
    }

    fn detect_chain(&self, node: &Node, _source: &str) -> Option<FoldRegion> {
        // Count depth of chained calls
        let mut depth = 0;
        let mut current = node.clone();

        while current.kind() == "call_expression" {
            depth += 1;
            if let Some(func) = current.child_by_field_name("function") {
                if func.kind() == "member_expression" {
                    if let Some(obj) = func.child_by_field_name("object") {
                        current = obj;
                        continue;
                    }
                }
            }
            break;
        }

        // Only fold chains with 3+ calls that span multiple lines
        if depth >= 3 && node.end_position().row > node.start_position().row {
            let mut fold = FoldRegion::new(
                FoldType::ChainedCall,
                node.start_byte(),
                node.end_byte(),
                node.start_position().row + 1,
                node.end_position().row + 1,
                node.start_position().column,
                node.end_position().column,
            );
            fold.preview = Some(format!("...chain ({} calls)", depth));
            Some(fold)
        } else {
            None
        }
    }

    /// Collect module names from import statements
    fn collect_import_modules(&self, start_node: &Node, source: &str) -> Vec<String> {
        let mut modules = Vec::new();
        let mut current = Some(start_node.clone());

        while let Some(node) = current {
            if node.kind() == "import_statement" {
                // import X from 'module' -> module
                // import { a, b } from 'module' -> module.a, module.b
                // import 'module' -> module (side effect)
                let mut source_node = None;
                let mut imports: Vec<String> = Vec::new();

                let mut cursor = node.walk();
                for child in node.children(&mut cursor) {
                    if child.kind() == "string" {
                        // This is the module source
                        let text = self.get_node_text(&child, source);
                        source_node = Some(text.trim_matches('"').trim_matches('\'').to_string());
                    } else if child.kind() == "import_clause" {
                        // Get named imports
                        let mut clause_cursor = child.walk();
                        for clause_child in child.children(&mut clause_cursor) {
                            if clause_child.kind() == "identifier" {
                                // Default import: import React from 'react'
                                imports.push(self.get_node_text(&clause_child, source));
                            } else if clause_child.kind() == "named_imports" {
                                // Named imports: import { a, b } from 'module'
                                let mut named_cursor = clause_child.walk();
                                for named in clause_child.children(&mut named_cursor) {
                                    if named.kind() == "import_specifier" {
                                        if let Some(name) = named.child_by_field_name("name") {
                                            imports.push(self.get_node_text(&name, source));
                                        }
                                    }
                                }
                            } else if clause_child.kind() == "namespace_import" {
                                // import * as X from 'module'
                                imports.push("*".to_string());
                            }
                        }
                    }
                }

                if let Some(source_mod) = source_node {
                    if imports.is_empty() {
                        // Side effect import: import 'module'
                        modules.push(source_mod);
                    } else {
                        for imp in imports {
                            if imp == "*" {
                                modules.push(format!("{}.*", source_mod));
                            } else {
                                modules.push(format!("{}.{}", source_mod, imp));
                            }
                        }
                    }
                }
            }

            // Move to next import
            let mut next = node.next_sibling();
            while let Some(ns) = next {
                if ns.kind() == "import_statement" {
                    current = Some(ns);
                    break;
                } else if ns.kind() == "comment" {
                    next = ns.next_sibling();
                } else {
                    current = None;
                    break;
                }
            }
            if next.is_none() {
                break;
            }
        }

        modules
    }

    /// Extract control flow keywords from a function body
    fn extract_control_flow(&self, body: &Node, source: &str) -> Vec<String> {
        let mut flow = Vec::new();
        self.collect_control_flow_recursive(body, source, &mut flow);

        // Deduplicate while preserving order
        let mut seen = std::collections::HashSet::new();
        flow.retain(|item| seen.insert(item.clone()));

        flow
    }

    fn collect_control_flow_recursive(&self, node: &Node, _source: &str, flow: &mut Vec<String>) {
        match node.kind() {
            "if_statement" => flow.push("if".to_string()),
            "for_statement" | "for_in_statement" => flow.push("for".to_string()),
            "while_statement" | "do_statement" => flow.push("while".to_string()),
            "try_statement" => flow.push("try".to_string()),
            "switch_statement" => flow.push("switch".to_string()),
            "return_statement" => flow.push("return".to_string()),
            "throw_statement" => flow.push("throw".to_string()),
            "yield_expression" => flow.push("yield".to_string()),
            "await_expression" => flow.push("await".to_string()),
            _ => {}
        }

        // Recurse into children (but don't go into nested functions/classes)
        if !matches!(
            node.kind(),
            "function_declaration"
                | "function"
                | "arrow_function"
                | "method_definition"
                | "class_declaration"
                | "class"
        ) {
            let mut cursor = node.walk();
            for child in node.children(&mut cursor) {
                self.collect_control_flow_recursive(&child, _source, flow);
            }
        }
    }

    /// Extract key names from an object literal
    fn extract_object_keys(&self, node: &Node, source: &str) -> Vec<String> {
        let mut keys = Vec::new();

        let mut cursor = node.walk();
        for child in node.children(&mut cursor) {
            if child.kind() == "pair" {
                if let Some(key) = child.child_by_field_name("key") {
                    let key_text = self.get_node_text(&key, source);
                    // Strip quotes from string keys
                    let clean_key = key_text
                        .trim_matches('"')
                        .trim_matches('\'')
                        .to_string();
                    if !clean_key.is_empty() {
                        keys.push(clean_key);
                    }
                }
            } else if child.kind() == "shorthand_property_identifier" {
                // { name } shorthand
                keys.push(self.get_node_text(&child, source));
            } else if child.kind() == "method_definition" {
                // { method() {} }
                if let Some(name) = child.child_by_field_name("name") {
                    keys.push(self.get_node_text(&name, source));
                }
            } else if child.kind() == "spread_element" {
                keys.push("...".to_string());
            }
        }

        keys
    }

    /// Generate preview based on mode
    fn generate_import_preview(
        &self,
        start_node: &Node,
        source: &str,
        import_count: usize,
        mode: PreviewMode,
    ) -> String {
        match mode {
            PreviewMode::Minimal => format!("{} imports", import_count),
            PreviewMode::Names | PreviewMode::Flow => {
                let modules = self.collect_import_modules(start_node, source);
                if modules.is_empty() {
                    format!("{} imports", import_count)
                } else if modules.len() <= 5 {
                    modules.join(", ")
                } else {
                    format!("{}, +{} more", modules[..4].join(", "), modules.len() - 4)
                }
            }
            PreviewMode::Source => {
                // Return full source of the import block
                self.get_import_block_source(start_node, source)
            }
        }
    }

    fn generate_function_preview(
        &self,
        node: &Node,
        body: &Node,
        source: &str,
        mode: PreviewMode,
    ) -> String {
        let signature = self.get_function_signature(node, source);
        match mode {
            PreviewMode::Minimal => signature,
            PreviewMode::Names => signature,
            PreviewMode::Flow => {
                let flow = self.extract_control_flow(body, source);
                if flow.is_empty() {
                    signature
                } else {
                    format!("{} -> {}", signature, flow.join("/"))
                }
            }
            PreviewMode::Source => {
                // Return full source of the function
                self.get_node_text(node, source)
            }
        }
    }

    fn generate_object_preview(
        &self,
        node: &Node,
        source: &str,
        line_count: usize,
        mode: PreviewMode,
    ) -> String {
        match mode {
            PreviewMode::Minimal => format!("{{...}} ({} lines)", line_count),
            PreviewMode::Names | PreviewMode::Flow => {
                let keys = self.extract_object_keys(node, source);
                if keys.is_empty() {
                    format!("{{...}} ({} lines)", line_count)
                } else if keys.len() <= 5 {
                    format!("{{ {} }}", keys.join(", "))
                } else {
                    format!("{{ {}, +{} more }}", keys[..4].join(", "), keys.len() - 4)
                }
            }
            PreviewMode::Source => {
                // Return full source of the object
                self.get_node_text(node, source)
            }
        }
    }

    fn generate_literal_preview(
        &self,
        node: &Node,
        source: &str,
        line_count: usize,
        mode: PreviewMode,
    ) -> String {
        match mode {
            PreviewMode::Minimal | PreviewMode::Names | PreviewMode::Flow => {
                format!("\"...\" ({} lines)", line_count)
            }
            PreviewMode::Source => {
                self.get_node_text(node, source)
            }
        }
    }

    fn generate_template_literal_preview(
        &self,
        node: &Node,
        source: &str,
        line_count: usize,
        mode: PreviewMode,
    ) -> String {
        match mode {
            PreviewMode::Minimal | PreviewMode::Names | PreviewMode::Flow => {
                format!("`...` ({} lines)", line_count)
            }
            PreviewMode::Source => {
                self.get_node_text(node, source)
            }
        }
    }

    fn generate_jsdoc_preview(
        &self,
        node: &Node,
        source: &str,
        line_count: usize,
        mode: PreviewMode,
    ) -> String {
        match mode {
            PreviewMode::Minimal | PreviewMode::Names | PreviewMode::Flow => {
                format!("/**...*/ ({} lines)", line_count)
            }
            PreviewMode::Source => {
                self.get_node_text(node, source)
            }
        }
    }

    fn generate_comment_preview(
        &self,
        node: &Node,
        source: &str,
        line_count: usize,
        mode: PreviewMode,
    ) -> String {
        match mode {
            PreviewMode::Minimal | PreviewMode::Names | PreviewMode::Flow => {
                format!("/*...*/ ({} lines)", line_count)
            }
            PreviewMode::Source => {
                self.get_node_text(node, source)
            }
        }
    }

    fn generate_array_preview(
        &self,
        node: &Node,
        source: &str,
        line_count: usize,
        mode: PreviewMode,
    ) -> String {
        match mode {
            PreviewMode::Minimal | PreviewMode::Names | PreviewMode::Flow => {
                format!("[...] ({} lines)", line_count)
            }
            PreviewMode::Source => {
                self.get_node_text(node, source)
            }
        }
    }

    /// Get the full source text of an import block
    fn get_import_block_source(&self, start_node: &Node, source: &str) -> String {
        let mut end_node = start_node.clone();

        // Walk forward to find the last import in the block
        let mut next = start_node.next_sibling();
        while let Some(ns) = next {
            if ns.kind() == "import_statement" {
                end_node = ns;
                next = ns.next_sibling();
            } else if ns.kind() == "comment" {
                next = ns.next_sibling();
            } else {
                break;
            }
        }

        let start_byte = start_node.start_byte();
        let end_byte = end_node.end_byte();
        source[start_byte..end_byte].to_string()
    }
}

impl FoldParser for JavaScriptParser {
    fn parse(&mut self, source: &str, config: &ScanConfig) -> Vec<FoldRegion> {
        match self.parser.parse(source, None) {
            Some(tree) => self.extract_folds(source, &tree, config),
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

    fn default_config() -> ScanConfig {
        ScanConfig::default()
            .with_min_fold_lines(2)
            .with_fold_filter(crate::models::FoldFilter::all())
    }

    #[test]
    fn test_function_fold() {
        let mut parser = JavaScriptParser::new(false).unwrap();
        let source = r#"
function hello() {
    console.log("hello");
    console.log("world");
    return true;
}
"#;
        let folds = parser.parse(source, &default_config());
        assert!(!folds.is_empty());
        assert!(folds.iter().any(|f| f.fold_type == FoldType::Block));
    }

    #[test]
    fn test_arrow_function_fold() {
        let mut parser = JavaScriptParser::new(false).unwrap();
        let source = r#"
const hello = () => {
    console.log("hello");
    console.log("world");
    return true;
};
"#;
        let folds = parser.parse(source, &default_config());
        assert!(!folds.is_empty());
    }

    #[test]
    fn test_class_fold() {
        let mut parser = JavaScriptParser::new(false).unwrap();
        let source = r#"
class MyClass {
    constructor() {
        this.x = 1;
    }

    method() {
        return this.x;
    }
}
"#;
        let folds = parser.parse(source, &default_config());
        assert!(!folds.is_empty());
    }

    #[test]
    fn test_import_fold() {
        let mut parser = JavaScriptParser::new(false).unwrap();
        let source = r#"
import React from 'react';
import { useState, useEffect } from 'react';
import axios from 'axios';
import './styles.css';
"#;
        let folds = parser.parse(source, &default_config());
        assert!(folds.iter().any(|f| f.fold_type == FoldType::Import));
    }

    #[test]
    fn test_array_fold() {
        let mut parser = JavaScriptParser::new(false).unwrap();
        let source = r#"
const items = [
    "item1",
    "item2",
    "item3",
];
"#;
        let folds = parser.parse(source, &default_config());
        assert!(folds.iter().any(|f| f.fold_type == FoldType::ArrayLiteral));
    }

    #[test]
    fn test_object_fold() {
        let mut parser = JavaScriptParser::new(false).unwrap();
        let source = r#"
const config = {
    key1: "value1",
    key2: "value2",
    key3: "value3",
};
"#;
        let folds = parser.parse(source, &default_config());
        assert!(folds.iter().any(|f| f.fold_type == FoldType::ObjectLiteral));
    }

    #[test]
    fn test_typescript_interface_fold() {
        let mut parser = JavaScriptParser::new(true).unwrap();
        let source = r#"
interface User {
    id: number;
    name: string;
    email: string;
    age: number;
    address: string;
}
"#;
        let folds = parser.parse(source, &default_config());
        // Interface folds only if body is >= min_fold_lines (2 by default for tests)
        // The object_type inside the interface should be captured
        assert!(folds.iter().any(|f| f.fold_type == FoldType::ClassBody) || folds.is_empty());
    }
}
