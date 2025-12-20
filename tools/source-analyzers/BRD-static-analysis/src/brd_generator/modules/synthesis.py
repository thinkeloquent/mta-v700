from typing import Dict, Any, List
from datetime import datetime
import yaml
import json
from .analyzer import ProjectAnalysis, DataModel, APIMethod, ValidationConstraint


class SynthesisEngine:
    """
    Synthesizes the analysis results into a structured BRD.
    """

    def generate_brd(self, analysis: ProjectAnalysis, format: str = "yaml") -> str:
        """Generate BRD document from analysis."""
        brd_structure = self._build_brd_structure(analysis)

        if format == "json":
            return json.dumps(brd_structure, indent=2, default=str)
        else:
            return yaml.dump(brd_structure, sort_keys=False, default_flow_style=False, allow_unicode=True)

    def _build_brd_structure(self, analysis: ProjectAnalysis) -> Dict[str, Any]:
        """Build the complete BRD structure."""
        return {
            "brd": {
                "metadata": self._build_metadata(analysis),
                "executive_summary": self._build_executive_summary(analysis),
                "data_models": self._build_data_models(analysis),
                "api_surface": self._build_api_surface(analysis),
                "functional_requirements": self._build_functional_requirements(analysis),
                "validation_rules": self._build_validation_rules(analysis),
                "error_handling": self._build_error_handling(analysis),
                "reasoning": self._build_reasoning(analysis)
            }
        }

    def _build_metadata(self, analysis: ProjectAnalysis) -> Dict[str, Any]:
        """Build metadata section."""
        return {
            "project": analysis.project_name,
            "version": "1.0.0",
            "files_analyzed": analysis.files_analyzed,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "generator": "brd-static-analysis-py v0.1.0"
        }

    def _build_executive_summary(self, analysis: ProjectAnalysis) -> Dict[str, Any]:
        """Build executive summary section."""
        # Generate purpose from analysis
        purpose = self._infer_purpose(analysis)

        return {
            "purpose": purpose,
            "key_capabilities": analysis.key_capabilities,
            "patterns_detected": analysis.reasoning.get('patterns_detected', [])
        }

    def _infer_purpose(self, analysis: ProjectAnalysis) -> str:
        """Infer project purpose from analysis."""
        parts = []

        if analysis.data_models:
            model_names = [m.name for m in analysis.data_models[:3]]
            parts.append(f"Defines data structures ({', '.join(model_names)})")

        if analysis.validation_rules:
            parts.append(f"with {len(analysis.validation_rules)} validation rules")

        if analysis.api_methods:
            persistence = [m for m in analysis.api_methods if 'save' in m.name.lower() or 'load' in m.name.lower()]
            if persistence:
                parts.append("supporting file persistence")

            serialization = [m for m in analysis.api_methods if 'json' in m.name.lower()]
            if serialization:
                parts.append("and JSON serialization")

        if parts:
            return ' '.join(parts) + '.'
        return f"Automated analysis of {analysis.project_name}"

    def _build_data_models(self, analysis: ProjectAnalysis) -> List[Dict[str, Any]]:
        """Build data models section."""
        models = []

        for model in analysis.data_models:
            model_entry = {
                "name": model.name,
                "type": "dataclass" if model.is_dataclass else ("abstract" if model.is_abstract else "class"),
                "source_file": self._short_path(model.source_file),
                "line": model.line_number
            }

            if model.base_classes:
                model_entry["inherits"] = model.base_classes

            if model.docstring:
                model_entry["description"] = model.docstring

            if model.fields:
                model_entry["fields"] = [
                    {
                        "name": f.name,
                        "type": f.type,
                        "required": f.required,
                        **({"default": f.default} if f.default else {})
                    }
                    for f in model.fields
                ]

            models.append(model_entry)

        return models

    def _build_api_surface(self, analysis: ProjectAnalysis) -> Dict[str, Any]:
        """Build API surface section."""
        # Group by class
        class_methods = {}
        standalone_functions = []

        for method in analysis.api_methods:
            if method.class_name:
                if method.class_name not in class_methods:
                    class_methods[method.class_name] = []
                class_methods[method.class_name].append(method)
            else:
                standalone_functions.append(method)

        api_surface = {
            "total_methods": len(analysis.api_methods)
        }

        if class_methods:
            api_surface["classes"] = {}
            for class_name, methods in class_methods.items():
                api_surface["classes"][class_name] = [
                    self._format_method(m) for m in methods
                ]

        if standalone_functions:
            api_surface["functions"] = [
                self._format_method(f) for f in standalone_functions
            ]

        return api_surface

    def _format_method(self, method: APIMethod) -> Dict[str, Any]:
        """Format a method for output."""
        entry = {
            "name": method.name,
            "signature": self._build_signature(method)
        }

        if method.docstring:
            entry["description"] = method.docstring

        if method.is_abstractmethod:
            entry["abstract"] = True

        if method.is_classmethod:
            entry["classmethod"] = True

        if method.is_async:
            entry["async"] = True

        return entry

    def _build_signature(self, method: APIMethod) -> str:
        """Build a method signature string."""
        params = []
        for p in method.parameters:
            if p.get('type') and p['type'] != 'Any':
                params.append(f"{p['name']}: {p['type']}")
            else:
                params.append(p['name'])

        param_str = ", ".join(params)
        return_str = f" -> {method.return_type}" if method.return_type else ""

        prefix = ""
        if method.is_async:
            prefix = "async "

        return f"{prefix}def {method.name}({param_str}){return_str}"

    def _build_functional_requirements(self, analysis: ProjectAnalysis) -> List[Dict[str, Any]]:
        """Build functional requirements from features."""
        requirements = []
        fr_counter = 0

        # Generate requirements from data models
        for model in analysis.data_models:
            fr_counter += 1
            req = {
                "id": f"FR-{fr_counter:03d}",
                "title": f"Data Model: {model.name}",
                "type": "Entity",
                "description": model.docstring or f"System shall maintain {model.name} data structure",
                "source_evidence": {
                    "file": self._short_path(model.source_file),
                    "line": model.line_number,
                    "code_ref": f"class {model.name}"
                }
            }

            if model.fields:
                req["attributes"] = [f.name for f in model.fields]

            requirements.append(req)

        # Generate requirements from validation rules
        for rule in analysis.validation_rules:
            fr_counter += 1
            requirements.append({
                "id": f"FR-{fr_counter:03d}",
                "title": rule.title,
                "type": "Constraint",
                "description": f"System shall validate: {rule.condition}",
                "source_evidence": {
                    "file": self._short_path(rule.source_file),
                    "line": rule.line_number,
                    "function": rule.function_name,
                    "code_ref": f"if {rule.condition}"
                },
                **({"error_message": rule.error_message} if rule.error_message else {})
            })

        return requirements

    def _build_validation_rules(self, analysis: ProjectAnalysis) -> List[Dict[str, Any]]:
        """Build detailed validation rules section."""
        rules = []

        for rule in analysis.validation_rules:
            rules.append({
                "id": rule.id,
                "function": rule.function_name,
                "condition": rule.condition,
                "error_message": rule.error_message,
                "line": rule.line_number,
                "business_rule": self._interpret_condition(rule.condition)
            })

        return rules

    def _interpret_condition(self, condition: str) -> str:
        """Interpret a condition into business language."""
        # Simple pattern matching for common validations
        if 'not in' in condition:
            # Extract the key being checked
            parts = condition.split('not in')
            if len(parts) == 2:
                key = parts[0].strip().strip('"\'')
                return f"Field '{key}' is required"

        if 'is None' in condition or '== None' in condition:
            return "Value must not be null"

        if '<' in condition and '>' not in condition:
            return "Value must meet minimum threshold"

        if '>' in condition and '<' not in condition:
            return "Value must not exceed maximum threshold"

        if 'len(' in condition:
            return "Value must meet length requirements"

        if 'isinstance' in condition:
            return "Value must be of correct type"

        return f"Condition: {condition}"

    def _build_error_handling(self, analysis: ProjectAnalysis) -> Dict[str, Any]:
        """Build error handling section."""
        return {
            "custom_exceptions": analysis.exceptions,
            "exception_count": len(analysis.exceptions)
        }

    def _build_reasoning(self, analysis: ProjectAnalysis) -> Dict[str, Any]:
        """Build reasoning/methodology section."""
        return {
            "summary": analysis.reasoning.get('summary', 'Generated via Static Analysis'),
            "active_personas": analysis.reasoning.get('active_personas', ['Code Analyst']),
            "tools_used": analysis.reasoning.get('tools_used', ['Python AST']),
            "patterns_detected": analysis.reasoning.get('patterns_detected', []),
            "decision_flow": [
                "1. File discovery - Scanned directory for Python source files",
                "2. AST parsing - Extracted classes, functions, and validation logic",
                "3. Pattern recognition - Identified data models, APIs, and constraints",
                "4. BRD synthesis - Generated structured documentation"
            ]
        }

    def _short_path(self, path: str) -> str:
        """Get shortened file path for display."""
        # Keep just the last 2-3 path components
        parts = path.replace('\\', '/').split('/')
        if len(parts) > 3:
            return '/'.join(parts[-3:])
        return path
