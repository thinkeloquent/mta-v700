use crate::config::ScanConfig;
use crate::models::{FoldRegion, FoldType, RenderedFile};
use ropey::Rope;
use std::fs;
use std::path::Path;
use termcolor::Color;

/// Renderer for producing folded output
pub struct Renderer {
    config: ScanConfig,
}

impl Renderer {
    pub fn new(config: ScanConfig) -> Self {
        Self { config }
    }

    /// Render a file with folds applied, returning plain text
    pub fn render(&self, source: &str, folds: &[FoldRegion]) -> String {
        if folds.is_empty() {
            return source.to_string();
        }

        let rope = Rope::from_str(source);
        let mut result = String::with_capacity(source.len());

        // Sort folds by start position, largest first (for nested handling)
        let mut sorted_folds: Vec<&FoldRegion> = folds.iter().collect();
        sorted_folds.sort_by_key(|f| (f.start_byte, -(f.end_byte as i64)));

        // Filter to only non-overlapping, outermost folds
        let active_folds = self.filter_overlapping_folds(&sorted_folds);

        let mut current_byte = 0;

        for fold in active_folds {
            // Check if this fold should be applied based on config
            if !self.config.fold_filter.should_fold(&fold.fold_type) {
                continue;
            }

            // Skip if fold starts before current position (nested/overlapping)
            if fold.start_byte < current_byte {
                continue;
            }

            // Add text before the fold
            if fold.start_byte > current_byte {
                let start_char = rope.byte_to_char(current_byte);
                let end_char = rope.byte_to_char(fold.start_byte);
                result.push_str(&rope.slice(start_char..end_char).to_string());
            }

            // Add fold placeholder
            result.push_str(&self.format_placeholder(fold));

            current_byte = fold.end_byte;
        }

        // Add remaining text after last fold
        if current_byte < source.len() {
            let start_char = rope.byte_to_char(current_byte);
            result.push_str(&rope.slice(start_char..).to_string());
        }

        result
    }

    /// Render a file with ANSI color codes
    pub fn render_ansi(&self, source: &str, folds: &[FoldRegion]) -> String {
        if folds.is_empty() {
            return source.to_string();
        }

        let rope = Rope::from_str(source);
        let mut result = String::with_capacity(source.len());

        let mut sorted_folds: Vec<&FoldRegion> = folds.iter().collect();
        sorted_folds.sort_by_key(|f| (f.start_byte, -(f.end_byte as i64)));

        let active_folds = self.filter_overlapping_folds(&sorted_folds);

        let mut current_byte = 0;

        for fold in active_folds {
            if !self.config.fold_filter.should_fold(&fold.fold_type) {
                continue;
            }

            if fold.start_byte < current_byte {
                continue;
            }

            // Add text before the fold
            if fold.start_byte > current_byte {
                let start_char = rope.byte_to_char(current_byte);
                let end_char = rope.byte_to_char(fold.start_byte);
                result.push_str(&rope.slice(start_char..end_char).to_string());
            }

            // Add colored fold placeholder
            result.push_str(&self.format_placeholder_ansi(fold));

            current_byte = fold.end_byte;
        }

        // Add remaining text
        if current_byte < source.len() {
            let start_char = rope.byte_to_char(current_byte);
            result.push_str(&rope.slice(start_char..).to_string());
        }

        result
    }

