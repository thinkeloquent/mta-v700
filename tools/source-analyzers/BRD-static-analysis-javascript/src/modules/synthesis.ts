import yaml from 'yaml';
import { ProjectAnalysis, DataModel, ValidationRule } from "./analyzer.js";

export class SynthesisEngine {
    generateBRD(analysis: ProjectAnalysis, format: string = 'yaml'): string {
        // Build executive summary
        const keyCapabilities: string[] = [];

        if (analysis.dataModels.length > 0) {
            const modelNames = analysis.dataModels.slice(0, 3).map(m => m.name).join(', ');
            keyCapabilities.push(`Data modeling (${modelNames}${analysis.dataModels.length > 3 ? '...' : ''})`);
        }

        if (analysis.apiSurface.totalMethods > 0) {
            keyCapabilities.push(`Public API with ${analysis.apiSurface.totalMethods} methods`);
        }

        if (analysis.validationRules.length > 0) {
            keyCapabilities.push(`Input validation (${analysis.validationRules.length} rules)`);
        }

        if (analysis.errorHandling.exceptionCount > 0) {
            const exNames = analysis.errorHandling.customExceptions.join(', ');
            keyCapabilities.push(`Error handling (${exNames})`);
        }

        if (analysis.zodSchemas.length > 0) {
            keyCapabilities.push('Zod schema validation');
        }

        if (analysis.patternsDetected.includes('Serialization (JSON conversion)')) {
            keyCapabilities.push('JSON serialization/deserialization');
        }

        if (analysis.patternsDetected.includes('File Persistence')) {
            keyCapabilities.push('File persistence');
        }

        // Build purpose statement
        const modelList = analysis.dataModels.slice(0, 3).map(m => m.name).join(', ');
        const purpose = analysis.dataModels.length > 0
            ? `Defines data structures (${modelList}) with ${analysis.validationRules.length} validation rules supporting ${this.detectCapabilities(analysis)}.`
            : `JavaScript/TypeScript module with ${analysis.apiSurface.totalMethods} API methods.`;

        // Build data models section
        const dataModelsSection = analysis.dataModels.map(model => {
            const modelEntry: any = {
                name: model.name,
                type: model.type,
                source_file: model.sourceFile,
                line: model.line
            };

            if (model.inherits && model.inherits.length > 0) {
                modelEntry.inherits = model.inherits;
            }

            if (model.implements && model.implements.length > 0) {
                modelEntry.implements = model.implements;
            }

            if (model.description) {
                modelEntry.description = model.description;
            }

            if (model.fields.length > 0) {
                modelEntry.fields = model.fields.map(f => {
                    const field: any = {
                        name: f.name,
                        type: f.type,
                        required: f.required
                    };
                    if (f.default !== undefined) {
                        field.default = f.default;
                    }
                    return field;
                });
            }

            return modelEntry;
        });

        // Build API surface section
        const apiSurfaceSection: any = {
            total_methods: analysis.apiSurface.totalMethods,
            classes: {} as Record<string, any[]>
        };

        for (const [className, methods] of Object.entries(analysis.apiSurface.classes)) {
            apiSurfaceSection.classes[className] = methods.map(m => {
                const methodEntry: any = {
                    name: m.name,
                    signature: m.signature
                };
                if (m.description) {
                    methodEntry.description = m.description;
                }
                if (m.isAsync) {
                    methodEntry.async = true;
                }
                if (m.isStatic) {
                    methodEntry.static = true;
                }
                if (m.isAbstract) {
                    methodEntry.abstract = true;
                }
                return methodEntry;
            });
        }

        if (analysis.apiSurface.functions.length > 0) {
            apiSurfaceSection.functions = analysis.apiSurface.functions.map(f => {
                const funcEntry: any = {
                    name: f.name,
                    signature: f.signature
                };
                if (f.description) {
                    funcEntry.description = f.description;
                }
                if (f.isAsync) {
                    funcEntry.async = true;
                }
                return funcEntry;
            });
        }

        // Build functional requirements
        const functionalRequirements: any[] = [];
        let frCounter = 0;

        // Add data models as entities
        for (const model of analysis.dataModels) {
            frCounter++;
            const fr: any = {
                id: `FR-${String(frCounter).padStart(3, '0')}`,
                title: `Data Model: ${model.name}`,
                type: 'Entity',
                description: model.description || `${model.type} ${model.name}`,
                source_evidence: {
                    file: model.sourceFile,
                    line: model.line,
                    code_ref: `${model.type} ${model.name}`
                }
            };
            if (model.fields.length > 0) {
                fr.attributes = model.fields.map(f => f.name);
            }
            functionalRequirements.push(fr);
        }

        // Add validation rules as constraints
        for (const rule of analysis.validationRules) {
            frCounter++;
            functionalRequirements.push({
                id: `FR-${String(frCounter).padStart(3, '0')}`,
                title: `Validation in ${rule.function}`,
                type: 'Constraint',
                description: `System shall validate: ${rule.condition}`,
                source_evidence: {
                    file: rule.sourceFile,
                    line: rule.line,
                    function: rule.function,
                    code_ref: `if ${rule.condition}`
                },
                error_message: rule.errorMessage
            });
        }

        // Build validation rules section
        const validationRulesSection = analysis.validationRules.map(rule => ({
            id: rule.id,
            function: rule.function,
            condition: rule.condition,
            error_message: rule.errorMessage,
            line: rule.line,
            business_rule: rule.businessRule
        }));

        // Build error handling section
        const errorHandlingSection: any = {
            custom_exceptions: analysis.errorHandling.customExceptions,
            exception_count: analysis.errorHandling.exceptionCount
        };

        // Build reasoning section
        const reasoning = {
            summary: 'Generated via JS Static Analysis',
            active_personas: ['Code Analyst', 'Systems Architect', 'Technical Writer'],
            tools_used: ['Babel Parser', 'Pattern Matching'],
            patterns_detected: analysis.patternsDetected,
            decision_flow: [
                '1. File discovery - Scanned directory for JS/TS source files',
                '2. AST parsing - Extracted classes, interfaces, functions, and validation logic',
                '3. Pattern recognition - Identified data models, APIs, and validation rules'
            ]
        };

        // Build final BRD structure
        const brdStructure: any = {
            brd: {
                metadata: {
                    project: analysis.projectName,
                    version: '1.0.0',
                    files_analyzed: analysis.filesAnalyzed,
                    generated_at: new Date().toISOString(),
                    generator: 'brd-static-analysis-js v0.1.0'
                },
                executive_summary: {
                    purpose,
                    key_capabilities: keyCapabilities,
                    patterns_detected: analysis.patternsDetected
                }
            }
        };

        // Add sections if they have content
        if (dataModelsSection.length > 0) {
            brdStructure.brd.data_models = dataModelsSection;
        }

        if (analysis.apiSurface.totalMethods > 0) {
            brdStructure.brd.api_surface = apiSurfaceSection;
        }

        if (functionalRequirements.length > 0) {
            brdStructure.brd.functional_requirements = functionalRequirements;
        }

        if (validationRulesSection.length > 0) {
            brdStructure.brd.validation_rules = validationRulesSection;
        }

        if (analysis.errorHandling.exceptionCount > 0) {
            brdStructure.brd.error_handling = errorHandlingSection;
        }

        brdStructure.brd.reasoning = reasoning;

        if (format === 'json') {
            return JSON.stringify(brdStructure, null, 2);
        } else {
            return yaml.stringify(brdStructure);
        }
    }

    private detectCapabilities(analysis: ProjectAnalysis): string {
        const caps: string[] = [];

        if (analysis.patternsDetected.includes('Serialization (JSON conversion)')) {
            caps.push('JSON serialization');
        }
        if (analysis.patternsDetected.includes('File Persistence')) {
            caps.push('file persistence');
        }
        if (analysis.patternsDetected.includes('Zod Schema Validation')) {
            caps.push('schema validation');
        }
        if (analysis.apiSurface.functions.some(f => f.isAsync)) {
            caps.push('async operations');
        }

        return caps.length > 0 ? caps.join(' and ') : 'data management';
    }
}
