use crate::models::FoldMap;
use super::FormatError;

/// Convert FoldMap to pretty-printed JSON
pub fn to_json(fold_map: &FoldMap) -> Result<String, FormatError> {
    serde_json::to_string_pretty(fold_map).map_err(FormatError::from)
}

/// Convert FoldMap to compact JSON
#[allow(dead_code)]
pub fn to_json_compact(fold_map: &FoldMap) -> Result<String, FormatError> {
    serde_json::to_string(fold_map).map_err(FormatError::from)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::models::{FoldStats, ScanMetadata};
    use std::path::PathBuf;

    #[test]
    fn test_to_json() {
        let fold_map = FoldMap {
            root: PathBuf::from("/test"),
            files: vec![],
            stats: FoldStats::default(),
            metadata: ScanMetadata::default(),
        };

        let json = to_json(&fold_map).unwrap();
        assert!(json.contains("\"root\""));
        assert!(json.contains("\"files\""));
    }
}
