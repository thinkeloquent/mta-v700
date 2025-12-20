import { ParsedFile, ClassInfo, FunctionInfo, ValidationInfo, MethodInfo, FieldInfo } from "./parser.js";
import { SourceFile } from "./discovery.js";
import path from 'path';

export interface DataModel {
    name: string;
    type: 'class' | 'interface' | 'type' | 'abstract';
    sourceFile: string;
    line: number;
    description?: string;
    inherits?: string[];
    implements?: string[];
    fields: Array<{
        name: string;
        type: string;
        required: boolean;
        default?: string;
    }>;
}

export interface APIMethod {
    name: string;
    signature: string;
    description?: string;
    isAsync: boolean;
    isStatic: boolean;
    isAbstract: boolean;
}

export interface APISurface {
    totalMethods: number;
    classes: Record<string, APIMethod[]>;
    functions: Array<{
        name: string;
        signature: string;
        description?: string;
        isAsync: boolean;
    }>;
}

export interface ValidationRule {
    id: string;
    function: string;
    condition: string;
    errorMessage: string;
    line: number;
    businessRule: string;
    sourceFile: string;
}

export interface ErrorHandling {
    customExceptions: string[];
    exceptionCount: number;
}

export interface PatternInfo {
    name: string;
    description: string;
}

export interface ProjectAnalysis {
    projectName: string;
    filesAnalyzed: number;
    dataModels: DataModel[];
    apiSurface: APISurface;
    validationRules: ValidationRule[];
    errorHandling: ErrorHandling;
    patternsDetected: string[];
    zodSchemas: Array<{ name: string; sourceFile: string; line: number }>;
    reasoning: Record<string, any>;
}

export class SemanticAnalyzer {
    private dataModels: DataModel[] = [];
    private apiSurface: APISurface = {
        totalMethods: 0,
        classes: {},
        functions: []
    };
    private validationRules: ValidationRule[] = [];
    private customExceptions: Set<string> = new Set();
    private patterns: Set<string> = new Set();
    private zodSchemas: Array<{ name: string; sourceFile: string; line: number }> = [];
    private validationCounter = 0;

    analyze(files: Array<{ sourceFile: SourceFile; parsed: ParsedFile }>): ProjectAnalysis {
        // Reset state
        this.dataModels = [];
        this.apiSurface = { totalMethods: 0, classes: {}, functions: [] };
        this.validationRules = [];
        this.customExceptions = new Set();
        this.patterns = new Set();
        this.zodSchemas = [];
        this.validationCounter = 0;

        for (const { sourceFile, parsed } of files) {
            this.analyzeFile(sourceFile, parsed);
        }

        return {
            projectName: '',
            filesAnalyzed: files.length,
            dataModels: this.dataModels,
            apiSurface: this.apiSurface,
            validationRules: this.validationRules,
            errorHandling: {
                customExceptions: Array.from(this.customExceptions),
                exceptionCount: this.customExceptions.size
            },
            patternsDetected: Array.from(this.patterns),
            zodSchemas: this.zodSchemas,
            reasoning: {}
        };
    }

