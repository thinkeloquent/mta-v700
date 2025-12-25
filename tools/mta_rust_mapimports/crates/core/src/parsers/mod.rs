mod javascript;
mod python;

pub use javascript::JavaScriptParser;
pub use python::PythonParser;

use crate::models::{ImportStatement, Language};
use thiserror::Error;

#[derive(Error, Debug)]
pub enum ParserError {
    #[error("Failed to initialize parser: {0}")]
    InitError(String),
    #[error("Failed to parse source code: {0}")]
    ParseError(String),
    #[error("Unsupported language: {0:?}")]
    UnsupportedLanguage(Language),
}

/// Trait for language-specific import parsers
pub trait ImportParser {
    /// Parse source code and extract import statements
    fn parse(&mut self, source: &str) -> Vec<ImportStatement>;

    /// Get the language this parser handles
    fn language(&self) -> Language;
}

/// Create a parser for the given language
pub fn create_parser(language: &Language) -> Result<Box<dyn ImportParser>, ParserError> {
    match language {
        Language::Python => Ok(Box::new(PythonParser::new()?)),
        Language::JavaScript => Ok(Box::new(JavaScriptParser::new(false)?)),
        Language::TypeScript => Ok(Box::new(JavaScriptParser::new(true)?)),
    }
}
