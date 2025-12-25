//! WASM bindings for MTA Rust MapImports
//!
//! This module provides WebAssembly bindings for the import mapper,
//! allowing it to be used in web applications.

use serde::{Deserialize, Serialize};
use wasm_bindgen::prelude::*;

/// Configuration for WASM scanning
#[derive(Serialize, Deserialize)]
pub struct WasmScanConfig {
    pub root: String,
    pub include_deps: bool,
    pub language_filter: Option<Vec<String>>,
    pub ignore_patterns: Vec<String>,
}

/// Scan result for WASM
#[derive(Serialize, Deserialize)]
pub struct WasmScanResult {
    pub success: bool,
    pub data: Option<String>,
    pub error: Option<String>,
}

/// Initialize the WASM module
#[wasm_bindgen(start)]
pub fn init() {
    // Set up panic hook for better error messages
    #[cfg(feature = "console_error_panic_hook")]
    console_error_panic_hook::set_once();
}

/// Scan a project and return JSON results
///
/// Note: This is a placeholder for future WASM support.
/// Full filesystem access is not available in WASM, so this would need
/// to be adapted to work with a virtual filesystem or provided file contents.
#[wasm_bindgen]
pub fn scan_project_json(_config: JsValue) -> JsValue {
    let result = WasmScanResult {
        success: false,
        data: None,
        error: Some("WASM scanning requires filesystem access. Use with virtual filesystem or provide file contents directly.".to_string()),
    };

    serde_wasm_bindgen::to_value(&result).unwrap_or(JsValue::NULL)
}

/// Parse a single Python file and return imports as JSON
#[wasm_bindgen]
pub fn parse_python_file(source: &str) -> JsValue {
    use mta_rust_mapimports_core::parsers::PythonParser;
    use mta_rust_mapimports_core::parsers::ImportParser;

    match PythonParser::new() {
        Ok(mut parser) => {
            let imports = parser.parse(source);
            let result = WasmScanResult {
                success: true,
                data: serde_json::to_string(&imports).ok(),
                error: None,
            };
            serde_wasm_bindgen::to_value(&result).unwrap_or(JsValue::NULL)
        }
        Err(e) => {
            let result = WasmScanResult {
                success: false,
                data: None,
                error: Some(e.to_string()),
            };
            serde_wasm_bindgen::to_value(&result).unwrap_or(JsValue::NULL)
        }
    }
}

/// Parse a single JavaScript file and return imports as JSON
#[wasm_bindgen]
pub fn parse_javascript_file(source: &str, typescript: bool) -> JsValue {
    use mta_rust_mapimports_core::parsers::JavaScriptParser;
    use mta_rust_mapimports_core::parsers::ImportParser;

    match JavaScriptParser::new(typescript) {
        Ok(mut parser) => {
            let imports = parser.parse(source);
            let result = WasmScanResult {
                success: true,
                data: serde_json::to_string(&imports).ok(),
                error: None,
            };
            serde_wasm_bindgen::to_value(&result).unwrap_or(JsValue::NULL)
        }
        Err(e) => {
            let result = WasmScanResult {
                success: false,
                data: None,
                error: Some(e.to_string()),
            };
            serde_wasm_bindgen::to_value(&result).unwrap_or(JsValue::NULL)
        }
    }
}

/// Get the library version
#[wasm_bindgen]
pub fn get_version() -> String {
    env!("CARGO_PKG_VERSION").to_string()
}
