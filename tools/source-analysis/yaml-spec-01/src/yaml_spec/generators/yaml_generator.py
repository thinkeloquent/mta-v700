"""
YAML specification generator.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from ..models import (
    ClassInfo,
    FileAnalysis,
    FunctionInfo,
    PackageAnalysis,
    PatternType,
)


class YamlSpecGenerator:
    """
    Generates YAML specification files from code analysis results.

    Produces structured documentation including:
    - Package metadata
    - File-by-file analysis
    - Class and function specifications
    - Detected patterns and exceptions
    """

    def __init__(
        self,
        include_line_numbers: bool = False,
        include_imports: bool = True,
        include_constants: bool = True,
        group_by_pattern: bool = True,
    ):
        """
        Initialize the generator.

        Args:
            include_line_numbers: Include source line numbers
            include_imports: Include import statements
            include_constants: Include constants
            group_by_pattern: Group classes by detected pattern
        """
        self.include_line_numbers = include_line_numbers
        self.include_imports = include_imports
        self.include_constants = include_constants
        self.group_by_pattern = group_by_pattern

    def generate(
        self,
        analyses: List[PackageAnalysis],
        output_path: Optional[str | Path] = None,
        spec_name: Optional[str] = None,
    ) -> str:
        """
        Generate YAML specification from analysis results.

        Args:
            analyses: List of package analyses
            output_path: Path to write output (optional)
            spec_name: Name for the spec (optional)

        Returns:
            Generated YAML string
        """
        spec = self._build_spec(analyses, spec_name)
        yaml_str = self._to_yaml(spec)

        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(yaml_str)

        return yaml_str

    def _build_spec(
        self,
        analyses: List[PackageAnalysis],
        spec_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build the specification dictionary."""
        spec: Dict[str, Any] = {
            "spec_version": "1.0.0",
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "generator": "yaml-spec-generator v0.1.0",
        }

        if spec_name:
            spec["spec_name"] = spec_name

        # Single package or multi-package
        if len(analyses) == 1:
            spec["package"] = self._build_package_spec(analyses[0])
        else:
            spec["packages"] = [self._build_package_spec(a) for a in analyses]

        # Add analysis metadata
        spec["analysis_metadata"] = self._build_analysis_metadata(analyses)

        return spec

    def _build_package_spec(self, analysis: PackageAnalysis) -> Dict[str, Any]:
        """Build specification for a single package."""
        package: Dict[str, Any] = {
            "name": analysis.name,
            "path": analysis.path,
        }

        if analysis.version:
            package["version"] = analysis.version
        if analysis.description:
            package["description"] = analysis.description
        if analysis.dependencies:
            package["dependencies"] = analysis.dependencies

        # Build components section
        components = self._build_components(analysis)
        if components:
            package["components"] = components

        # Build exceptions section
        exceptions = self._collect_exceptions(analysis)
        if exceptions:
            package["exceptions"] = exceptions

        # Build file index
        package["files"] = self._build_file_index(analysis)

        return package

    def _build_components(self, analysis: PackageAnalysis) -> Dict[str, Any]:
        """Build the components section with classes and functions."""
        components: Dict[str, Any] = {}

        # Collect all classes and functions
        all_classes: List[tuple[str, ClassInfo]] = []
        all_functions: List[tuple[str, FunctionInfo]] = []

        for file_analysis in analysis.files:
            for cls in file_analysis.classes:
                all_classes.append((file_analysis.path, cls))
            for func in file_analysis.functions:
                all_functions.append((file_analysis.path, func))

        # Group classes by pattern if enabled
        if self.group_by_pattern:
            pattern_groups: Dict[str, List[tuple[str, ClassInfo]]] = {}

            for path, cls in all_classes:
                if cls.patterns:
                    for pattern in cls.patterns:
                        key = pattern.value
                        if key not in pattern_groups:
                            pattern_groups[key] = []
                        pattern_groups[key].append((path, cls))
                else:
                    if "classes" not in pattern_groups:
                        pattern_groups["classes"] = []
                    pattern_groups["classes"].append((path, cls))

            for pattern_name, classes in pattern_groups.items():
                section_name = f"{pattern_name}_classes" if pattern_name != "classes" else "classes"
                components[section_name] = {}
                for path, cls in classes:
                    components[section_name][cls.name] = self._build_class_spec(cls, path)
        else:
            if all_classes:
                components["classes"] = {}
                for path, cls in all_classes:
                    components["classes"][cls.name] = self._build_class_spec(cls, path)

        # Add functions
        if all_functions:
            components["functions"] = {}
            for path, func in all_functions:
                components["functions"][func.name] = self._build_function_spec(func, path)

        return components

    def _build_class_spec(self, cls: ClassInfo, file_path: str) -> Dict[str, Any]:
        """Build specification for a class."""
        spec: Dict[str, Any] = {
            "file": file_path,
        }

        if self.include_line_numbers and cls.line_number:
            spec["line"] = cls.line_number

        if cls.docstring:
            spec["description"] = cls.docstring.split("\n")[0].strip()

        if cls.bases:
            spec["extends"] = cls.bases

        if cls.decorators:
            spec["decorators"] = cls.decorators

        if cls.patterns:
            spec["patterns"] = [p.value for p in cls.patterns]

        # Build fields
        if cls.fields:
            spec["fields"] = {}
            for field in cls.fields:
                field_spec: Dict[str, Any] = {}
                if field.type_annotation:
                    field_spec["type"] = field.type_annotation
                if field.default_value:
                    field_spec["default"] = field.default_value
                if field.is_class_var:
                    field_spec["class_variable"] = True
                spec["fields"][field.name] = field_spec if field_spec else {"type": "any"}

        # Build methods
        if cls.methods:
            spec["methods"] = {}
            for method in cls.methods:
                spec["methods"][method.name] = self._build_method_spec(method)

        return spec

    def _build_method_spec(self, method: FunctionInfo) -> Dict[str, Any]:
        """Build specification for a method."""
        spec: Dict[str, Any] = {}

        if method.docstring:
            spec["description"] = method.docstring.split("\n")[0].strip()

        if method.is_async:
            spec["async"] = True
        if method.is_static:
            spec["static"] = True
        if method.is_classmethod:
            spec["classmethod"] = True
        if method.is_property:
            spec["property"] = True

        if method.parameters:
            spec["parameters"] = {}
            for param in method.parameters:
                param_spec: Dict[str, Any] = {}
                if param.type_annotation:
                    param_spec["type"] = param.type_annotation
                if param.default_value:
                    param_spec["default"] = param.default_value
                param_spec["required"] = param.is_required
                spec["parameters"][param.name] = param_spec

        if method.return_type:
            spec["returns"] = method.return_type

        if method.decorators:
            spec["decorators"] = method.decorators

        return spec

    def _build_function_spec(self, func: FunctionInfo, file_path: str) -> Dict[str, Any]:
        """Build specification for a function."""
        spec = self._build_method_spec(func)
        spec["file"] = file_path

        if self.include_line_numbers and func.line_number:
            spec["line"] = func.line_number

        return spec

    def _collect_exceptions(self, analysis: PackageAnalysis) -> Dict[str, Any]:
        """Collect all exceptions from the analysis."""
        exceptions: Dict[str, Any] = {}

        for file_analysis in analysis.files:
            for exc in file_analysis.exceptions:
                exceptions[exc.name] = {
                    "extends": exc.base,
                    "file": file_analysis.path,
                }
                if exc.docstring:
                    exceptions[exc.name]["description"] = exc.docstring.split("\n")[0].strip()

        return exceptions

    def _build_file_index(self, analysis: PackageAnalysis) -> List[Dict[str, Any]]:
        """Build file index with summaries."""
        files = []

        for file_analysis in analysis.files:
            file_info: Dict[str, Any] = {
                "path": file_analysis.path,
                "language": file_analysis.language.value,
            }

            if file_analysis.module_docstring:
                file_info["description"] = file_analysis.module_docstring.split("\n")[0].strip()

            # Summary counts
            summary = {}
            if file_analysis.classes:
                summary["classes"] = len(file_analysis.classes)
            if file_analysis.functions:
                summary["functions"] = len(file_analysis.functions)
            if file_analysis.exceptions:
                summary["exceptions"] = len(file_analysis.exceptions)
            if file_analysis.constants:
                summary["constants"] = len(file_analysis.constants)

            if summary:
                file_info["summary"] = summary

            # Include imports if enabled
            if self.include_imports and file_analysis.imports:
                file_info["imports"] = [imp.to_dict() for imp in file_analysis.imports]

            # Include constants if enabled
            if self.include_constants and file_analysis.constants:
                file_info["constants"] = [const.to_dict() for const in file_analysis.constants]

            # Include exports
            if file_analysis.exports:
                file_info["exports"] = file_analysis.exports

            files.append(file_info)

        return files

    def _build_analysis_metadata(self, analyses: List[PackageAnalysis]) -> Dict[str, Any]:
        """Build metadata about the analysis process."""
        total_files = sum(len(a.files) for a in analyses)
        total_classes = sum(
            sum(len(f.classes) for f in a.files) for a in analyses
        )
        total_functions = sum(
            sum(len(f.functions) for f in a.files) for a in analyses
        )
        total_exceptions = sum(
            sum(len(f.exceptions) for f in a.files) for a in analyses
        )

        # Count by language
        language_counts: Dict[str, int] = {}
        for analysis in analyses:
            for file_analysis in analysis.files:
                lang = file_analysis.language.value
                language_counts[lang] = language_counts.get(lang, 0) + 1

        return {
            "statistics": {
                "packages_analyzed": len(analyses),
                "files_analyzed": total_files,
                "classes_found": total_classes,
                "functions_found": total_functions,
                "exceptions_found": total_exceptions,
            },
            "languages": language_counts,
            "tools_used": [
                {"name": "FileDiscovery", "purpose": "Scan directories for source files"},
                {"name": "PythonAnalyzer", "purpose": "AST-based Python code analysis"},
                {"name": "JavaScriptAnalyzer", "purpose": "JavaScript/TypeScript code analysis"},
                {"name": "YamlSpecGenerator", "purpose": "Generate YAML specification"},
            ],
        }

    def _to_yaml(self, data: Dict[str, Any]) -> str:
        """Convert dictionary to YAML string with custom formatting."""
        # Custom representer for multiline strings
        def str_representer(dumper, data):
            if "\n" in data:
                return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
            return dumper.represent_scalar("tag:yaml.org,2002:str", data)

        yaml.add_representer(str, str_representer)

        return yaml.dump(
            data,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
            width=100,
        )
