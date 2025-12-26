//! YAML output formatter

use crate::models::OutlineMap;
use crate::output::FormatError;

/// Format outline data as YAML
pub fn format_yaml(data: &OutlineMap) -> Result<String, FormatError> {
    serde_yaml::to_string(data).map_err(FormatError::from)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::models::{FileOutline, Language, OutlineNode, NodeType, ScanMetadata, ScanStats};
    use std::path::PathBuf;

    fn create_test_data() -> OutlineMap {
        OutlineMap {
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
        }
    }

    #[test]
    fn test_format_yaml() {
        let data = create_test_data();
        let result = format_yaml(&data);
        assert!(result.is_ok());
        let yaml = result.unwrap();
        assert!(yaml.contains("root:"));
        assert!(yaml.contains("files:"));
        assert!(yaml.contains("hello"));
    }
}
