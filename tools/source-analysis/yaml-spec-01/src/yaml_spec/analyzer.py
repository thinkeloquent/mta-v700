"""
Main code analyzer that coordinates language-specific analyzers.
"""

from pathlib import Path
from typing import Dict, List, Optional

from .discovery import DiscoveryResult, FileDiscovery
from .models import FileAnalysis, Language, PackageAnalysis
from .analyzers.python_analyzer import PythonAnalyzer
from .analyzers.javascript_analyzer import JavaScriptAnalyzer
from .analyzers.base import BaseAnalyzer


class CodeAnalyzer:
    """
    Main analyzer that coordinates file discovery and language-specific analysis.

    Automatically selects the appropriate analyzer based on file type.
    """

    def __init__(self):
        """Initialize with all available analyzers."""
        self._analyzers: Dict[Language, BaseAnalyzer] = {}

        # Register built-in analyzers
        python_analyzer = PythonAnalyzer()
        js_analyzer = JavaScriptAnalyzer()

        for lang in python_analyzer.supported_languages:
            self._analyzers[lang] = python_analyzer

        for lang in js_analyzer.supported_languages:
            self._analyzers[lang] = js_analyzer

        self._discovery = FileDiscovery()

    def analyze_directory(
        self,
        path: str | Path,
        include_tests: bool = True,
    ) -> PackageAnalysis:
        """
        Analyze all source files in a directory.

        Args:
            path: Directory path to analyze
            include_tests: Whether to include test files

        Returns:
            PackageAnalysis containing all file analyses
        """
        self._discovery.include_tests = include_tests
        discovery_result = self._discovery.discover(path)

        package = PackageAnalysis(
            name=discovery_result.package_info.get("name", Path(path).name),
            path=str(discovery_result.root_path),
            version=discovery_result.package_info.get("version"),
            description=discovery_result.package_info.get("description"),
            dependencies=discovery_result.package_info.get("dependencies", {}),
        )

        # Analyze each discovered file
        for discovered_file in discovery_result.files:
            analyzer = self._analyzers.get(discovered_file.language)
            if analyzer:
                try:
                    analysis = analyzer.analyze_file(discovered_file.path)
                    # Use relative path in analysis
                    analysis.path = discovered_file.relative_path
                    package.files.append(analysis)
                except Exception as e:
                    # Create minimal analysis for files that fail
                    package.files.append(FileAnalysis(
                        path=discovered_file.relative_path,
                        language=discovered_file.language,
                        module_docstring=f"[Analysis Error: {e}]",
                    ))

        return package

    def analyze_file(self, path: str | Path) -> FileAnalysis:
        """
        Analyze a single source file.

        Args:
            path: Path to the source file

        Returns:
            FileAnalysis for the file
        """
        file_path = Path(path)
        ext = file_path.suffix.lower()

        # Determine language
        language = FileDiscovery.EXTENSION_MAP.get(ext, Language.UNKNOWN)

        analyzer = self._analyzers.get(language)
        if not analyzer:
            return FileAnalysis(
                path=str(file_path),
                language=language,
                module_docstring=f"[No analyzer available for {language.value}]",
            )

        return analyzer.analyze_file(file_path)

    def analyze_multiple_directories(
        self,
        paths: List[str | Path],
        include_tests: bool = True,
    ) -> List[PackageAnalysis]:
        """
        Analyze multiple directories.

        Args:
            paths: List of directory paths
            include_tests: Whether to include test files

        Returns:
            List of PackageAnalysis objects
        """
        results = []
        for path in paths:
            try:
                analysis = self.analyze_directory(path, include_tests)
                results.append(analysis)
            except Exception as e:
                # Create minimal analysis for directories that fail
                results.append(PackageAnalysis(
                    name=Path(path).name,
                    path=str(path),
                    description=f"[Analysis Error: {e}]",
                ))
        return results

    def get_supported_languages(self) -> List[Language]:
        """Get list of supported languages."""
        return list(self._analyzers.keys())
