import os
import ast
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

# Try importing tree_sitter, allow fallback if not installed/configured
try:
    from tree_sitter_languages import get_language, get_parser
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False


class FieldInfo(BaseModel):
    """Represents a class/dataclass field."""
    name: str
    type_annotation: Optional[str] = None
    default_value: Optional[str] = None
    is_required: bool = True


class ParameterInfo(BaseModel):
    """Represents a function parameter."""
    name: str
    type_annotation: Optional[str] = None
    default_value: Optional[str] = None


class MethodInfo(BaseModel):
    """Represents a method/function signature."""
    name: str
    parameters: List[ParameterInfo] = []
    return_type: Optional[str] = None
    is_async: bool = False
    is_classmethod: bool = False
    is_staticmethod: bool = False
    is_abstractmethod: bool = False
    decorators: List[str] = []
    docstring: Optional[str] = None
    line_number: int = 0


class ClassInfo(BaseModel):
    """Represents detailed class information."""
    name: str
    base_classes: List[str] = []
    decorators: List[str] = []
    fields: List[FieldInfo] = []
    methods: List[MethodInfo] = []
    is_dataclass: bool = False
    is_abstract: bool = False
    docstring: Optional[str] = None
    line_number: int = 0


class ValidationRule(BaseModel):
    """Represents an extracted validation rule."""
    function_name: str
    condition: str
    error_message: Optional[str] = None
    line_number: int = 0


class ASTNode(BaseModel):
    type: str
    name: Optional[str] = None
    content: Optional[str] = None
    start_point: tuple
    end_point: tuple
    children: List['ASTNode'] = []
    metadata: Dict[str, Any] = {}


class EnhancedAST(BaseModel):
    """Enhanced AST with extracted semantic information."""
    file_path: str
    language: str
    classes: List[ClassInfo] = []
    functions: List[MethodInfo] = []
    imports: List[str] = []
    exports: List[str] = []
    validation_rules: List[ValidationRule] = []
    exceptions: List[str] = []
    raw_ast: Optional[ASTNode] = None