    private analyzeFile(sourceFile: SourceFile, parsed: ParsedFile): void {
        const relPath = sourceFile.path;

        // Process classes
        for (const cls of parsed.classes) {
            // Check if it's a custom exception
            if (cls.isErrorClass) {
                this.customExceptions.add(cls.name);
                this.patterns.add('Custom Exception Classes');
                continue; // Don't add error classes as data models
            }

            // Add as data model
            this.dataModels.push({
                name: cls.name,
                type: cls.type,
                sourceFile: relPath,
                line: cls.line,
                description: cls.description,
                inherits: cls.inherits,
                implements: cls.implements,
                fields: cls.fields.map(f => ({
                    name: f.name,
                    type: f.type,
                    required: f.required,
                    default: f.default
                }))
            });

            // Add methods to API surface
            if (cls.methods.length > 0) {
                this.apiSurface.classes[cls.name] = cls.methods.map(m => ({
                    name: m.name,
                    signature: m.signature,
                    description: m.description,
                    isAsync: m.isAsync,
                    isStatic: m.isStatic,
                    isAbstract: m.isAbstract
                }));
                this.apiSurface.totalMethods += cls.methods.length;
            }

            // Detect patterns
            this.detectClassPatterns(cls);
        }

        // Process interfaces
        for (const iface of parsed.interfaces) {
            this.dataModels.push({
                name: iface.name,
                type: iface.type,
                sourceFile: relPath,
                line: iface.line,
                description: iface.description,
                inherits: iface.inherits,
                fields: iface.fields.map(f => ({
                    name: f.name,
                    type: f.type,
                    required: f.required,
                    default: f.default
                }))
            });

            // Add interface methods to API surface
            if (iface.methods.length > 0) {
                this.apiSurface.classes[iface.name] = iface.methods.map(m => ({
                    name: m.name,
                    signature: m.signature,
                    description: m.description,
                    isAsync: m.isAsync,
                    isStatic: m.isStatic,
                    isAbstract: m.isAbstract
                }));
                this.apiSurface.totalMethods += iface.methods.length;
            }

            this.patterns.add('Interface Definition');
        }

        // Process standalone functions
        for (const func of parsed.functions) {
            if (func.isExported) {
                this.apiSurface.functions.push({
                    name: func.name,
                    signature: func.signature,
                    description: func.description,
                    isAsync: func.isAsync
                });
                this.apiSurface.totalMethods++;
            }
        }

        // Process validation rules
        for (const validation of parsed.validations) {
            this.validationCounter++;
            this.validationRules.push({
                id: `VC-${String(this.validationCounter).padStart(3, '0')}`,
                function: validation.function,
                condition: validation.condition,
                errorMessage: validation.errorMessage,
                line: validation.line,
                businessRule: this.inferBusinessRule(validation),
                sourceFile: relPath
            });
            this.patterns.add('Guard Clause (early validation)');
        }

        // Process Zod schemas
        for (const schema of parsed.zodSchemas) {
            this.zodSchemas.push({
                name: schema.name,
                sourceFile: relPath,
                line: schema.line
            });
            this.patterns.add('Zod Schema Validation');
        }
    }

    private detectClassPatterns(cls: ClassInfo): void {
        // Singleton pattern
        if (cls.methods.some(m => m.name === 'getInstance' && m.isStatic)) {
            this.patterns.add('Singleton Pattern');
        }

        // Factory pattern
        if (cls.methods.some(m => m.name.startsWith('create') && m.isStatic)) {
            this.patterns.add('Factory Pattern');
        }

        // Builder pattern
        if (cls.methods.some(m => m.name === 'build')) {
            this.patterns.add('Builder Pattern');
        }

        // Class with fields - data structure
        if (cls.fields.length > 0 && cls.methods.length <= 3) {
            this.patterns.add('Data Class (structured data)');
        }

        // Serialization pattern
        if (cls.methods.some(m => m.name === 'toJSON' || m.name === 'fromJSON')) {
            this.patterns.add('Serialization (JSON conversion)');
        }

        // File persistence
        if (cls.methods.some(m => m.name.includes('save') || m.name.includes('load') || m.name.includes('Disk'))) {
            this.patterns.add('File Persistence');
        }
    }

    private inferBusinessRule(validation: ValidationInfo): string {
        const condition = validation.condition.toLowerCase();
        const errorMsg = validation.errorMessage.toLowerCase();

        // Null/undefined checks
        if (condition.includes('=== undefined') || condition.includes('=== null') ||
            condition.includes('== null') || condition.includes('== undefined')) {
            return 'Value must not be null/undefined';
        }

        // Type checks
        if (condition.includes('typeof')) {
            const typeMatch = condition.match(/typeof\s+\w+\s*[!=]==?\s*['"](\w+)['"]/);
            if (typeMatch) {
                return `Value must be of type ${typeMatch[1]}`;
            }
        }

        // Required field checks
        if (errorMsg.includes('required') || errorMsg.includes('missing')) {
            return 'Required field validation';
        }

        // Not found
        if (errorMsg.includes('not found') || errorMsg.includes('not defined')) {
            return 'Existence check';
        }

        // Payload/content validation
        if (errorMsg.includes('cannot be')) {
            return 'Content type restriction';
        }

        return 'Validation constraint';
    }
}
