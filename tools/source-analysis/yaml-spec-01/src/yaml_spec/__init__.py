"""
YAML Spec Generator - Automated source code analysis and specification generation.

This package provides tools to:
1. Discover source files in a directory
2. Analyze code structure (classes, functions, patterns)
3. Generate YAML specification files
"""

__version__ = "0.1.0"

from .discovery import FileDiscovery
from .analyzer import CodeAnalyzer
from .spec_generator import SpecGenerator

__all__ = ["FileDiscovery", "CodeAnalyzer", "SpecGenerator"]
