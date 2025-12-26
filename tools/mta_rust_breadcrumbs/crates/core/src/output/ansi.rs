//! ANSI colored output formatter
//!
//! This module provides colorful terminal output for breadcrumbs and outlines.

use crate::models::{FileOutline, GroupedOutlineMap, LanguageSection, NodeType, OutlineMap, OutlineNode};

// ANSI escape codes
const RESET: &str = "\x1b[0m";
const BOLD: &str = "\x1b[1m";
const DIM: &str = "\x1b[2m";

// Colors (allow unused - defined for completeness)
#[allow(dead_code)]
const BLACK: &str = "\x1b[30m";
#[allow(dead_code)]
const RED: &str = "\x1b[31m";
const GREEN: &str = "\x1b[32m";
const YELLOW: &str = "\x1b[33m";
const BLUE: &str = "\x1b[34m";
const MAGENTA: &str = "\x1b[35m";
const CYAN: &str = "\x1b[36m";
const WHITE: &str = "\x1b[37m";

// Bright colors
#[allow(dead_code)]
const BRIGHT_BLACK: &str = "\x1b[90m";
const BRIGHT_RED: &str = "\x1b[91m";
const BRIGHT_GREEN: &str = "\x1b[92m";
const BRIGHT_YELLOW: &str = "\x1b[93m";
const BRIGHT_BLUE: &str = "\x1b[94m";
const BRIGHT_MAGENTA: &str = "\x1b[95m";
const BRIGHT_CYAN: &str = "\x1b[96m";
const BRIGHT_WHITE: &str = "\x1b[97m";

// Background colors
const BG_BLUE: &str = "\x1b[44m";
const BG_GREEN: &str = "\x1b[42m";

/// Get color for node type
fn node_type_color(node_type: &NodeType) -> &'static str {
    match node_type {
        NodeType::Module => BRIGHT_WHITE,
        NodeType::Class => BRIGHT_YELLOW,
        NodeType::Function | NodeType::AsyncFunction => BRIGHT_CYAN,
        NodeType::Method | NodeType::AsyncMethod => CYAN,
        NodeType::Constructor => BRIGHT_MAGENTA,
        NodeType::Getter | NodeType::Setter => MAGENTA,
        NodeType::Property => BLUE,
        NodeType::Interface => BRIGHT_GREEN,
        NodeType::TypeAlias => GREEN,
        NodeType::Enum => BRIGHT_YELLOW,
        NodeType::Namespace => BRIGHT_BLUE,
        NodeType::ArrowFunction => CYAN,
        NodeType::Lambda => CYAN,
        NodeType::Decorator => MAGENTA,
        NodeType::IfStatement | NodeType::ElifClause | NodeType::ElseClause => DIM,
        NodeType::ForLoop | NodeType::WhileLoop => DIM,
        NodeType::TryBlock | NodeType::ExceptHandler | NodeType::FinallyBlock => YELLOW,
        NodeType::SwitchStatement | NodeType::CaseClause => DIM,
        NodeType::ErrorNode => BRIGHT_RED,
        _ => WHITE,
    }
}

/// Format outline data as ANSI colored text
pub fn format_ansi(data: &OutlineMap) -> String {
    let mut output = String::new();

    // Header
    output.push_str(&format!(
        "\n{}{}  Breadcrumbs Scan Results  {}{}\n\n",
        BOLD, BG_BLUE, RESET, RESET
    ));

    // Root info
    output.push_str(&format!(
        "{}Root:{} {}\n\n",
        BOLD,
        RESET,
        data.root.display()
    ));

    // Stats summary
    output.push_str(&format!(
        "{}Files:{} {}  {}Lines:{} {}  {}Nodes:{} {}\n\n",
        BOLD,
        RESET,
        data.stats.total_files,
        BOLD,
        RESET,
        data.stats.total_lines,
        BOLD,
        RESET,
        data.stats.total_nodes
    ));

    // Files
    for file in &data.files {
        output.push_str(&format_file_ansi(file));
    }

    // Footer
    output.push_str(&format!(
        "\n{}Scan completed in {}ms ({:.2} files/sec){}\n",
        DIM,
        data.metadata.scan_duration_ms,
        data.metadata.files_per_second,
        RESET
    ));

    output
}

