use crate::models::{ImportStatement, ImportType, Language};
use tree_sitter::{Node, Parser};

use super::{ImportParser, ParserError};

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

    /// Extract imports using tree-sitter queries
    fn extract_imports(&self, source: &str, tree: &tree_sitter::Tree) -> Vec<ImportStatement> {
        let mut imports = Vec::new();
        let root = tree.root_node();

        // Traverse the tree manually to find import statements
        self.traverse_node(&root, source, &mut imports);

        imports
    }

    fn traverse_node(&self, node: &Node, source: &str, imports: &mut Vec<ImportStatement>) {
        match node.kind() {
            "import_statement" => {
                self.parse_import_statement(node, source, imports);
            }
            "import_from_statement" => {
                self.parse_import_from_statement(node, source, imports);
            }
            _ => {
                // Recurse into children
                let mut cursor = node.walk();
                for child in node.children(&mut cursor) {
                    self.traverse_node(&child, source, imports);
                }
            }
        }
    }

    /// Parse `import x, y, z` or `import x as alias`
    fn parse_import_statement(
        &self,
        node: &Node,
        source: &str,
        imports: &mut Vec<ImportStatement>,
    ) {
        let mut cursor = node.walk();
        for child in node.children(&mut cursor) {
            match child.kind() {
                "dotted_name" => {
                    let module = self.get_node_text(&child, source);
                    imports.push(ImportStatement {
                        module,
                        items: vec![],
                        is_default: false,
                        line: child.start_position().row + 1,
                        column: child.start_position().column,
                        raw: self.get_node_text(node, source),
                        import_type: ImportType::Unknown,
                        alias: None,
                    });
                }
                "aliased_import" => {
                    let (module, alias) = self.parse_aliased_import(&child, source);
                    imports.push(ImportStatement {
                        module,
                        items: vec![],
                        is_default: false,
                        line: child.start_position().row + 1,
                        column: child.start_position().column,
                        raw: self.get_node_text(node, source),
                        import_type: ImportType::Unknown,
                        alias,
                    });
                }
                _ => {}
            }
        }
    }

    /// Parse `from x import y, z` or `from . import x` or `from ..x import y`
    fn parse_import_from_statement(
        &self,
        node: &Node,
        source: &str,
        imports: &mut Vec<ImportStatement>,
    ) {
        let mut module = String::new();
        let mut items = Vec::new();
        let mut alias: Option<String> = None;
        let mut is_wildcard = false;

        let mut cursor = node.walk();
        for child in node.children(&mut cursor) {
            match child.kind() {
                "dotted_name" => {
                    if module.is_empty() {
                        module = self.get_node_text(&child, source);
                    } else {
                        items.push(self.get_node_text(&child, source));
                    }
                }
                "relative_import" => {
                    module = self.parse_relative_import(&child, source);
                }
                "aliased_import" => {
                    let (name, al) = self.parse_aliased_import(&child, source);
                    items.push(name);
                    if al.is_some() {
                        alias = al;
                    }
                }
                "wildcard_import" => {
                    is_wildcard = true;
                    items.push("*".to_string());
                }
                "identifier" => {
                    items.push(self.get_node_text(&child, source));
                }
                _ => {}
            }
        }

        if !module.is_empty() || !items.is_empty() {
            imports.push(ImportStatement {
                module,
                items,
                is_default: is_wildcard,
                line: node.start_position().row + 1,
                column: node.start_position().column,
                raw: self.get_node_text(node, source),
                import_type: ImportType::Unknown,
                alias,
            });
        }
    }

    /// Parse relative import prefix (., .., ...)
    fn parse_relative_import(&self, node: &Node, source: &str) -> String {
        let mut prefix = String::new();
        let mut module_part = String::new();

        let mut cursor = node.walk();
        for child in node.children(&mut cursor) {
            match child.kind() {
                "import_prefix" => {
                    prefix = self.get_node_text(&child, source);
                }
                "dotted_name" => {
                    module_part = self.get_node_text(&child, source);
                }
                _ => {}
            }
        }

        if module_part.is_empty() {
            prefix
        } else {
            format!("{}{}", prefix, module_part)
        }
    }

    /// Parse aliased import (x as y)
    fn parse_aliased_import(&self, node: &Node, source: &str) -> (String, Option<String>) {
        let mut name = String::new();
        let mut alias = None;

        let mut cursor = node.walk();
        for child in node.children(&mut cursor) {
            match child.kind() {
                "dotted_name" | "identifier" => {
                    if name.is_empty() {
                        name = self.get_node_text(&child, source);
                    } else {
                        alias = Some(self.get_node_text(&child, source));
                    }
                }
                _ => {}
            }
        }

        (name, alias)
    }

    fn get_node_text(&self, node: &Node, source: &str) -> String {
        source[node.byte_range()].to_string()
    }
}

impl ImportParser for PythonParser {
    fn parse(&mut self, source: &str) -> Vec<ImportStatement> {
        match self.parser.parse(source, None) {
            Some(tree) => self.extract_imports(source, &tree),
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

    #[test]
    fn test_simple_import() {
        let mut parser = PythonParser::new().unwrap();
        let imports = parser.parse("import os\nimport sys");

        assert_eq!(imports.len(), 2);
        assert_eq!(imports[0].module, "os");
        assert_eq!(imports[1].module, "sys");
    }

    #[test]
    fn test_import_with_alias() {
        let mut parser = PythonParser::new().unwrap();
        let imports = parser.parse("import numpy as np");

        assert_eq!(imports.len(), 1);
        assert_eq!(imports[0].module, "numpy");
        assert_eq!(imports[0].alias, Some("np".to_string()));
    }

    #[test]
    fn test_from_import() {
        let mut parser = PythonParser::new().unwrap();
        let imports = parser.parse("from typing import List, Dict, Optional");

        assert_eq!(imports.len(), 1);
        assert_eq!(imports[0].module, "typing");
        assert!(imports[0].items.contains(&"List".to_string()));
        assert!(imports[0].items.contains(&"Dict".to_string()));
    }

    #[test]
    fn test_relative_import() {
        let mut parser = PythonParser::new().unwrap();
        let imports = parser.parse("from . import utils\nfrom ..config import Settings");

        assert_eq!(imports.len(), 2);
        assert_eq!(imports[0].module, ".");
        assert_eq!(imports[1].module, "..config");
    }

    #[test]
    fn test_wildcard_import() {
        let mut parser = PythonParser::new().unwrap();
        let imports = parser.parse("from os.path import *");

        assert_eq!(imports.len(), 1);
        assert_eq!(imports[0].module, "os.path");
        assert!(imports[0].items.contains(&"*".to_string()));
        assert!(imports[0].is_default);
    }
}