    /// Filter out overlapping folds, keeping only outermost ones
    fn filter_overlapping_folds<'a>(&self, folds: &[&'a FoldRegion]) -> Vec<&'a FoldRegion> {
        let mut result: Vec<&FoldRegion> = Vec::new();

        for fold in folds {
            // Check if this fold is contained within any existing fold
            let is_nested = result.iter().any(|f| {
                f.start_byte <= fold.start_byte && f.end_byte >= fold.end_byte
            });

            if !is_nested {
                // Remove any folds that this one contains
                result.retain(|f| {
                    !(fold.start_byte <= f.start_byte && fold.end_byte >= f.end_byte)
                });
                result.push(fold);
            }
        }

        // Sort by start position
        result.sort_by_key(|f| f.start_byte);
        result
    }

    /// Format a fold placeholder (plain text)
    fn format_placeholder(&self, fold: &FoldRegion) -> String {
        let preview = fold.preview.as_deref().unwrap_or("...");
        let _type_str = fold.fold_type.as_str();

        if fold.line_count > 1 {
            format!("/* {} ({} lines) */", preview, fold.line_count)
        } else {
            format!("/* {} */", preview)
        }
    }

    /// Format a fold placeholder with ANSI colors
    fn format_placeholder_ansi(&self, fold: &FoldRegion) -> String {
        let preview = fold.preview.as_deref().unwrap_or("...");
        let color = self.get_fold_color(&fold.fold_type);

        // ANSI escape codes
        let dim = "\x1b[2m";
        let reset = "\x1b[0m";
        let fg_color = match color {
            Color::Blue => "\x1b[34m",
            Color::Green => "\x1b[32m",
            Color::Yellow => "\x1b[33m",
            Color::Magenta => "\x1b[35m",
            Color::Cyan => "\x1b[36m",
            Color::Red => "\x1b[31m",
            _ => "\x1b[90m", // Gray
        };

        if fold.line_count > 1 {
            format!(
                "{}{}/* {} ({} lines) */{}",
                dim, fg_color, preview, fold.line_count, reset
            )
        } else {
            format!("{}{}/* {} */{}", dim, fg_color, preview, reset)
        }
    }

    /// Get color for fold type
    fn get_fold_color(&self, fold_type: &FoldType) -> Color {
        match fold_type {
            FoldType::Block => Color::Blue,
            FoldType::Import => Color::Green,
            FoldType::ArgList => Color::Yellow,
            FoldType::ChainedCall => Color::Magenta,
            FoldType::Literal => Color::Cyan,
            FoldType::Comment => Color::White,
            FoldType::DocComment => Color::Green,
            FoldType::ClassBody => Color::Blue,
            FoldType::ArrayLiteral => Color::Cyan,
            FoldType::ObjectLiteral => Color::Cyan,
        }
    }
}

/// Render a file with folds applied (convenience function)
pub fn render_file(path: &Path, config: &ScanConfig) -> Result<RenderedFile, std::io::Error> {
    let content = fs::read_to_string(path)?;

    let ext = path
        .extension()
        .map(|e| e.to_string_lossy().to_string())
        .unwrap_or_default();

    let language = crate::models::Language::from_extension(&ext).ok_or_else(|| {
        std::io::Error::new(std::io::ErrorKind::InvalidInput, "Unsupported file type")
    })?;

    let mut parser = crate::parsers::create_parser(&language).map_err(|e| {
        std::io::Error::new(std::io::ErrorKind::Other, e.to_string())
    })?;

    let folds = parser.parse(&content, config);
    let renderer = Renderer::new(config.clone());
    let rendered = renderer.render(&content, &folds);

    let lines_hidden: usize = folds.iter().map(|f| f.line_count.saturating_sub(1)).sum();

    Ok(RenderedFile {
        path: path.to_path_buf(),
        content: rendered,
        fold_count: folds.len(),
        lines_hidden,
    })
}

/// Render a file with ANSI colors (convenience function)
pub fn render_file_ansi(path: &Path, config: &ScanConfig) -> Result<RenderedFile, std::io::Error> {
    let content = fs::read_to_string(path)?;

    let ext = path
        .extension()
        .map(|e| e.to_string_lossy().to_string())
        .unwrap_or_default();

    let language = crate::models::Language::from_extension(&ext).ok_or_else(|| {
        std::io::Error::new(std::io::ErrorKind::InvalidInput, "Unsupported file type")
    })?;

    let mut parser = crate::parsers::create_parser(&language).map_err(|e| {
        std::io::Error::new(std::io::ErrorKind::Other, e.to_string())
    })?;

    let folds = parser.parse(&content, config);
    let renderer = Renderer::new(config.clone());
    let rendered = renderer.render_ansi(&content, &folds);

    let lines_hidden: usize = folds.iter().map(|f| f.line_count.saturating_sub(1)).sum();

    Ok(RenderedFile {
        path: path.to_path_buf(),
        content: rendered,
        fold_count: folds.len(),
        lines_hidden,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::models::FoldFilter;

    fn test_config() -> ScanConfig {
        ScanConfig::default()
            .with_min_fold_lines(2)
            .with_fold_filter(FoldFilter::all())
    }

    #[test]
    fn test_renderer_no_folds() {
        let renderer = Renderer::new(test_config());
        let source = "hello world";
        let result = renderer.render(source, &[]);
        assert_eq!(result, source);
    }

    #[test]
    fn test_renderer_single_fold() {
        let renderer = Renderer::new(test_config());
        let source = "function test() {\n  line1\n  line2\n  line3\n}";

        let fold = FoldRegion::new(FoldType::Block, 17, 44, 1, 5, 17, 1);

        let result = renderer.render(source, &[fold]);
        assert!(result.contains("/*"));
        assert!(!result.contains("line1"));
    }
}