/// Format grouped outline data as ANSI colored text
pub fn format_grouped_ansi(data: &GroupedOutlineMap) -> String {
    let mut output = String::new();

    // Header
    output.push_str(&format!(
        "\n{}{}  Breadcrumbs Scan Results (Grouped)  {}{}\n\n",
        BOLD, BG_BLUE, RESET, RESET
    ));

    // Root info
    output.push_str(&format!(
        "{}Root:{} {}\n\n",
        BOLD,
        RESET,
        data.root.display()
    ));

    // Python section
    if data.python.file_count > 0 {
        output.push_str(&format_language_section_ansi(&data.python, BRIGHT_YELLOW, "Python"));
    }

    // Node.js section
    if data.nodejs.file_count > 0 {
        output.push_str(&format_language_section_ansi(&data.nodejs, BRIGHT_GREEN, "Node.js"));
    }

    // Footer
    output.push_str(&format!(
        "\n{}Scan completed in {}ms ({:.2} files/sec){}\n",
        DIM,
        data.metadata.scan_duration_ms,
        data.metadata.files_per_second,
        RESET
    ));

    output
}

/// Format a language section
fn format_language_section_ansi(section: &LanguageSection, color: &str, name: &str) -> String {
    let mut output = String::new();

    // Section header
    output.push_str(&format!(
        "{}{}{}  {}  {}{}\n",
        BOLD, color, BG_GREEN, name, RESET, RESET
    ));
    output.push_str(&format!(
        "{}Files:{} {}  {}Nodes:{} {}  {}Lines:{} {}\n\n",
        BOLD,
        RESET,
        section.file_count,
        BOLD,
        RESET,
        section.total_nodes,
        BOLD,
        RESET,
        section.total_lines
    ));

    // Files
    for file in &section.files {
        output.push_str(&format_file_ansi(file));
    }

    output.push_str("\n");
    output
}

/// Format a single file's outline
fn format_file_ansi(file: &FileOutline) -> String {
    let mut output = String::new();

    // File header
    let lang_color = match file.language {
        crate::models::Language::Python => BRIGHT_YELLOW,
        crate::models::Language::JavaScript => BRIGHT_GREEN,
        crate::models::Language::TypeScript => BRIGHT_BLUE,
    };

    output.push_str(&format!(
        "{}{}📄 {}{} {}({}){}\n",
        BOLD,
        lang_color,
        file.path.display(),
        RESET,
        DIM,
        file.language.display_name(),
        RESET
    ));

    // Errors indicator
    if !file.errors.is_empty() {
        output.push_str(&format!(
            "   {}⚠ {} parse error(s){}\n",
            BRIGHT_RED,
            file.errors.len(),
            RESET
        ));
    }

    // Outline nodes
    for node in &file.nodes {
        output.push_str(&format_node_ansi(node, 1));
    }

    output.push_str("\n");
    output
}

/// Format a single outline node with indentation
fn format_node_ansi(node: &OutlineNode, indent: usize) -> String {
    let mut output = String::new();
    let indent_str = "   ".repeat(indent);

    let color = node_type_color(&node.node_type);
    let icon = get_node_icon(&node.node_type);

    // Node line
    let name = node.name.as_deref().unwrap_or("");
    let line_info = format!(":{}-{}", node.start_line, node.end_line);

    output.push_str(&format!(
        "{}{}{} {}{} {}{}{}{}",
        indent_str,
        color,
        icon,
        node.node_type.label(),
        RESET,
        BOLD,
        name,
        RESET,
        DIM,
    ));

    output.push_str(&format!(" {}{}", line_info, RESET));

    if node.has_error {
        output.push_str(&format!(" {}⚠{}", BRIGHT_RED, RESET));
    }

    output.push_str("\n");

    // Preview if available
    if let Some(ref preview) = node.preview {
        if !preview.is_empty() && node.node_type.is_named_scope() {
            output.push_str(&format!(
                "{}   {}{}{}\n",
                indent_str,
                DIM,
                preview,
                RESET
            ));
        }
    }

    // Children
    for child in &node.children {
        output.push_str(&format_node_ansi(child, indent + 1));
    }

    output
}

