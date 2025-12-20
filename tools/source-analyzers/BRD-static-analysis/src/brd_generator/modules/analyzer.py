from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from .parser import EnhancedAST, ClassInfo, MethodInfo, FieldInfo, ValidationRule, ASTNode
from .discovery import SourceFile, FileType


class DataModelField(BaseModel):
    """Represents a field in a data model."""
    name: str
    type: str
    required: bool = True
    default: Optional[str] = None
    description: Optional[str] = None


class DataModel(BaseModel):
    """Represents a data model/entity."""
    name: str
    source_file: str
    line_number: int = 0
    fields: List[DataModelField] = []
    base_classes: List[str] = []
    is_dataclass: bool = False
    is_abstract: bool = False
    docstring: Optional[str] = None


class APIMethod(BaseModel):
    """Represents a public API method."""
    name: str
    source_file: str
    class_name: Optional[str] = None
    parameters: List[Dict[str, str]] = []
    return_type: Optional[str] = None
    is_async: bool = False
    is_classmethod: bool = False
    is_abstractmethod: bool = False
    docstring: Optional[str] = None
    line_number: int = 0


class ValidationConstraint(BaseModel):
    """Represents a validation/business rule."""
    id: str
    title: str
    description: str
    condition: str
    error_message: Optional[str] = None
    source_file: str
    function_name: str
    line_number: int = 0


class BusinessFeature(BaseModel):
    """Legacy feature type for backward compatibility."""
    name: str
    type: str  # API Endpoint, Model, Constraint, Entity
    description: Optional[str] = None
    source_file: str
    code_ref: Optional[str] = None
    metadata: Dict[str, Any] = {}


class ProjectAnalysis(BaseModel):
    """Complete project analysis results."""
    project_name: str
    files_analyzed: int

    # Enhanced structured data
    data_models: List[DataModel] = []
    api_methods: List[APIMethod] = []
    validation_rules: List[ValidationConstraint] = []
    exceptions: List[str] = []
    imports: Dict[str, List[str]] = {}

    # Legacy features for backward compatibility
    features: List[BusinessFeature] = []

    # Metadata
    reasoning: Dict[str, Any] = {}
    key_capabilities: List[str] = []


