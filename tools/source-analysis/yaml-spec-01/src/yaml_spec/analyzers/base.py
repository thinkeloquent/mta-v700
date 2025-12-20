"""
Base analyzer interface.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from ..models import FileAnalysis, Language


class BaseAnalyzer(ABC):
    """Abstract base class for code analyzers."""

    @property
    @abstractmethod
    def supported_languages(self) -> list[Language]:
        """Languages this analyzer supports."""
        pass

    @abstractmethod
    def analyze_file(self, path: Path) -> FileAnalysis:
        """
        Analyze a single source file.

        Args:
            path: Path to the source file

        Returns:
            FileAnalysis containing extracted information
        """
        pass

    def can_analyze(self, language: Language) -> bool:
        """Check if this analyzer can handle the given language."""
        return language in self.supported_languages

    def _extract_docstring(self, docstring: Optional[str]) -> Optional[str]:
        """Clean up a docstring."""
        if not docstring:
            return None
        # Remove leading/trailing whitespace and normalize
        cleaned = docstring.strip()
        # Remove triple quotes if present
        if cleaned.startswith('"""') and cleaned.endswith('"""'):
            cleaned = cleaned[3:-3].strip()
        elif cleaned.startswith("'''") and cleaned.endswith("'''"):
            cleaned = cleaned[3:-3].strip()
        return cleaned if cleaned else None
