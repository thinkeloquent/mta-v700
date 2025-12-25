use crate::models::ImportMap;
use super::FormatError;

/// Serialize ImportMap to YAML
pub fn to_yaml(import_map: &ImportMap) -> Result<String, FormatError> {
    serde_yaml::to_string(import_map).map_err(FormatError::from)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::models::{ImportStats, ScanMetadata};
    use std::collections::HashMap;
    use std::path::PathBuf;

    #[test]
    fn test_to_yaml() {
        let import_map = ImportMap {
            root: PathBuf::from("/test"),
            files: vec![],
            manifests: vec![],
            external_dependencies: HashMap::new(),
            internal_packages: vec![],
            stats: ImportStats::default(),
            metadata: ScanMetadata::default(),
        };

        let yaml = to_yaml(&import_map).unwrap();
        assert!(yaml.contains("root:"));
        assert!(yaml.contains("files:"));
    }
}