/// Get icon for node type
fn get_node_icon(node_type: &NodeType) -> &'static str {
    match node_type {
        NodeType::Module => "📦",
        NodeType::Class => "🔷",
        NodeType::Function | NodeType::AsyncFunction => "⚡",
        NodeType::Method | NodeType::AsyncMethod => "🔹",
        NodeType::Constructor => "🔨",
        NodeType::Getter => "📖",
        NodeType::Setter => "📝",
        NodeType::Property => "📌",
        NodeType::Interface => "📐",
        NodeType::TypeAlias => "🏷",
        NodeType::Enum => "📋",
        NodeType::Namespace => "📁",
        NodeType::ArrowFunction => "➡",
        NodeType::Lambda => "λ",
        NodeType::Decorator => "🎨",
        NodeType::IfStatement => "❓",
        NodeType::ElseClause | NodeType::ElifClause => "↪",
        NodeType::ForLoop => "🔄",
        NodeType::WhileLoop => "🔁",
        NodeType::TryBlock => "🛡",
        NodeType::ExceptHandler => "⚡",
        NodeType::FinallyBlock => "🏁",
        NodeType::SwitchStatement => "🔀",
        NodeType::CaseClause => "📍",
        NodeType::ErrorNode => "❌",
        _ => "•",
    }
}

/// Format breadcrumb trail as ANSI
pub fn format_breadcrumb_ansi(components: &[crate::models::BreadcrumbComponent]) -> String {
    if components.is_empty() {
        return format!("{}(root){}", DIM, RESET);
    }

    components
        .iter()
        .map(|c| {
            let color = node_type_color(&c.node_type);
            let name = c.name.as_deref().unwrap_or(c.node_type.label());
            format!("{}{}{}", color, name, RESET)
        })
        .collect::<Vec<_>>()
        .join(&format!(" {}>{} ", DIM, RESET))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::models::{Language, ScanMetadata, ScanStats};
    use std::path::PathBuf;

    #[test]
    fn test_format_ansi_basic() {
        let data = OutlineMap {
            root: PathBuf::from("/test"),
            files: vec![FileOutline {
                path: PathBuf::from("test.py"),
                absolute_path: PathBuf::from("/test/test.py"),
                language: Language::Python,
                total_lines: 10,
                nodes: vec![OutlineNode::new(
                    NodeType::Function,
                    Some("hello".to_string()),
                    1,
                    5,
                )],
                errors: vec![],
            }],
            stats: ScanStats {
                total_files: 1,
                total_lines: 10,
                total_nodes: 1,
                python_files: 1,
                javascript_files: 0,
                typescript_files: 0,
                files_with_errors: 0,
            },
            metadata: ScanMetadata {
                scan_duration_ms: 100,
                files_per_second: 10.0,
                timestamp: "2024-01-01T00:00:00Z".to_string(),
                tool_version: "0.1.0".to_string(),
            },
        };

        let output = format_ansi(&data);
        assert!(output.contains("Breadcrumbs"));
        assert!(output.contains("test.py"));
        assert!(output.contains("hello"));
    }

    #[test]
    fn test_node_icons() {
        assert_eq!(get_node_icon(&NodeType::Function), "⚡");
        assert_eq!(get_node_icon(&NodeType::Class), "🔷");
        assert_eq!(get_node_icon(&NodeType::Interface), "📐");
    }
}