class SemanticAnalyzer:
    """
    Identifies Business Blocks from EnhancedAST with detailed extraction.
    """
    def __init__(self):
        self.constraint_counter = 0

    def analyze(self, source_file: SourceFile, ast: EnhancedAST) -> Dict[str, Any]:
        """
        Analyze a source file and return structured results.
        Returns a dict with data_models, api_methods, validation_rules, etc.
        """
        results = {
            'data_models': [],
            'api_methods': [],
            'validation_rules': [],
            'exceptions': [],
            'imports': [],
            'features': []  # Legacy
        }

        if not ast:
            return results

        # Extract from enhanced AST
        if ast.classes:
            for cls in ast.classes:
                # Data models
                if cls.is_dataclass or cls.fields or self._is_entity_class(cls):
                    model = self._extract_data_model(cls, source_file.path)
                    results['data_models'].append(model)

                    # Legacy feature
                    results['features'].append(BusinessFeature(
                        name=cls.name,
                        type="Entity",
                        description=cls.docstring or f"Data model: {cls.name}",
                        source_file=source_file.path,
                        code_ref=f"class {cls.name} (line {cls.line_number})"
                    ))

                # API methods from classes
                for method in cls.methods:
                    if self._is_public_method(method):
                        api_method = self._extract_api_method(method, source_file.path, cls.name)
                        results['api_methods'].append(api_method)

        # Top-level functions as API
        if ast.functions:
            for func in ast.functions:
                if self._is_public_function(func):
                    api_method = self._extract_api_method(func, source_file.path, None)
                    results['api_methods'].append(api_method)

                    # Check for route decorators
                    if self._has_route_decorator(func):
                        results['features'].append(BusinessFeature(
                            name=func.name,
                            type="API Endpoint",
                            description=func.docstring or f"API endpoint: {func.name}",
                            source_file=source_file.path,
                            code_ref=f"Function: {func.name}"
                        ))

        # Validation rules
        if ast.validation_rules:
            for rule in ast.validation_rules:
                constraint = self._extract_validation_constraint(rule, source_file.path)
                results['validation_rules'].append(constraint)

                # Legacy feature
                results['features'].append(BusinessFeature(
                    name=f"Validation: {rule.condition[:50]}..." if len(rule.condition) > 50 else f"Validation: {rule.condition}",
                    type="Constraint",
                    description=self._generate_constraint_description(rule),
                    source_file=source_file.path,
                    code_ref=f"if {rule.condition} (line {rule.line_number})"
                ))

        # Exceptions
        if ast.exceptions:
            results['exceptions'] = ast.exceptions
            for exc in ast.exceptions:
                results['features'].append(BusinessFeature(
                    name=exc,
                    type="Exception",
                    description=f"Custom exception type: {exc}",
                    source_file=source_file.path
                ))

        # Imports
        results['imports'] = ast.imports

        return results

    def _extract_data_model(self, cls: ClassInfo, source_file: str) -> DataModel:
        """Extract a data model from class info."""
        fields = []
        for field in cls.fields:
            fields.append(DataModelField(
                name=field.name,
                type=field.type_annotation or "Any",
                required=field.is_required,
                default=field.default_value
            ))

        return DataModel(
            name=cls.name,
            source_file=source_file,
            line_number=cls.line_number,
            fields=fields,
            base_classes=cls.base_classes,
            is_dataclass=cls.is_dataclass,
            is_abstract=cls.is_abstract,
            docstring=cls.docstring
        )

    def _extract_api_method(self, method: MethodInfo, source_file: str, class_name: Optional[str]) -> APIMethod:
        """Extract API method information."""
        params = []
        for p in method.parameters:
            params.append({
                'name': p.name,
                'type': p.type_annotation or 'Any'
            })

        return APIMethod(
            name=method.name,
            source_file=source_file,
            class_name=class_name,
            parameters=params,
            return_type=method.return_type,
            is_async=method.is_async,
            is_classmethod=method.is_classmethod,
            is_abstractmethod=method.is_abstractmethod,
            docstring=method.docstring,
            line_number=method.line_number
        )

    def _extract_validation_constraint(self, rule: ValidationRule, source_file: str) -> ValidationConstraint:
        """Extract validation constraint from rule."""
        self.constraint_counter += 1

        return ValidationConstraint(
            id=f"VC-{self.constraint_counter:03d}",
            title=self._generate_constraint_title(rule),
            description=self._generate_constraint_description(rule),
            condition=rule.condition,
            error_message=rule.error_message,
            source_file=source_file,
            function_name=rule.function_name,
            line_number=rule.line_number
        )

    def _generate_constraint_title(self, rule: ValidationRule) -> str:
        """Generate a human-readable title for a validation rule."""
        condition = rule.condition

        # Pattern matching for common validation types
        if 'not in' in condition:
            return f"Required field check in {rule.function_name}"
        elif 'is None' in condition or '== None' in condition:
            return f"Null check in {rule.function_name}"
        elif '<' in condition or '>' in condition or '<=' in condition or '>=' in condition:
            return f"Range/boundary validation in {rule.function_name}"
        elif 'len(' in condition:
            return f"Length validation in {rule.function_name}"
        elif 'isinstance' in condition:
            return f"Type validation in {rule.function_name}"
        else:
            return f"Validation in {rule.function_name}"

    def _generate_constraint_description(self, rule: ValidationRule) -> str:
        """Generate a description for a validation rule."""
        condition = rule.condition

        # Try to make it more readable
        desc = f"Validates that: {condition}"

        if rule.error_message:
            desc += f"\nError: {rule.error_message}"

        return desc

    def _is_entity_class(self, cls: ClassInfo) -> bool:
        """Check if a class represents a data entity."""
        # Check base classes
        entity_bases = {'BaseModel', 'Model', 'Entity', 'ABC', 'TypedDict'}
        if any(base in entity_bases for base in cls.base_classes):
            return True

        # Check if it has typed fields
        if cls.fields:
            return True

        # Check naming conventions
        if cls.name.endswith(('Model', 'Entity', 'Data', 'DTO', 'Schema')):
            return True

        return False

    def _is_public_method(self, method: MethodInfo) -> bool:
        """Check if a method is public (doesn't start with _)."""
        return not method.name.startswith('_')

    def _is_public_function(self, func: MethodInfo) -> bool:
        """Check if a function is public."""
        return not func.name.startswith('_')

    def _has_route_decorator(self, func: MethodInfo) -> bool:
        """Check if function has API route decorators."""
        route_indicators = {'get', 'post', 'put', 'delete', 'patch', 'route', 'api', 'app'}
        for dec in func.decorators:
            dec_lower = dec.lower()
            if any(ind in dec_lower for ind in route_indicators):
                return True
        return False


