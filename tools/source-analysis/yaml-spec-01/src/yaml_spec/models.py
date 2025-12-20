"""
Data models for code analysis results.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class Language(Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    UNKNOWN = "unknown"


class PatternType(Enum):
    SINGLETON = "singleton"
    FACTORY = "factory"
    DATACLASS = "dataclass"
    ABSTRACT = "abstract"
    INTERFACE = "interface"
    MIXIN = "mixin"


@dataclass
class Parameter:
    """Function/method parameter."""
    name: str
    type_annotation: Optional[str] = None
    default_value: Optional[str] = None
    is_required: bool = True

    def to_dict(self) -> Dict[str, Any]:
        result = {"name": self.name, "required": self.is_required}
        if self.type_annotation:
            result["type"] = self.type_annotation
        if self.default_value:
            result["default"] = self.default_value
        return result


@dataclass
class FunctionInfo:
    """Information about a function or method."""
    name: str
    parameters: List[Parameter] = field(default_factory=list)
    return_type: Optional[str] = None
    decorators: List[str] = field(default_factory=list)
    docstring: Optional[str] = None
    is_async: bool = False
    is_static: bool = False
    is_classmethod: bool = False
    is_property: bool = False
    line_number: int = 0

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "name": self.name,
            "line": self.line_number,
        }
        if self.parameters:
            result["parameters"] = [p.to_dict() for p in self.parameters]
        if self.return_type:
            result["returns"] = self.return_type
        if self.decorators:
            result["decorators"] = self.decorators
        if self.docstring:
            result["description"] = self.docstring.split('\n')[0].strip()
        if self.is_async:
            result["async"] = True
        if self.is_static:
            result["static"] = True
        if self.is_classmethod:
            result["classmethod"] = True
        if self.is_property:
            result["property"] = True
        return result


@dataclass
class FieldInfo:
    """Information about a class field/attribute."""
    name: str
    type_annotation: Optional[str] = None
    default_value: Optional[str] = None
    is_class_var: bool = False
    line_number: int = 0

    def to_dict(self) -> Dict[str, Any]:
        result = {"name": self.name}
        if self.type_annotation:
            result["type"] = self.type_annotation
        if self.default_value:
            result["default"] = self.default_value
        if self.is_class_var:
            result["class_variable"] = True
        return result


@dataclass
class ClassInfo:
    """Information about a class."""
    name: str
    bases: List[str] = field(default_factory=list)
    decorators: List[str] = field(default_factory=list)
    methods: List[FunctionInfo] = field(default_factory=list)
    fields: List[FieldInfo] = field(default_factory=list)
    docstring: Optional[str] = None
    patterns: List[PatternType] = field(default_factory=list)
    line_number: int = 0

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "name": self.name,
            "line": self.line_number,
        }
        if self.bases:
            result["extends"] = self.bases
        if self.decorators:
            result["decorators"] = self.decorators
        if self.docstring:
            result["description"] = self.docstring.split('\n')[0].strip()
        if self.patterns:
            result["patterns"] = [p.value for p in self.patterns]
        if self.fields:
            result["fields"] = [f.to_dict() for f in self.fields]
        if self.methods:
            result["methods"] = [m.to_dict() for m in self.methods]
        return result


@dataclass
class ImportInfo:
    """Information about an import statement."""
    module: str
    names: List[str] = field(default_factory=list)
    alias: Optional[str] = None
    is_from_import: bool = False

    def to_dict(self) -> Dict[str, Any]:
        if self.is_from_import:
            return {"from": self.module, "import": self.names}
        return {"import": self.module, "alias": self.alias} if self.alias else {"import": self.module}


@dataclass
class ConstantInfo:
    """Information about a module-level constant."""
    name: str
    value: Optional[str] = None
    type_annotation: Optional[str] = None
    line_number: int = 0

    def to_dict(self) -> Dict[str, Any]:
        result = {"name": self.name}
        if self.value:
            result["value"] = self.value
        if self.type_annotation:
            result["type"] = self.type_annotation
        return result


@dataclass
class ExceptionInfo:
    """Information about a custom exception class."""
    name: str
    base: str = "Exception"
    docstring: Optional[str] = None
    line_number: int = 0

    def to_dict(self) -> Dict[str, Any]:
        result = {"name": self.name, "extends": self.base}
        if self.docstring:
            result["description"] = self.docstring.split('\n')[0].strip()
        return result


@dataclass
class FileAnalysis:
    """Complete analysis of a single file."""
    path: str
    language: Language
    imports: List[ImportInfo] = field(default_factory=list)
    classes: List[ClassInfo] = field(default_factory=list)
    functions: List[FunctionInfo] = field(default_factory=list)
    constants: List[ConstantInfo] = field(default_factory=list)
    exceptions: List[ExceptionInfo] = field(default_factory=list)
    exports: List[str] = field(default_factory=list)
    module_docstring: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "path": self.path,
            "language": self.language.value,
        }
        if self.module_docstring:
            result["description"] = self.module_docstring.split('\n')[0].strip()
        if self.imports:
            result["imports"] = [i.to_dict() for i in self.imports]
        if self.classes:
            result["classes"] = [c.to_dict() for c in self.classes]
        if self.functions:
            result["functions"] = [f.to_dict() for f in self.functions]
        if self.constants:
            result["constants"] = [c.to_dict() for c in self.constants]
        if self.exceptions:
            result["exceptions"] = [e.to_dict() for e in self.exceptions]
        if self.exports:
            result["exports"] = self.exports
        return result


@dataclass
class PackageAnalysis:
    """Complete analysis of a package/directory."""
    name: str
    path: str
    files: List[FileAnalysis] = field(default_factory=list)
    dependencies: Dict[str, str] = field(default_factory=dict)
    version: Optional[str] = None
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "name": self.name,
            "path": self.path,
        }
        if self.version:
            result["version"] = self.version
        if self.description:
            result["description"] = self.description
        if self.dependencies:
            result["dependencies"] = self.dependencies
        if self.files:
            result["files"] = [f.to_dict() for f in self.files]
        return result
