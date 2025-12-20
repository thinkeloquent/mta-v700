"""
Python AST-based code analyzer.
"""

import ast
from pathlib import Path
from typing import List, Optional, Tuple

from .base import BaseAnalyzer
from ..models import (
    ClassInfo,
    ConstantInfo,
    ExceptionInfo,
    FieldInfo,
    FileAnalysis,
    FunctionInfo,
    ImportInfo,
    Language,
    Parameter,
    PatternType,
)


class PythonAnalyzer(BaseAnalyzer):
    """
    Analyzes Python source files using the built-in AST module.

    Extracts:
    - Classes with methods, fields, and decorators
    - Functions with signatures and decorators
    - Imports
    - Module-level constants
    - Custom exceptions
    - Design patterns (singleton, dataclass, etc.)
    """

    @property
    def supported_languages(self) -> list[Language]:
        return [Language.PYTHON]

    def analyze_file(self, path: Path) -> FileAnalysis:
        """Analyze a Python source file."""
        content = path.read_text(encoding="utf-8")

        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            # Return minimal analysis for files with syntax errors
            return FileAnalysis(
                path=str(path),
                language=Language.PYTHON,
                module_docstring=f"[Syntax Error: {e}]",
            )

        analysis = FileAnalysis(
            path=str(path),
            language=Language.PYTHON,
        )

        # Extract module docstring
        analysis.module_docstring = ast.get_docstring(tree)

        # Process top-level nodes
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                class_info = self._analyze_class(node)
                if self._is_exception_class(node):
                    analysis.exceptions.append(
                        ExceptionInfo(
                            name=class_info.name,
                            base=class_info.bases[0] if class_info.bases else "Exception",
                            docstring=class_info.docstring,
                            line_number=class_info.line_number,
                        )
                    )
                else:
                    analysis.classes.append(class_info)

            elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                analysis.functions.append(self._analyze_function(node))

            elif isinstance(node, ast.Import):
                for alias in node.names:
                    analysis.imports.append(
                        ImportInfo(
                            module=alias.name,
                            alias=alias.asname,
                            is_from_import=False,
                        )
                    )

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    names = [alias.name for alias in node.names]
                    analysis.imports.append(
                        ImportInfo(
                            module=node.module,
                            names=names,
                            is_from_import=True,
                        )
                    )

            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        const = self._analyze_constant(target, node.value, node.lineno)
                        if const:
                            analysis.constants.append(const)

            elif isinstance(node, ast.AnnAssign):
                if isinstance(node.target, ast.Name):
                    const = self._analyze_annotated_constant(node)
                    if const:
                        analysis.constants.append(const)

        # Extract __all__ exports
        analysis.exports = self._extract_exports(tree)

        return analysis

    def _analyze_class(self, node: ast.ClassDef) -> ClassInfo:
        """Analyze a class definition."""
        class_info = ClassInfo(
            name=node.name,
            line_number=node.lineno,
            docstring=ast.get_docstring(node),
        )

        # Extract base classes
        for base in node.bases:
            class_info.bases.append(self._get_name(base))

        # Extract decorators
        for decorator in node.decorator_list:
            class_info.decorators.append(self._get_name(decorator))

        # Detect patterns
        class_info.patterns = self._detect_patterns(node, class_info.decorators)

        # Analyze class body
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                class_info.methods.append(self._analyze_function(item))

            elif isinstance(item, ast.AnnAssign):
                field = self._analyze_class_field(item)
                if field:
                    class_info.fields.append(field)

            elif isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        field = FieldInfo(
                            name=target.id,
                            default_value=self._get_value_repr(item.value),
                            is_class_var=True,
                            line_number=item.lineno,
                        )
                        class_info.fields.append(field)

        return class_info

    def _analyze_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> FunctionInfo:
        """Analyze a function or method definition."""
        func_info = FunctionInfo(
            name=node.name,
            line_number=node.lineno,
            docstring=ast.get_docstring(node),
            is_async=isinstance(node, ast.AsyncFunctionDef),
        )

        # Extract decorators
        for decorator in node.decorator_list:
            dec_name = self._get_name(decorator)
            func_info.decorators.append(dec_name)
            if dec_name == "staticmethod":
                func_info.is_static = True
            elif dec_name == "classmethod":
                func_info.is_classmethod = True
            elif dec_name == "property":
                func_info.is_property = True

        # Extract parameters
        func_info.parameters = self._analyze_parameters(node.args)

        # Extract return type
        if node.returns:
            func_info.return_type = self._get_annotation(node.returns)

        return func_info

    def _analyze_parameters(self, args: ast.arguments) -> List[Parameter]:
        """Extract function parameters."""
        parameters = []

        # Calculate defaults offset
        num_args = len(args.args)
        num_defaults = len(args.defaults)
        defaults_offset = num_args - num_defaults

        for i, arg in enumerate(args.args):
            # Skip 'self' and 'cls'
            if arg.arg in ("self", "cls"):
                continue

            param = Parameter(
                name=arg.arg,
                type_annotation=self._get_annotation(arg.annotation) if arg.annotation else None,
            )

            # Check for default value
            default_idx = i - defaults_offset
            if default_idx >= 0 and default_idx < len(args.defaults):
                param.default_value = self._get_value_repr(args.defaults[default_idx])
                param.is_required = False

            parameters.append(param)

        # Handle *args
        if args.vararg:
            parameters.append(
                Parameter(
                    name=f"*{args.vararg.arg}",
                    type_annotation=self._get_annotation(args.vararg.annotation) if args.vararg.annotation else None,
                    is_required=False,
                )
            )

        # Handle keyword-only args
        kw_defaults = args.kw_defaults
        for i, arg in enumerate(args.kwonlyargs):
            param = Parameter(
                name=arg.arg,
                type_annotation=self._get_annotation(arg.annotation) if arg.annotation else None,
            )
            if i < len(kw_defaults) and kw_defaults[i] is not None:
                param.default_value = self._get_value_repr(kw_defaults[i])
                param.is_required = False
            parameters.append(param)

        # Handle **kwargs
        if args.kwarg:
            parameters.append(
                Parameter(
                    name=f"**{args.kwarg.arg}",
                    type_annotation=self._get_annotation(args.kwarg.annotation) if args.kwarg.annotation else None,
                    is_required=False,
                )
            )

        return parameters

    def _analyze_class_field(self, node: ast.AnnAssign) -> Optional[FieldInfo]:
        """Analyze a class field with type annotation."""
        if not isinstance(node.target, ast.Name):
            return None

        return FieldInfo(
            name=node.target.id,
            type_annotation=self._get_annotation(node.annotation),
            default_value=self._get_value_repr(node.value) if node.value else None,
            line_number=node.lineno,
        )

    def _analyze_constant(
        self, target: ast.Name, value: ast.expr, lineno: int
    ) -> Optional[ConstantInfo]:
        """Analyze a module-level constant assignment."""
        name = target.id

        # Check if it's likely a constant (UPPER_CASE or specific patterns)
        if not (name.isupper() or name.startswith("_") or name == "__all__"):
            return None

        return ConstantInfo(
            name=name,
            value=self._get_value_repr(value),
            line_number=lineno,
        )

    def _analyze_annotated_constant(self, node: ast.AnnAssign) -> Optional[ConstantInfo]:
        """Analyze an annotated constant."""
        if not isinstance(node.target, ast.Name):
            return None

        name = node.target.id

        return ConstantInfo(
            name=name,
            value=self._get_value_repr(node.value) if node.value else None,
            type_annotation=self._get_annotation(node.annotation),
            line_number=node.lineno,
        )

    def _detect_patterns(self, node: ast.ClassDef, decorators: List[str]) -> List[PatternType]:
        """Detect design patterns in a class."""
        patterns = []

        # Check decorators
        if "dataclass" in decorators:
            patterns.append(PatternType.DATACLASS)

        # Check for singleton pattern
        if self._has_singleton_pattern(node):
            patterns.append(PatternType.SINGLETON)

        # Check for abstract class
        for base in node.bases:
            base_name = self._get_name(base)
            if "ABC" in base_name or "Abstract" in base_name:
                patterns.append(PatternType.ABSTRACT)
                break

        # Check for abstractmethod decorators
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for dec in item.decorator_list:
                    if self._get_name(dec) == "abstractmethod":
                        if PatternType.ABSTRACT not in patterns:
                            patterns.append(PatternType.ABSTRACT)
                        break

        return patterns

    def _has_singleton_pattern(self, node: ast.ClassDef) -> bool:
        """Check if class implements singleton pattern."""
        has_instance_var = False
        has_get_instance = False
        has_new_override = False

        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        if target.id in ("_instance", "instance", "_singleton"):
                            has_instance_var = True

            elif isinstance(item, ast.AnnAssign):
                if isinstance(item.target, ast.Name):
                    if item.target.id in ("_instance", "instance", "_singleton"):
                        has_instance_var = True

            elif isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if item.name in ("get_instance", "getInstance", "instance"):
                    has_get_instance = True
                elif item.name == "__new__":
                    has_new_override = True

        return has_instance_var and (has_get_instance or has_new_override)

    def _is_exception_class(self, node: ast.ClassDef) -> bool:
        """Check if a class is an exception."""
        for base in node.bases:
            base_name = self._get_name(base)
            if "Exception" in base_name or "Error" in base_name:
                return True
        return False

    def _extract_exports(self, tree: ast.Module) -> List[str]:
        """Extract __all__ exports."""
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "__all__":
                        if isinstance(node.value, (ast.List, ast.Tuple)):
                            return [
                                elt.value
                                for elt in node.value.elts
                                if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                            ]
        return []

    def _get_name(self, node: ast.expr) -> str:
        """Get the name from various AST node types."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Call):
            return self._get_name(node.func)
        elif isinstance(node, ast.Subscript):
            return f"{self._get_name(node.value)}[{self._get_name(node.slice)}]"
        elif isinstance(node, ast.Constant):
            return repr(node.value)
        elif isinstance(node, ast.Tuple):
            return ", ".join(self._get_name(elt) for elt in node.elts)
        return "unknown"

    def _get_annotation(self, node: Optional[ast.expr]) -> Optional[str]:
        """Get type annotation as string."""
        if node is None:
            return None
        return self._get_name(node)

    def _get_value_repr(self, node: Optional[ast.expr]) -> Optional[str]:
        """Get a string representation of a value node."""
        if node is None:
            return None

        if isinstance(node, ast.Constant):
            return repr(node.value)
        elif isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.List):
            return "[...]"
        elif isinstance(node, ast.Dict):
            return "{...}"
        elif isinstance(node, ast.Set):
            return "{...}"
        elif isinstance(node, ast.Tuple):
            return "(...)"
        elif isinstance(node, ast.Call):
            return f"{self._get_name(node.func)}(...)"
        elif isinstance(node, ast.Attribute):
            return self._get_name(node)
        elif isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.USub):
                return f"-{self._get_value_repr(node.operand)}"
            return self._get_value_repr(node.operand)
        elif isinstance(node, ast.BinOp):
            return "..."

        return "..."
