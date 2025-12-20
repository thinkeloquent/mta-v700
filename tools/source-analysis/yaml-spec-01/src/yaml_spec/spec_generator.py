"""
High-level spec generator combining analysis and output generation.
"""

from pathlib import Path
from typing import List, Optional

from .analyzer import CodeAnalyzer
from .generators.yaml_generator import YamlSpecGenerator
from .models import PackageAnalysis


class SpecGenerator:
    """
    High-level API for generating YAML specifications from source code.

    Combines file discovery, code analysis, and YAML generation into a
    single interface.

    Example:
        generator = SpecGenerator()
        yaml_str = generator.generate(
            directories=["./src", "./lib"],
            output_path="./docs/spec.yaml",
        )
    """

    def __init__(
        self,
        include_tests: bool = True,
        include_line_numbers: bool = False,
        include_imports: bool = True,
        include_constants: bool = True,
        group_by_pattern: bool = True,
    ):
        """
        Initialize the spec generator.

        Args:
            include_tests: Include test files in analysis
            include_line_numbers: Include line numbers in output
            include_imports: Include import statements
            include_constants: Include constant definitions
            group_by_pattern: Group classes by detected pattern
        """
        self._analyzer = CodeAnalyzer()
        self._yaml_generator = YamlSpecGenerator(
            include_line_numbers=include_line_numbers,
            include_imports=include_imports,
            include_constants=include_constants,
            group_by_pattern=group_by_pattern,
        )
        self._include_tests = include_tests

    def generate(
        self,
        directories: List[str | Path],
        output_path: Optional[str | Path] = None,
        spec_name: Optional[str] = None,
    ) -> str:
        """
        Generate YAML specification from source directories.

        Args:
            directories: List of directories to analyze
            output_path: Path to write output file (optional)
            spec_name: Name for the specification (optional)

        Returns:
            Generated YAML string
        """
        # Analyze all directories
        analyses = self._analyzer.analyze_multiple_directories(
            directories,
            include_tests=self._include_tests,
        )

        # Generate YAML
        return self._yaml_generator.generate(
            analyses=analyses,
            output_path=output_path,
            spec_name=spec_name,
        )

    def generate_single(
        self,
        directory: str | Path,
        output_path: Optional[str | Path] = None,
        spec_name: Optional[str] = None,
    ) -> str:
        """
        Generate YAML specification from a single directory.

        Args:
            directory: Directory to analyze
            output_path: Path to write output file (optional)
            spec_name: Name for the specification (optional)

        Returns:
            Generated YAML string
        """
        return self.generate(
            directories=[directory],
            output_path=output_path,
            spec_name=spec_name,
        )

    def analyze(self, directory: str | Path) -> PackageAnalysis:
        """
        Analyze a directory without generating YAML.

        Useful for programmatic access to analysis results.

        Args:
            directory: Directory to analyze

        Returns:
            PackageAnalysis object
        """
        return self._analyzer.analyze_directory(
            directory,
            include_tests=self._include_tests,
        )