def aggregate_analysis(
    project_name: str,
    file_results: List[Dict[str, Any]],
    file_count: int
) -> ProjectAnalysis:
    """
    Aggregate analysis results from multiple files into a ProjectAnalysis.
    """
    analysis = ProjectAnalysis(
        project_name=project_name,
        files_analyzed=file_count
    )

    all_imports = {}

    for result in file_results:
        # Aggregate data models
        analysis.data_models.extend(result.get('data_models', []))

        # Aggregate API methods
        analysis.api_methods.extend(result.get('api_methods', []))

        # Aggregate validation rules
        analysis.validation_rules.extend(result.get('validation_rules', []))

        # Aggregate exceptions
        for exc in result.get('exceptions', []):
            if exc not in analysis.exceptions:
                analysis.exceptions.append(exc)

        # Aggregate features (legacy)
        analysis.features.extend(result.get('features', []))

        # Aggregate imports by file
        # (simplified - just collect unique imports)
        for imp in result.get('imports', []):
            if imp not in all_imports:
                all_imports[imp] = True

    analysis.imports = all_imports

    # Generate key capabilities from analysis
    analysis.key_capabilities = _infer_capabilities(analysis)

    # Add reasoning
    analysis.reasoning = {
        'summary': 'Generated via Enhanced Static Analysis',
        'active_personas': ['Code Analyst', 'Systems Architect', 'Technical Writer'],
        'tools_used': ['Python AST', 'Pattern Matching'],
        'patterns_detected': _detect_patterns(analysis)
    }

    return analysis


def _infer_capabilities(analysis: ProjectAnalysis) -> List[str]:
    """Infer key capabilities from analysis results."""
    capabilities = []

    # From data models
    if analysis.data_models:
        model_names = [m.name for m in analysis.data_models]
        capabilities.append(f"Data modeling ({', '.join(model_names[:3])}{'...' if len(model_names) > 3 else ''})")

    # From API methods
    public_apis = [m for m in analysis.api_methods if not m.name.startswith('_')]
    if public_apis:
        capabilities.append(f"Public API with {len(public_apis)} methods")

    # From validation rules
    if analysis.validation_rules:
        capabilities.append(f"Input validation ({len(analysis.validation_rules)} rules)")

    # From exceptions
    if analysis.exceptions:
        capabilities.append(f"Error handling ({', '.join(analysis.exceptions[:2])})")

    # Check for specific patterns
    serialization_methods = [m for m in analysis.api_methods if 'json' in m.name.lower() or 'serialize' in m.name.lower()]
    if serialization_methods:
        capabilities.append("JSON serialization/deserialization")

    persistence_methods = [m for m in analysis.api_methods if 'save' in m.name.lower() or 'load' in m.name.lower() or 'disk' in m.name.lower()]
    if persistence_methods:
        capabilities.append("File persistence")

    return capabilities


def _detect_patterns(analysis: ProjectAnalysis) -> List[str]:
    """Detect design patterns from analysis."""
    patterns = []

    # Dataclass pattern
    if any(m.is_dataclass for m in analysis.data_models):
        patterns.append("Dataclass (immutable data structures)")

    # Abstract base class pattern
    if any(m.is_abstract for m in analysis.data_models):
        patterns.append("Abstract Base Class (interface definition)")

    # Validation pattern
    if analysis.validation_rules:
        patterns.append("Guard Clause (early validation)")

    # Serialization pattern
    serialization_methods = [m for m in analysis.api_methods if 'json' in m.name.lower()]
    if serialization_methods:
        patterns.append("Serialization (JSON conversion)")

    return patterns
