use crate::models::ImportMap;
use super::FormatError;

/// Serialize ImportMap to pretty-printed JSON
pub fn to_json(import_map: &ImportMap) -> Result<String, FormatError> {
    serde_json::to_string_pretty(import_map).map_err(FormatError::from)
}

/// Serialize ImportMap to compact JSON
#[allow(dead_code)]
pub fn to_json_compact(import_map: &ImportMap) -> Result<String, FormatError> {
    serde_json::to_string(import_map).map_err(FormatError::from)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::models::{ImportStats, ScanMetadata};
    use std::collections::HashMap;
    use std::path::PathBuf;

    #[test]
    fn test_to_json() {
        let import_map = ImportMap {
            root: PathBuf::from("/test"),
            files: vec![],
            manifests: vec![],
            external_dependencies: HashMap::new(),
            internal_packages: vec![],
            stats: ImportStats::default(),
            metadata: ScanMetadata::default(),
        };

        let json = to_json(&import_map).unwrap();
        assert!(json.contains("\"root\""));
        assert!(json.contains("\"files\""));
    }
}
