"""
JavaScript/TypeScript code analyzer.

Uses esprima for parsing when available, falls back to regex-based analysis.
"""

import re
from pathlib import Path
from typing import List, Optional, Dict, Any

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


class JavaScriptAnalyzer(BaseAnalyzer):
    """
    Analyzes JavaScript and TypeScript source files.

    Attempts to use esprima for accurate parsing.
    Falls back to regex-based analysis if esprima is not available.
    """

    def __init__(self):
        self._esprima = None
        try:
            import esprima
            self._esprima = esprima
        except ImportError:
            pass

    @property
    def supported_languages(self) -> list[Language]:
        return [Language.JAVASCRIPT, Language.TYPESCRIPT]

    def analyze_file(self, path: Path) -> FileAnalysis:
        """Analyze a JavaScript/TypeScript source file."""
        content = path.read_text(encoding="utf-8")
        language = Language.TYPESCRIPT if path.suffix in (".ts", ".tsx", ".mts", ".cts") else Language.JAVASCRIPT

        analysis = FileAnalysis(
            path=str(path),
            language=language,
        )

        if self._esprima and language == Language.JAVASCRIPT:
            return self._analyze_with_esprima(content, analysis)
        else:
            return self._analyze_with_regex(content, analysis)

    def _analyze_with_esprima(self, content: str, analysis: FileAnalysis) -> FileAnalysis:
        """Analyze using esprima parser."""
        try:
            tree = self._esprima.parseModule(content, {"jsx": True, "tolerant": True, "comment": True})
            return self._process_esprima_tree(tree, analysis)
        except Exception:
            # Fall back to regex on parse error
            return self._analyze_with_regex(content, analysis)

    def _process_esprima_tree(self, tree: Any, analysis: FileAnalysis) -> FileAnalysis:
        """Process esprima AST."""
        for node in tree.body:
            node_type = node.type

            if node_type == "ImportDeclaration":
                analysis.imports.append(self._parse_import_node(node))

            elif node_type == "ExportNamedDeclaration":
                if node.declaration:
                    self._process_declaration(node.declaration, analysis, exported=True)

            elif node_type == "ExportDefaultDeclaration":
                if node.declaration:
                    self._process_declaration(node.declaration, analysis, exported=True)

            elif node_type == "ClassDeclaration":
                analysis.classes.append(self._parse_class_node(node))

            elif node_type == "FunctionDeclaration":
                analysis.functions.append(self._parse_function_node(node))

            elif node_type == "VariableDeclaration":
                self._process_variable_declaration(node, analysis)

        return analysis

    def _parse_import_node(self, node: Any) -> ImportInfo:
        """Parse an import declaration."""
        source = node.source.value
        names = []

        for spec in node.specifiers:
            if spec.type == "ImportDefaultSpecifier":
                names.append("default")
            elif spec.type == "ImportNamespaceSpecifier":
                names.append("*")
            else:
                names.append(spec.imported.name if hasattr(spec, "imported") else spec.local.name)

        return ImportInfo(
            module=source,
            names=names,
            is_from_import=True,
        )

    def _parse_class_node(self, node: Any) -> ClassInfo:
        """Parse a class declaration."""
        class_info = ClassInfo(
            name=node.id.name if node.id else "anonymous",
            line_number=node.loc.start.line if hasattr(node, "loc") else 0,
        )

        if node.superClass:
            class_info.bases.append(self._get_node_name(node.superClass))

        # Parse class body
        for item in node.body.body:
            if item.type == "MethodDefinition":
                method = self._parse_method_node(item)
                class_info.methods.append(method)
            elif item.type in ("PropertyDefinition", "ClassProperty"):
                field = self._parse_property_node(item)
                if field:
                    class_info.fields.append(field)

        # Detect patterns
        class_info.patterns = self._detect_js_patterns(class_info)

        return class_info

    def _parse_function_node(self, node: Any) -> FunctionInfo:
        """Parse a function declaration."""
        return FunctionInfo(
            name=node.id.name if node.id else "anonymous",
            is_async=getattr(node, "async", False),
            parameters=self._parse_params(node.params),
            line_number=node.loc.start.line if hasattr(node, "loc") else 0,
        )

    def _parse_method_node(self, node: Any) -> FunctionInfo:
        """Parse a method definition."""
        name = self._get_node_name(node.key) if node.key else "anonymous"

        return FunctionInfo(
            name=name,
            is_async=getattr(node.value, "async", False) if node.value else False,
            is_static=getattr(node, "static", False),
            is_property=node.kind == "get" or node.kind == "set",
            parameters=self._parse_params(node.value.params) if node.value else [],
            line_number=node.loc.start.line if hasattr(node, "loc") else 0,
        )

    def _parse_property_node(self, node: Any) -> Optional[FieldInfo]:
        """Parse a class property."""
        name = self._get_node_name(node.key) if node.key else None
        if not name:
            return None

        return FieldInfo(
            name=name,
            is_class_var=getattr(node, "static", False),
            default_value=self._get_value_repr(node.value) if node.value else None,
            line_number=node.loc.start.line if hasattr(node, "loc") else 0,
        )

    def _parse_params(self, params: List[Any]) -> List[Parameter]:
        """Parse function parameters."""
        result = []
        for param in params:
            if param.type == "Identifier":
                result.append(Parameter(name=param.name))
            elif param.type == "AssignmentPattern":
                result.append(Parameter(
                    name=self._get_node_name(param.left),
                    default_value=self._get_value_repr(param.right),
                    is_required=False,
                ))
            elif param.type == "RestElement":
                result.append(Parameter(
                    name=f"...{self._get_node_name(param.argument)}",
                    is_required=False,
                ))
            elif param.type == "ObjectPattern":
                result.append(Parameter(name="{...}", is_required=True))
            elif param.type == "ArrayPattern":
                result.append(Parameter(name="[...]", is_required=True))
        return result

    def _process_declaration(self, node: Any, analysis: FileAnalysis, exported: bool = False):
        """Process a declaration node."""
        if node.type == "ClassDeclaration":
            class_info = self._parse_class_node(node)
            if exported:
                analysis.exports.append(class_info.name)
            analysis.classes.append(class_info)
        elif node.type == "FunctionDeclaration":
            func_info = self._parse_function_node(node)
            if exported:
                analysis.exports.append(func_info.name)
            analysis.functions.append(func_info)
        elif node.type == "VariableDeclaration":
            self._process_variable_declaration(node, analysis, exported)

    def _process_variable_declaration(self, node: Any, analysis: FileAnalysis, exported: bool = False):
        """Process variable declarations."""
        for decl in node.declarations:
            if decl.id.type == "Identifier":
                name = decl.id.name
                if exported:
                    analysis.exports.append(name)
                # Check if it's a constant (const + UPPER_CASE)
                if node.kind == "const" and name.isupper():
                    analysis.constants.append(ConstantInfo(
                        name=name,
                        value=self._get_value_repr(decl.init) if decl.init else None,
                    ))

    def _get_node_name(self, node: Any) -> str:
        """Get name from various node types."""
        if node is None:
            return "unknown"
        if hasattr(node, "name"):
            return node.name
        if hasattr(node, "type"):
            if node.type == "Identifier":
                return node.name
            elif node.type == "MemberExpression":
                obj = self._get_node_name(node.object)
                prop = self._get_node_name(node.property)
                return f"{obj}.{prop}"
        return "unknown"

    def _get_value_repr(self, node: Any) -> Optional[str]:
        """Get string representation of a value."""
        if node is None:
            return None
        if hasattr(node, "type"):
            if node.type == "Literal":
                return repr(node.value)
            elif node.type == "Identifier":
                return node.name
            elif node.type == "ArrayExpression":
                return "[...]"
            elif node.type == "ObjectExpression":
                return "{...}"
            elif node.type == "ArrowFunctionExpression":
                return "() => {...}"
            elif node.type == "FunctionExpression":
                return "function() {...}"
            elif node.type == "CallExpression":
                return f"{self._get_node_name(node.callee)}(...)"
            elif node.type == "NewExpression":
                return f"new {self._get_node_name(node.callee)}(...)"
        return "..."

    def _detect_js_patterns(self, class_info: ClassInfo) -> List[PatternType]:
        """Detect patterns in JS class."""
        patterns = []

        # Check for singleton
        has_instance = any(f.name in ("instance", "_instance") for f in class_info.fields)
        has_get_instance = any(m.name in ("getInstance", "get_instance") for m in class_info.methods)
        if has_instance and has_get_instance:
            patterns.append(PatternType.SINGLETON)

        return patterns

    # =========================================================================
    # Regex-based fallback analysis
    # =========================================================================

    def _analyze_with_regex(self, content: str, analysis: FileAnalysis) -> FileAnalysis:
        """Analyze using regex patterns (fallback for TypeScript or when esprima unavailable)."""

        # Extract imports
        analysis.imports = self._extract_imports_regex(content)

        # Extract classes
        analysis.classes = self._extract_classes_regex(content)

        # Extract functions
        analysis.functions = self._extract_functions_regex(content)

        # Extract constants
        analysis.constants = self._extract_constants_regex(content)

        # Extract exports
        analysis.exports = self._extract_exports_regex(content)

        # Extract exceptions (error classes)
        analysis.exceptions = self._extract_exceptions_regex(content)

        return analysis

    def _extract_imports_regex(self, content: str) -> List[ImportInfo]:
        """Extract imports using regex."""
        imports = []

        # ES6 imports: import { x, y } from 'module'
        pattern = r"import\s+(?:\{([^}]+)\}|(\w+)|\*\s+as\s+(\w+))\s+from\s+['\"]([^'\"]+)['\"]"
        for match in re.finditer(pattern, content):
            named, default, namespace, module = match.groups()
            names = []
            if named:
                names = [n.strip().split(" as ")[0].strip() for n in named.split(",")]
            elif default:
                names = ["default"]
            elif namespace:
                names = ["*"]

            imports.append(ImportInfo(
                module=module,
                names=names,
                is_from_import=True,
            ))

        # require() imports
        pattern = r"(?:const|let|var)\s+(?:\{([^}]+)\}|(\w+))\s*=\s*require\(['\"]([^'\"]+)['\"]\)"
        for match in re.finditer(pattern, content):
            destructured, name, module = match.groups()
            names = []
            if destructured:
                names = [n.strip() for n in destructured.split(",")]
            elif name:
                names = [name]

            imports.append(ImportInfo(
                module=module,
                names=names,
                is_from_import=False,
            ))

        return imports

    def _extract_classes_regex(self, content: str) -> List[ClassInfo]:
        """Extract classes using regex."""
        classes = []

        # Class pattern: class Name extends Base { ... }
        pattern = r"(?:export\s+)?class\s+(\w+)(?:\s+extends\s+(\w+(?:\.\w+)*))?\s*\{"

        for match in re.finditer(pattern, content):
            name, base = match.groups()

            class_info = ClassInfo(
                name=name,
                bases=[base] if base else [],
                line_number=content[:match.start()].count("\n") + 1,
            )

            # Find class body and extract methods/fields
            class_body = self._extract_block(content, match.end() - 1)
            if class_body:
                class_info.methods = self._extract_class_methods_regex(class_body)
                class_info.fields = self._extract_class_fields_regex(class_body)
                class_info.patterns = self._detect_js_patterns(class_info)

            classes.append(class_info)

        return classes

    def _extract_class_methods_regex(self, class_body: str) -> List[FunctionInfo]:
        """Extract methods from class body."""
        methods = []

        # Method pattern: async? static? methodName(params) { ... }
        pattern = r"(async\s+)?(static\s+)?(\w+)\s*\(([^)]*)\)\s*\{"

        for match in re.finditer(pattern, class_body):
            is_async, is_static, name, params = match.groups()

            # Skip constructor for now
            if name == "constructor":
                continue

            method = FunctionInfo(
                name=name,
                is_async=bool(is_async),
                is_static=bool(is_static),
                parameters=self._parse_params_regex(params),
                line_number=class_body[:match.start()].count("\n") + 1,
            )
            methods.append(method)

        return methods

    def _extract_class_fields_regex(self, class_body: str) -> List[FieldInfo]:
        """Extract fields from class body."""
        fields = []

        # Field pattern: static? fieldName = value; or fieldName: type = value;
        pattern = r"(static\s+)?(\w+)\s*(?::\s*([^=;\n]+))?\s*(?:=\s*([^;\n]+))?\s*;"

        for match in re.finditer(pattern, class_body):
            is_static, name, type_ann, value = match.groups()

            # Skip if it looks like a method
            if name in ("async", "static", "get", "set"):
                continue

            field = FieldInfo(
                name=name,
                is_class_var=bool(is_static),
                type_annotation=type_ann.strip() if type_ann else None,
                default_value=value.strip() if value else None,
            )
            fields.append(field)

        return fields

    def _extract_functions_regex(self, content: str) -> List[FunctionInfo]:
        """Extract top-level functions using regex."""
        functions = []

        # Function declarations: async? function name(params) { ... }
        pattern = r"(?:export\s+)?(async\s+)?function\s+(\w+)\s*\(([^)]*)\)"

        for match in re.finditer(pattern, content):
            is_async, name, params = match.groups()

            func = FunctionInfo(
                name=name,
                is_async=bool(is_async),
                parameters=self._parse_params_regex(params),
                line_number=content[:match.start()].count("\n") + 1,
            )
            functions.append(func)

        # Arrow functions assigned to const: const name = async? (params) => { ... }
        pattern = r"(?:export\s+)?const\s+(\w+)\s*=\s*(async\s+)?\(([^)]*)\)\s*=>"

        for match in re.finditer(pattern, content):
            name, is_async, params = match.groups()

            func = FunctionInfo(
                name=name,
                is_async=bool(is_async),
                parameters=self._parse_params_regex(params),
                line_number=content[:match.start()].count("\n") + 1,
            )
            functions.append(func)

        return functions

    def _extract_constants_regex(self, content: str) -> List[ConstantInfo]:
        """Extract constants using regex."""
        constants = []

        # UPPER_CASE constants
        pattern = r"(?:export\s+)?const\s+([A-Z][A-Z0-9_]*)\s*(?::\s*([^=]+))?\s*=\s*([^;\n]+)"

        for match in re.finditer(pattern, content):
            name, type_ann, value = match.groups()

            constants.append(ConstantInfo(
                name=name,
                type_annotation=type_ann.strip() if type_ann else None,
                value=value.strip(),
                line_number=content[:match.start()].count("\n") + 1,
            ))

        return constants

    def _extract_exports_regex(self, content: str) -> List[str]:
        """Extract export names."""
        exports = []

        # export { name1, name2 }
        pattern = r"export\s+\{([^}]+)\}"
        for match in re.finditer(pattern, content):
            names = [n.strip().split(" as ")[0].strip() for n in match.group(1).split(",")]
            exports.extend(names)

        # export const/function/class name
        pattern = r"export\s+(?:default\s+)?(?:const|let|var|function|class)\s+(\w+)"
        for match in re.finditer(pattern, content):
            exports.append(match.group(1))

        return exports

    def _extract_exceptions_regex(self, content: str) -> List[ExceptionInfo]:
        """Extract custom error classes."""
        exceptions = []

        # class SomeError extends Error
        pattern = r"class\s+(\w*Error\w*)\s+extends\s+(Error|[A-Z]\w*Error)"

        for match in re.finditer(pattern, content):
            name, base = match.groups()
            exceptions.append(ExceptionInfo(
                name=name,
                base=base,
                line_number=content[:match.start()].count("\n") + 1,
            ))

        return exceptions

    def _parse_params_regex(self, params_str: str) -> List[Parameter]:
        """Parse parameter string."""
        if not params_str.strip():
            return []

        params = []
        # Split by comma, but handle nested structures
        depth = 0
        current = ""
        for char in params_str:
            if char in "([{":
                depth += 1
            elif char in ")]}":
                depth -= 1
            elif char == "," and depth == 0:
                if current.strip():
                    params.append(self._parse_single_param(current.strip()))
                current = ""
                continue
            current += char

        if current.strip():
            params.append(self._parse_single_param(current.strip()))

        return params

    def _parse_single_param(self, param: str) -> Parameter:
        """Parse a single parameter."""
        # Handle destructuring
        if param.startswith("{"):
            return Parameter(name="{...}", is_required=True)
        if param.startswith("["):
            return Parameter(name="[...]", is_required=True)

        # Handle rest params
        if param.startswith("..."):
            name = param[3:].split(":")[0].strip()
            return Parameter(name=f"...{name}", is_required=False)

        # Handle default values
        if "=" in param:
            parts = param.split("=", 1)
            name_type = parts[0].strip()
            default = parts[1].strip()

            # Extract name and type
            if ":" in name_type:
                name, type_ann = name_type.split(":", 1)
                return Parameter(
                    name=name.strip(),
                    type_annotation=type_ann.strip(),
                    default_value=default,
                    is_required=False,
                )
            return Parameter(name=name_type, default_value=default, is_required=False)

        # Handle typed params
        if ":" in param:
            name, type_ann = param.split(":", 1)
            return Parameter(name=name.strip(), type_annotation=type_ann.strip())

        return Parameter(name=param)

    def _extract_block(self, content: str, start_pos: int) -> Optional[str]:
        """Extract a brace-delimited block starting at start_pos."""
        if start_pos >= len(content) or content[start_pos] != "{":
            return None

        depth = 0
        end_pos = start_pos

        for i in range(start_pos, len(content)):
            if content[i] == "{":
                depth += 1
            elif content[i] == "}":
                depth -= 1
                if depth == 0:
                    end_pos = i
                    break

        return content[start_pos + 1:end_pos]
