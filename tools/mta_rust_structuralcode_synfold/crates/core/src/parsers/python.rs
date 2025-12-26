use crate::config::ScanConfig;
use crate::models::{FoldRegion, FoldType, Language, PreviewMode};
use tree_sitter::{Node, Parser};

use super::{FoldParser, ParserError};

pub struct PythonParser {
    parser: Parser,
}

impl PythonParser {
    pub fn new() -> Result<Self, ParserError> {
        let mut parser = Parser::new();
        parser
            .set_language(&tree_sitter_python::LANGUAGE.into())
            .map_err(|e| ParserError::InitError(e.to_string()))?;

        Ok(Self { parser })
    }

    /// Extract fold regions from the parse tree
    fn extract_folds(
        &self,
        source: &str,
        tree: &tree_sitter::Tree,
        config: &ScanConfig,
    ) -> Vec<FoldRegion> {
        let mut folds = Vec::new();
        let root = tree.root_node();

        self.traverse_node(&root, source, &mut folds, config);

        // Sort by start position and filter by min_fold_lines
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
            // Function definitions
            "function_definition" | "async_function_definition" => {
                if config.fold_filter.fold_blocks {
                    if let Some(body) = node.child_by_field_name("body") {
                        let fold = self.create_fold(&body, FoldType::Block, source);
                        if let Some(mut f) = fold {
                            // Set preview based on mode
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

            // Class definitions
            "class_definition" => {
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

            // Import statements (consecutive imports)
            "import_statement" | "import_from_statement" => {
                if config.fold_filter.fold_imports {
                    // Check if this is part of a consecutive import block
                    let parent = node.parent();
                    if let Some(_p) = parent {
                        // Only process if this is the first import in a sequence
                        let mut prev = node.prev_sibling();
                        while let Some(ps) = prev {
                            if ps.kind() == "import_statement"
                                || ps.kind() == "import_from_statement"
                            {
                                // There's a previous import, so skip
                                break;
                            }
                            if ps.kind() != "comment" && !ps.kind().is_empty() {
                                // Found non-import, non-comment - this is the first
                                let import_block =
                                    self.collect_import_block(node, source, config);
                                if let Some(f) = import_block {
                                    folds.push(f);
                                }
                                break;
                            }
                            prev = ps.prev_sibling();
                        }
                        // If no previous sibling, this is the first
                        if prev.is_none() {
                            let import_block = self.collect_import_block(node, source, config);
                            if let Some(f) = import_block {
                                folds.push(f);
                            }
                        }
                    }
                }
            }

            // Arguments/parameters
            "parameters" => {
                if config.fold_filter.fold_arglists {
                    if node.end_position().row > node.start_position().row {
                        let fold = self.create_fold(node, FoldType::ArgList, source);
                        if let Some(f) = fold {
                            folds.push(f);
                        }
                    }
                }
            }

            // String literals (multi-line)
            "string" | "concatenated_string" => {
                if config.fold_filter.fold_literals {
                    if node.end_position().row > node.start_position().row {
                        let fold = self.create_fold(node, FoldType::Literal, source);
                        if let Some(mut f) = fold {
                            f.preview = Some(format!("\"...\" ({} lines)", f.line_count));
                            folds.push(f);
                        }
                    }
                }
            }

            // Comments (including docstrings)
            "comment" => {
                if config.fold_filter.fold_comments {
                    // Multi-line comments or consecutive single-line comments
                    if node.end_position().row > node.start_position().row {
                        let fold = self.create_fold(node, FoldType::Comment, source);
                        if let Some(f) = fold {
                            folds.push(f);
                        }
                    }
                }
            }

            // Expression statements containing docstrings
            "expression_statement" => {
                if config.fold_filter.fold_docs {
                    if let Some(child) = node.child(0) {
                        if child.kind() == "string" {
                            let text = self.get_node_text(&child, source);
                            if (text.starts_with("\"\"\"") || text.starts_with("'''"))
                                && child.end_position().row > child.start_position().row
                            {
                                let fold = self.create_fold(&child, FoldType::DocComment, source);
                                if let Some(mut f) = fold {
                                    f.preview =
                                        Some(format!("\"\"\"...\"\"\" ({} lines)", f.line_count));
                                    folds.push(f);
                                }
                            }
                        }
                    }
                }
            }

            // List/tuple literals
            "list" | "tuple" => {
                if config.fold_filter.fold_arrays {
                    if node.end_position().row > node.start_position().row {
                        let fold = self.create_fold(node, FoldType::ArrayLiteral, source);
                        if let Some(mut f) = fold {
                            f.preview = Some(format!("[...] ({} lines)", f.line_count));
                            folds.push(f);
                        }
                    }
                }
            }

            // Dictionary literals
            "dictionary" | "set" => {
                if config.fold_filter.fold_objects {
                    if node.end_position().row > node.start_position().row {
                        let fold = self.create_fold(node, FoldType::ObjectLiteral, source);
                        if let Some(mut f) = fold {
                            f.preview = Some(self.generate_dict_preview(
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
            "call" => {
                if config.fold_filter.fold_chains {
                    if let Some(chain_fold) = self.detect_chain(node, source) {
                        folds.push(chain_fold);
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
        // Get text from start of function to first ':'
        let start = node.start_byte();
        let text = &source[start..];
        if let Some(colon_pos) = text.find(':') {
            text[..colon_pos].trim().to_string()
        } else {
            self.get_node_text(node, source)
                .lines()
                .next()
                .unwrap_or("")
                .to_string()
        }
    }

    fn get_class_signature(&self, node: &Node, source: &str) -> String {
        // Get text from start of class to first ':'
        let start = node.start_byte();
        let text = &source[start..];
        if let Some(colon_pos) = text.find(':') {
            text[..colon_pos].trim().to_string()
        } else {
            self.get_node_text(node, source)
                .lines()
                .next()
                .unwrap_or("")
                .to_string()
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
            if ns.kind() == "import_statement" || ns.kind() == "import_from_statement" {
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

        while current.kind() == "call" {
            depth += 1;
            if let Some(func) = current.child_by_field_name("function") {
                if func.kind() == "attribute" {
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
                // "import os" or "import os, sys"
                let mut cursor = node.walk();
                for child in node.children(&mut cursor) {
                    if child.kind() == "dotted_name" {
                        modules.push(self.get_node_text(&child, source));
                    } else if child.kind() == "aliased_import" {
                        // import numpy as np -> "numpy"
                        if let Some(name) = child.child_by_field_name("name") {
                            modules.push(self.get_node_text(&name, source));
                        }
                    }
                }
            } else if node.kind() == "import_from_statement" {
                // "from typing import List" or "from os.path import join"
                let module = node.child_by_field_name("module_name");
                let mut module_prefix = module
                    .map(|m| self.get_node_text(&m, source))
                    .unwrap_or_default();

                // Handle relative imports: count leading dots
                let mut cursor = node.walk();
                let mut dot_count = 0;
                for child in node.children(&mut cursor) {
                    if child.kind() == "." {
                        dot_count += 1;
                    } else if child.kind() != "import" && child.kind() != "from" {
                        break;
                    }
                }
                if dot_count > 0 {
                    let dots: String = ".".repeat(dot_count);
                    if module_prefix.is_empty() {
                        module_prefix = dots;
                    } else {
                        module_prefix = format!("{}{}", dots, module_prefix);
                    }
                }

                // Get imported names
                let mut cursor = node.walk();
                for child in node.children(&mut cursor) {
                    if child.kind() == "dotted_name" && Some(&child) != module.as_ref() {
                        let name = self.get_node_text(&child, source);
                        if module_prefix.is_empty() {
                            modules.push(name);
                        } else {
                            modules.push(format!("{}.{}", module_prefix, name));
                        }
                    } else if child.kind() == "aliased_import" {
                        if let Some(name) = child.child_by_field_name("name") {
                            let name_text = self.get_node_text(&name, source);
                            if module_prefix.is_empty() {
                                modules.push(name_text);
                            } else {
                                modules.push(format!("{}.{}", module_prefix, name_text));
                            }
                        }
                    }
                }

                // If no specific names imported (import *), just use module name
                if modules.is_empty() || modules.last().map(|m| !m.contains(&module_prefix)).unwrap_or(true) {
                    if !module_prefix.is_empty() {
                        let has_this_module = modules.iter().any(|m| m.starts_with(&module_prefix));
                        if !has_this_module {
                            modules.push(module_prefix);
                        }
                    }
                }
            }

            // Move to next import
            let mut next = node.next_sibling();
            while let Some(ns) = next {
                if ns.kind() == "import_statement" || ns.kind() == "import_from_statement" {
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
            "for_statement" => flow.push("for".to_string()),
            "while_statement" => flow.push("while".to_string()),
            "try_statement" => flow.push("try".to_string()),
            "with_statement" => flow.push("with".to_string()),
            "match_statement" => flow.push("match".to_string()),
            "return_statement" => flow.push("return".to_string()),
            "yield" => flow.push("yield".to_string()),
            "raise_statement" => flow.push("raise".to_string()),
            "assert_statement" => flow.push("assert".to_string()),
            "await" => flow.push("await".to_string()),
            _ => {}
        }

        // Recurse into children (but don't go into nested functions/classes)
        if node.kind() != "function_definition"
            && node.kind() != "async_function_definition"
            && node.kind() != "class_definition"
        {
            let mut cursor = node.walk();
            for child in node.children(&mut cursor) {
                self.collect_control_flow_recursive(&child, _source, flow);
            }
        }
    }

    /// Extract key names from a dictionary literal
    fn extract_dict_keys(&self, node: &Node, source: &str) -> Vec<String> {
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
                let text = self.get_node_text(start_node, source);
                let first_line = text.lines().next().unwrap_or("");
                if first_line.len() > 60 {
                    format!("{}...", &first_line[..57])
                } else {
                    first_line.to_string()
                }
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
                let text = self.get_node_text(node, source);
                let lines: Vec<&str> = text.lines().take(2).collect();
                lines.join(" ").chars().take(80).collect()
            }
        }
    }

    fn generate_dict_preview(
        &self,
        node: &Node,
        source: &str,
        line_count: usize,
        mode: PreviewMode,
    ) -> String {
        match mode {
            PreviewMode::Minimal => format!("{{...}} ({} lines)", line_count),
            PreviewMode::Names | PreviewMode::Flow => {
                let keys = self.extract_dict_keys(node, source);
                if keys.is_empty() {
                    format!("{{...}} ({} lines)", line_count)
                } else if keys.len() <= 5 {
                    format!("{{ {} }}", keys.join(", "))
                } else {
                    format!("{{ {}, +{} more }}", keys[..4].join(", "), keys.len() - 4)
                }
            }
            PreviewMode::Source => {
                let text = self.get_node_text(node, source);
                let preview: String = text.chars().take(60).collect();
                if text.len() > 60 {
                    format!("{}...", preview)
                } else {
                    preview
                }
            }
        }
    }
}

impl FoldParser for PythonParser {
    fn parse(&mut self, source: &str, config: &ScanConfig) -> Vec<FoldRegion> {
        match self.parser.parse(source, None) {
            Some(tree) => self.extract_folds(source, &tree, config),
            None => vec![],
        }
    }

    fn language(&self) -> Language {
        Language::Python
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
        let mut parser = PythonParser::new().unwrap();
        let source = r#"
def hello():
    print("hello")
    print("world")
    return True
"#;
        let folds = parser.parse(source, &default_config());
        assert!(!folds.is_empty());
        assert!(folds.iter().any(|f| f.fold_type == FoldType::Block));
    }

    #[test]
    fn test_class_fold() {
        let mut parser = PythonParser::new().unwrap();
        let source = r#"
class MyClass:
    def __init__(self):
        self.x = 1

    def method(self):
        return self.x
"#;
        let folds = parser.parse(source, &default_config());
        assert!(!folds.is_empty());
    }

    #[test]
    fn test_import_fold() {
        let mut parser = PythonParser::new().unwrap();
        let source = r#"
import os
import sys
from typing import List, Dict
from pathlib import Path
"#;
        let folds = parser.parse(source, &default_config());
        assert!(folds.iter().any(|f| f.fold_type == FoldType::Import));
    }

    #[test]
    fn test_list_fold() {
        let mut parser = PythonParser::new().unwrap();
        let source = r#"
items = [
    "item1",
    "item2",
    "item3",
]
"#;
        let folds = parser.parse(source, &default_config());
        assert!(folds.iter().any(|f| f.fold_type == FoldType::ArrayLiteral));
    }

    #[test]
    fn test_dict_fold() {
        let mut parser = PythonParser::new().unwrap();
        let source = r#"
config = {
    "key1": "value1",
    "key2": "value2",
    "key3": "value3",
}
"#;
        let folds = parser.parse(source, &default_config());
        assert!(folds.iter().any(|f| f.fold_type == FoldType::ObjectLiteral));
    }
}
