use crate::models::FoldMap;
use super::FormatError;

/// Convert FoldMap to YAML
pub fn to_yaml(fold_map: &FoldMap) -> Result<String, FormatError> {
    serde_yaml::to_string(fold_map).map_err(FormatError::from)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::models::{FoldStats, ScanMetadata};
    use std::path::PathBuf;

    #[test]
    fn test_to_yaml() {
        let fold_map = FoldMap {
            root: PathBuf::from("/test"),
            files: vec![],
            stats: FoldStats::default(),
            metadata: ScanMetadata::default(),
        };

        let yaml = to_yaml(&fold_map).unwrap();
        assert!(yaml.contains("root:"));
        assert!(yaml.contains("files:"));
    }
}