class PolyglotParser:
    """
    Parses source code into a normalized AST using Tree-sitter if available,
    with enhanced semantic extraction for Python.
    """
    def __init__(self):
        self.parsers = {}
        if TREE_SITTER_AVAILABLE:
            try:
                # tree-sitter-languages provides pre-built parsers
                self.parsers['python'] = get_parser('python')
                self.parsers['javascript'] = get_parser('javascript')
                self.parsers['typescript'] = get_parser('typescript')
            except Exception as e:
                print(f"Warning: Failed to initialize some tree-sitter parsers: {e}")

    def parse_file(self, file_path: str, language: str) -> Optional[EnhancedAST]:
        """Parse a file and return enhanced AST with semantic information."""
        if language == 'python':
            return self._parse_python_enhanced(file_path)

        # Fallback for other languages
        if not TREE_SITTER_AVAILABLE:
            return self._basic_parse(file_path, language)

        parser = self.parsers.get(language)
        if not parser:
            return self._basic_parse(file_path, language)

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()

            tree = parser.parse(bytes(code, 'utf8'))
            raw_ast = self._normalize_node(tree.root_node, code)

            return EnhancedAST(
                file_path=file_path,
                language=language,
                raw_ast=raw_ast
            )
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return None

    def _parse_python_enhanced(self, file_path: str) -> Optional[EnhancedAST]:
        """Enhanced Python parsing using the ast module."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()

            tree = ast.parse(code)

            enhanced = EnhancedAST(
                file_path=file_path,
                language='python'
            )

            # Extract imports
            enhanced.imports = self._extract_imports(tree)

            # Extract classes with full details
            enhanced.classes = self._extract_classes(tree, code)

            # Extract top-level functions
            enhanced.functions = self._extract_functions(tree, code)

            # Extract validation rules
            enhanced.validation_rules = self._extract_validations(tree, code)

            # Extract exception definitions
            enhanced.exceptions = self._extract_exceptions(tree)

            # Convert to raw AST for backward compatibility
            enhanced.raw_ast = self._convert_py_ast(tree)

            return enhanced

        except SyntaxError as e:
            print(f"Syntax error in {file_path}: {e}")
            return None
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return None

    def _extract_imports(self, tree: ast.Module) -> List[str]:
        """Extract import statements."""
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}")
        return imports

    def _extract_classes(self, tree: ast.Module, code: str) -> List[ClassInfo]:
        """Extract detailed class information."""
        classes = []

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                class_info = self._analyze_class(node, code)
                classes.append(class_info)

        return classes

    def _analyze_class(self, node: ast.ClassDef, code: str) -> ClassInfo:
        """Analyze a class definition in detail."""
        # Extract decorators
        decorators = []
        is_dataclass = False
        for dec in node.decorator_list:
            dec_name = self._get_decorator_name(dec)
            decorators.append(dec_name)
            if 'dataclass' in dec_name.lower():
                is_dataclass = True

        # Extract base classes
        base_classes = []
        is_abstract = False
        for base in node.bases:
            base_name = self._get_name(base)
            base_classes.append(base_name)
            if base_name in ('ABC', 'ABCMeta'):
                is_abstract = True

        # Extract docstring
        docstring = ast.get_docstring(node)

        # Extract fields (class attributes with type annotations)
        fields = self._extract_class_fields(node, is_dataclass)

        # Extract methods
        methods = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method_info = self._analyze_function(item, code)
                methods.append(method_info)

        return ClassInfo(
            name=node.name,
            base_classes=base_classes,
            decorators=decorators,
            fields=fields,
            methods=methods,
            is_dataclass=is_dataclass,
            is_abstract=is_abstract,
            docstring=docstring,
            line_number=node.lineno
        )

    def _extract_class_fields(self, node: ast.ClassDef, is_dataclass: bool) -> List[FieldInfo]:
        """Extract class fields with type annotations."""
        fields = []

        for item in node.body:
            # Annotated assignments (field: type = value)
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                field = FieldInfo(
                    name=item.target.id,
                    type_annotation=self._get_type_annotation(item.annotation),
                    default_value=self._get_value_repr(item.value) if item.value else None,
                    is_required=item.value is None
                )
                fields.append(field)

            # For dataclasses, also check field() calls
            if is_dataclass and isinstance(item, ast.AnnAssign):
                if item.value and isinstance(item.value, ast.Call):
                    func_name = self._get_name(item.value.func)
                    if func_name == 'field':
                        # Extract default_factory if present
                        for kw in item.value.keywords:
                            if kw.arg == 'default_factory':
                                field_idx = len(fields) - 1
                                if field_idx >= 0:
                                    fields[field_idx].default_value = f"factory:{self._get_name(kw.value)}"
                                    fields[field_idx].is_required = False

        return fields

    def _extract_functions(self, tree: ast.Module, code: str) -> List[MethodInfo]:
        """Extract top-level function definitions."""
        functions = []

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_info = self._analyze_function(node, code)
                functions.append(func_info)

        return functions

    def _analyze_function(self, node, code: str) -> MethodInfo:
        """Analyze a function/method definition."""
        is_async = isinstance(node, ast.AsyncFunctionDef)

        # Extract decorators
        decorators = []
        is_classmethod = False
        is_staticmethod = False
        is_abstractmethod = False

        for dec in node.decorator_list:
            dec_name = self._get_decorator_name(dec)
            decorators.append(dec_name)
            if dec_name == 'classmethod':
                is_classmethod = True
            elif dec_name == 'staticmethod':
                is_staticmethod = True
            elif dec_name == 'abstractmethod':
                is_abstractmethod = True

        # Extract parameters
        parameters = []
        for arg in node.args.args:
            if arg.arg == 'self' or arg.arg == 'cls':
                continue
            param = ParameterInfo(
                name=arg.arg,
                type_annotation=self._get_type_annotation(arg.annotation) if arg.annotation else None
            )
            parameters.append(param)

        # Extract return type
        return_type = self._get_type_annotation(node.returns) if node.returns else None

        # Extract docstring
        docstring = ast.get_docstring(node)

        return MethodInfo(
            name=node.name,
            parameters=parameters,
            return_type=return_type,
            is_async=is_async,
            is_classmethod=is_classmethod,
            is_staticmethod=is_staticmethod,
            is_abstractmethod=is_abstractmethod,
            decorators=decorators,
            docstring=docstring,
            line_number=node.lineno
        )

    def _extract_validations(self, tree: ast.Module, code: str) -> List[ValidationRule]:
        """Extract validation rules from conditionals and raise statements."""
        validations = []
        code_lines = code.split('\n')

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_name = node.name

                # Walk function body for if statements with raises
                for child in ast.walk(node):
                    if isinstance(child, ast.If):
                        # Check if this if has a raise in its body
                        has_raise = any(isinstance(n, ast.Raise) for n in ast.walk(child))
                        if has_raise:
                            # Extract the condition
                            try:
                                condition = ast.unparse(child.test)
                            except:
                                condition = self._get_source_segment(code_lines, child.test)

                            # Try to get error message
                            error_msg = None
                            for n in ast.walk(child):
                                if isinstance(n, ast.Raise) and n.exc:
                                    if isinstance(n.exc, ast.Call) and n.exc.args:
                                        try:
                                            error_msg = ast.unparse(n.exc.args[0])
                                        except:
                                            pass

                            validations.append(ValidationRule(
                                function_name=func_name,
                                condition=condition,
                                error_message=error_msg,
                                line_number=child.lineno
                            ))

        return validations

    def _extract_exceptions(self, tree: ast.Module) -> List[str]:
        """Extract custom exception class names."""
        exceptions = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check if inherits from Exception or Error
                for base in node.bases:
                    base_name = self._get_name(base)
                    if 'Exception' in base_name or 'Error' in base_name:
                        exceptions.append(node.name)
                        break

        return exceptions

    def _get_decorator_name(self, dec) -> str:
        """Get decorator name as string."""
        if isinstance(dec, ast.Name):
            return dec.id
        elif isinstance(dec, ast.Call):
            return self._get_name(dec.func)
        elif isinstance(dec, ast.Attribute):
            return f"{self._get_name(dec.value)}.{dec.attr}"
        return str(dec)

    def _get_name(self, node) -> str:
        """Get name from various node types."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Subscript):
            return f"{self._get_name(node.value)}[{self._get_name(node.slice)}]"
        elif isinstance(node, ast.Constant):
            return str(node.value)
        elif isinstance(node, ast.Tuple):
            return ', '.join(self._get_name(e) for e in node.elts)
        return str(type(node).__name__)

    def _get_type_annotation(self, node) -> Optional[str]:
        """Convert type annotation node to string."""
        if node is None:
            return None
        try:
            return ast.unparse(node)
        except:
            return self._get_name(node)

    def _get_value_repr(self, node) -> Optional[str]:
        """Get string representation of a value node."""
        if node is None:
            return None
        try:
            return ast.unparse(node)
        except:
            if isinstance(node, ast.Constant):
                return repr(node.value)
            return str(type(node).__name__)

    def _get_source_segment(self, code_lines: List[str], node) -> str:
        """Get source code for a node."""
        try:
            return code_lines[node.lineno - 1][node.col_offset:].strip()
        except:
            return ""

    def _normalize_node(self, node, code: str) -> ASTNode:
        """Normalize tree-sitter node to ASTNode."""
        name = None

        if node.type in ['function_definition', 'class_definition', 'function_declaration', 'class_declaration']:
            for child in node.children:
                if child.type == 'identifier':
                    name = code[child.start_byte:child.end_byte]
                    break
        elif node.type == 'identifier':
            name = code[node.start_byte:node.end_byte]

        children = [self._normalize_node(child, code) for child in node.children]

        return ASTNode(
            type=node.type,
            name=name,
            start_point=node.start_point,
            end_point=node.end_point,
            children=children
        )

    def _basic_parse(self, file_path: str, language: str) -> EnhancedAST:
        """Basic fallback parse."""
        return EnhancedAST(
            file_path=file_path,
            language=language,
            raw_ast=ASTNode(
                type="file",
                name=os.path.basename(file_path),
                start_point=(0, 0),
                end_point=(0, 0),
                metadata={"status": "basic_parse"}
            )
        )

    def _convert_py_ast(self, node) -> ASTNode:
        """Convert Python AST to ASTNode for backward compatibility."""
        name = getattr(node, 'name', None)
        node_type = type(node).__name__
        children = []
        metadata = {}

        if hasattr(node, 'decorator_list'):
            decorators = []
            for d in node.decorator_list:
                decorators.append(self._get_decorator_name(d))
            if decorators:
                metadata['decorators'] = decorators

        for field, value in ast.iter_fields(node):
            if field == 'decorator_list':
                continue
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, ast.AST):
                        children.append(self._convert_py_ast(item))
            elif isinstance(value, ast.AST):
                children.append(self._convert_py_ast(value))

        return ASTNode(
            type=node_type,
            name=name,
            start_point=(getattr(node, 'lineno', 0), getattr(node, 'col_offset', 0)),
            end_point=(getattr(node, 'end_lineno', 0), getattr(node, 'end_col_offset', 0)),
            children=children,
            metadata=metadata
        )
