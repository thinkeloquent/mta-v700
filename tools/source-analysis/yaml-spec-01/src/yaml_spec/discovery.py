"""
File discovery module - scans directories for source files.
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

from .models import Language


@dataclass
class DiscoveredFile:
    """Represents a discovered source file."""
    path: Path
    language: Language
    relative_path: str
    size_bytes: int


@dataclass
class DiscoveryResult:
    """Result of file discovery operation."""
    root_path: Path
    files: List[DiscoveredFile] = field(default_factory=list)
    package_info: Dict[str, any] = field(default_factory=dict)

    @property
    def by_language(self) -> Dict[Language, List[DiscoveredFile]]:
        """Group files by language."""
        result: Dict[Language, List[DiscoveredFile]] = {}
        for f in self.files:
            if f.language not in result:
                result[f.language] = []
            result[f.language].append(f)
        return result

    @property
    def total_files(self) -> int:
        return len(self.files)


class FileDiscovery:
    """
    Discovers source files in a directory tree.

    Supports Python, JavaScript, and TypeScript files.
    Automatically detects package configuration files.
    """

    # File extensions mapped to languages
    EXTENSION_MAP: Dict[str, Language] = {
        ".py": Language.PYTHON,
        ".pyi": Language.PYTHON,
        ".js": Language.JAVASCRIPT,
        ".mjs": Language.JAVASCRIPT,
        ".cjs": Language.JAVASCRIPT,
        ".jsx": Language.JAVASCRIPT,
        ".ts": Language.TYPESCRIPT,
        ".tsx": Language.TYPESCRIPT,
        ".mts": Language.TYPESCRIPT,
        ".cts": Language.TYPESCRIPT,
    }

    # Directories to skip
    DEFAULT_IGNORE_DIRS: Set[str] = {
        "node_modules",
        "__pycache__",
        ".git",
        ".svn",
        ".hg",
        "venv",
        ".venv",
        "env",
        ".env",
        "dist",
        "build",
        ".tox",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "coverage",
        ".coverage",
        ".nyc_output",
        "htmlcov",
        "egg-info",
        ".eggs",
    }

    # Package config files to look for
    PACKAGE_CONFIG_FILES: Set[str] = {
        "package.json",
        "pyproject.toml",
        "setup.py",
        "setup.cfg",
        "Cargo.toml",
    }

    def __init__(
        self,
        ignore_dirs: Optional[Set[str]] = None,
        ignore_patterns: Optional[List[str]] = None,
        include_tests: bool = True,
    ):
        """
        Initialize file discovery.

        Args:
            ignore_dirs: Additional directories to ignore
            ignore_patterns: Glob patterns to ignore
            include_tests: Whether to include test files
        """
        self.ignore_dirs = self.DEFAULT_IGNORE_DIRS.copy()
        if ignore_dirs:
            self.ignore_dirs.update(ignore_dirs)

        self.ignore_patterns = ignore_patterns or []
        self.include_tests = include_tests

    def discover(self, path: str | Path) -> DiscoveryResult:
        """
        Discover all source files in the given path.

        Args:
            path: Directory path to scan

        Returns:
            DiscoveryResult containing all discovered files
        """
        root = Path(path).resolve()
        if not root.exists():
            raise FileNotFoundError(f"Path does not exist: {root}")

        if not root.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {root}")

        result = DiscoveryResult(root_path=root)

        # Discover package info first
        result.package_info = self._discover_package_info(root)

        # Walk the directory tree
        for dirpath, dirnames, filenames in os.walk(root):
            # Filter out ignored directories
            dirnames[:] = [
                d for d in dirnames
                if d not in self.ignore_dirs
                and not d.endswith(".egg-info")
            ]

            current_dir = Path(dirpath)

            # Skip test directories if configured
            if not self.include_tests:
                if any(part in ["test", "tests", "__tests__"] for part in current_dir.parts):
                    continue

            for filename in filenames:
                file_path = current_dir / filename

                # Check extension
                ext = file_path.suffix.lower()
                if ext not in self.EXTENSION_MAP:
                    continue

                # Check ignore patterns
                if self._should_ignore(file_path, root):
                    continue

                discovered = DiscoveredFile(
                    path=file_path,
                    language=self.EXTENSION_MAP[ext],
                    relative_path=str(file_path.relative_to(root)),
                    size_bytes=file_path.stat().st_size,
                )
                result.files.append(discovered)

        # Sort files by path for consistent ordering
        result.files.sort(key=lambda f: f.relative_path)

        return result

    def _should_ignore(self, file_path: Path, root: Path) -> bool:
        """Check if a file should be ignored."""
        rel_path = str(file_path.relative_to(root))

        for pattern in self.ignore_patterns:
            if file_path.match(pattern):
                return True

        # Skip common non-source files
        if file_path.name.startswith("."):
            return True

        return False

    def _discover_package_info(self, root: Path) -> Dict[str, any]:
        """Extract package information from config files."""
        info: Dict[str, any] = {}

        for config_file in self.PACKAGE_CONFIG_FILES:
            config_path = root / config_file
            if config_path.exists():
                try:
                    if config_file == "package.json":
                        info.update(self._parse_package_json(config_path))
                    elif config_file == "pyproject.toml":
                        info.update(self._parse_pyproject_toml(config_path))
                except Exception:
                    pass

        return info

    def _parse_package_json(self, path: Path) -> Dict[str, any]:
        """Parse package.json for package info."""
        with open(path, "r") as f:
            data = json.load(f)

        result = {}
        if "name" in data:
            result["name"] = data["name"]
        if "version" in data:
            result["version"] = data["version"]
        if "description" in data:
            result["description"] = data["description"]
        if "dependencies" in data:
            result["dependencies"] = data["dependencies"]
        if "devDependencies" in data:
            result["dev_dependencies"] = data["devDependencies"]

        return result

    def _parse_pyproject_toml(self, path: Path) -> Dict[str, any]:
        """Parse pyproject.toml for package info."""
        # Simple TOML parsing without external dependency
        content = path.read_text()
        result = {}

        # Extract basic fields using simple parsing
        lines = content.split("\n")
        in_project = False
        in_dependencies = False
        deps = {}

        for line in lines:
            stripped = line.strip()

            if stripped == "[project]" or stripped == "[tool.poetry]":
                in_project = True
                in_dependencies = False
                continue
            elif stripped.startswith("[") and stripped.endswith("]"):
                in_project = False
                in_dependencies = False
                if "dependencies" in stripped.lower():
                    in_dependencies = True
                continue

            if in_project:
                if stripped.startswith("name"):
                    result["name"] = self._extract_toml_string(stripped)
                elif stripped.startswith("version"):
                    result["version"] = self._extract_toml_string(stripped)
                elif stripped.startswith("description"):
                    result["description"] = self._extract_toml_string(stripped)

            if in_dependencies and "=" in stripped:
                parts = stripped.split("=", 1)
                if len(parts) == 2:
                    key = parts[0].strip().strip('"').strip("'")
                    val = parts[1].strip().strip('"').strip("'")
                    if key and not key.startswith("#"):
                        deps[key] = val

        if deps:
            result["dependencies"] = deps

        return result

    def _extract_toml_string(self, line: str) -> str:
        """Extract a string value from a TOML line."""
        if "=" not in line:
            return ""
        value = line.split("=", 1)[1].strip()
        # Remove quotes
        if value.startswith('"') and value.endswith('"'):
            return value[1:-1]
        if value.startswith("'") and value.endswith("'"):
            return value[1:-1]
        return value
