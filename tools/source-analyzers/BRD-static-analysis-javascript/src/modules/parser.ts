import fs from 'fs/promises';
import { parse } from '@babel/parser';
import * as t from '@babel/types';
import generator from '@babel/generator';

// Handle both ESM and CJS module formats
const generate = typeof generator === 'function' ? generator : (generator as any).default;

export interface FieldInfo {
    name: string;
    type: string;
    required: boolean;
    default?: string;
}

export interface MethodInfo {
    name: string;
    signature: string;
    description?: string;
    isAsync: boolean;
    isStatic: boolean;
    isAbstract: boolean;
    parameters: Array<{ name: string; type: string; optional: boolean }>;
    returnType?: string;
}

export interface ClassInfo {
    name: string;
    type: 'class' | 'interface' | 'type' | 'abstract';
    inherits?: string[];
    implements?: string[];
    fields: FieldInfo[];
    methods: MethodInfo[];
    isErrorClass: boolean;
    description?: string;
    line: number;
}

export interface ValidationInfo {
    function: string;
    condition: string;
    errorMessage: string;
    line: number;
}

export interface FunctionInfo {
    name: string;
    signature: string;
    description?: string;
    isAsync: boolean;
    isExported: boolean;
    parameters: Array<{ name: string; type: string; optional: boolean }>;
    returnType?: string;
    line: number;
}

export interface ParsedFile {
    classes: ClassInfo[];
    interfaces: ClassInfo[];
    functions: FunctionInfo[];
    validations: ValidationInfo[];
    exports: string[];
    zodSchemas: Array<{ name: string; line: number }>;
}

export class PolyglotParser {
    async parseFile(filePath: string, language: string): Promise<ParsedFile | null> {
        try {
            const code = await fs.readFile(filePath, 'utf-8');
            const isTs = language === 'typescript';

            const ast = parse(code, {
                sourceType: 'module',
                plugins: [
                    'jsx',
                    ...(isTs ? ['typescript' as const] : []),
                    'decorators-legacy',
                    'classProperties'
                ]
            });

            return this.extractInfo(ast, code);
        } catch (error) {
            console.error(`Error parsing ${filePath}:`, error);
            return null;
        }
    }

    private extractInfo(ast: t.File, code: string): ParsedFile {
        const result: ParsedFile = {
            classes: [],
            interfaces: [],
            functions: [],
            validations: [],
            exports: [],
            zodSchemas: []
        };

        const lines = code.split('\n');

        // Helper to get leading comment as description
        const getDescription = (node: t.Node): string | undefined => {
            const comments = node.leadingComments;
            if (comments && comments.length > 0) {
                const lastComment = comments[comments.length - 1];
                // Clean up comment
                let text = lastComment.value;
                if (lastComment.type === 'CommentBlock') {
                    text = text.replace(/^\*+\s*/gm, '').replace(/\s*\*+$/gm, '').trim();
                }
                return text.trim() || undefined;
            }
            return undefined;
        };

        // Helper to convert type annotation to string
        const typeToString = (typeAnnotation: t.Node | null | undefined): string => {
            if (!typeAnnotation) return 'any';

            if (t.isTSTypeAnnotation(typeAnnotation)) {
                return typeToString(typeAnnotation.typeAnnotation);
            }
            if (t.isTSStringKeyword(typeAnnotation)) return 'string';
            if (t.isTSNumberKeyword(typeAnnotation)) return 'number';
            if (t.isTSBooleanKeyword(typeAnnotation)) return 'boolean';
            if (t.isTSAnyKeyword(typeAnnotation)) return 'any';
            if (t.isTSVoidKeyword(typeAnnotation)) return 'void';
            if (t.isTSNullKeyword(typeAnnotation)) return 'null';
            if (t.isTSUndefinedKeyword(typeAnnotation)) return 'undefined';
            if (t.isTSNeverKeyword(typeAnnotation)) return 'never';
            if (t.isTSUnknownKeyword(typeAnnotation)) return 'unknown';
            if (t.isTSTypeReference(typeAnnotation)) {
                let name = '';
                if (t.isIdentifier(typeAnnotation.typeName)) {
                    name = typeAnnotation.typeName.name;
                } else if (t.isTSQualifiedName(typeAnnotation.typeName)) {
                    name = generate(typeAnnotation.typeName).code;
                }
                if (typeAnnotation.typeParameters) {
                    const params = typeAnnotation.typeParameters.params.map(p => typeToString(p)).join(', ');
                    return `${name}<${params}>`;
                }
                return name;
            }
            if (t.isTSArrayType(typeAnnotation)) {
                return `${typeToString(typeAnnotation.elementType)}[]`;
            }
            if (t.isTSUnionType(typeAnnotation)) {
                return typeAnnotation.types.map(t => typeToString(t)).join(' | ');
            }
            if (t.isTSIntersectionType(typeAnnotation)) {
                return typeAnnotation.types.map(t => typeToString(t)).join(' & ');
            }
            if (t.isTSTypeLiteral(typeAnnotation)) {
                return 'object';
            }
            if (t.isTSFunctionType(typeAnnotation)) {
                return 'Function';
            }
            if (t.isTSLiteralType(typeAnnotation)) {
                if (t.isStringLiteral(typeAnnotation.literal)) {
                    return `'${typeAnnotation.literal.value}'`;
                }
                if (t.isNumericLiteral(typeAnnotation.literal)) {
                    return String(typeAnnotation.literal.value);
                }
                if (t.isBooleanLiteral(typeAnnotation.literal)) {
                    return String(typeAnnotation.literal.value);
                }
            }
            // Fallback: try to generate code
            try {
                return generate(typeAnnotation as any).code;
            } catch {
                return 'any';
            }
        };

        // Helper to extract parameters from function
        const extractParams = (params: t.Node[]): Array<{ name: string; type: string; optional: boolean }> => {
            return params.map(p => {
                if (t.isIdentifier(p)) {
                    return {
                        name: p.name,
                        type: typeToString(p.typeAnnotation),
                        optional: p.optional || false
                    };
                }
                if (t.isAssignmentPattern(p) && t.isIdentifier(p.left)) {
                    return {
                        name: p.left.name,
                        type: typeToString(p.left.typeAnnotation),
                        optional: true
                    };
                }
                if (t.isRestElement(p) && t.isIdentifier(p.argument)) {
                    return {
                        name: `...${p.argument.name}`,
                        type: typeToString(p.typeAnnotation),
                        optional: true
                    };
                }
                if (t.isObjectPattern(p)) {
                    return {
                        name: 'options',
                        type: typeToString(p.typeAnnotation),
                        optional: false
                    };
                }
                return { name: 'unknown', type: 'any', optional: false };
            });
        };

        // Build method signature
        const buildSignature = (name: string, params: Array<{ name: string; type: string; optional: boolean }>, returnType: string, isAsync: boolean): string => {
            const paramStr = params.map(p => {
                const opt = p.optional ? '?' : '';
                return `${p.name}${opt}: ${p.type}`;
            }).join(', ');
            const asyncPrefix = isAsync ? 'async ' : '';
            return `${asyncPrefix}${name}(${paramStr}): ${returnType}`;
        };

        // Track current function for validation context
        let currentFunction: string | null = null;

        const visit = (node: t.Node, parent?: t.Node) => {
            // Class Declaration
            if (t.isClassDeclaration(node) && node.id) {
                const classInfo: ClassInfo = {
                    name: node.id.name,
                    type: node.abstract ? 'abstract' : 'class',
                    fields: [],
                    methods: [],
                    isErrorClass: false,
                    line: node.loc?.start.line || 0,
                    description: getDescription(node)
                };

                // Check inheritance
                if (node.superClass) {
                    if (t.isIdentifier(node.superClass)) {
                        classInfo.inherits = [node.superClass.name];
                        if (node.superClass.name === 'Error') {
                            classInfo.isErrorClass = true;
                        }
                    }
                }

                // Check implements
                if (node.implements) {
                    classInfo.implements = node.implements.map(impl => {
                        if (t.isTSExpressionWithTypeArguments(impl) && t.isIdentifier(impl.expression)) {
                            return impl.expression.name;
                        }
                        return 'unknown';
                    });
                }

                // Process class body
                for (const member of node.body.body) {
                    // Class Property
                    if (t.isClassProperty(member) && t.isIdentifier(member.key)) {
                        const field: FieldInfo = {
                            name: member.key.name,
                            type: typeToString(member.typeAnnotation),
                            required: !member.optional,
                            default: member.value ? generate(member.value).code : undefined
                        };
                        classInfo.fields.push(field);
                    }

                    // Class Method
                    if (t.isClassMethod(member) && t.isIdentifier(member.key)) {
                        const params = extractParams(member.params);
                        const returnType = typeToString(member.returnType);
                        const isAsync = member.async;
                        const isStatic = member.static;

                        // Skip constructor for methods list but extract field assignments
                        if (member.key.name === 'constructor') {
                            // Extract field initializations from constructor
                            member.body.body.forEach(stmt => {
                                if (t.isExpressionStatement(stmt) &&
                                    t.isAssignmentExpression(stmt.expression) &&
                                    t.isMemberExpression(stmt.expression.left) &&
                                    t.isThisExpression(stmt.expression.left.object) &&
                                    t.isIdentifier(stmt.expression.left.property)) {
                                    const fieldName = stmt.expression.left.property.name;
                                    // Check if field already exists
                                    if (!classInfo.fields.find(f => f.name === fieldName)) {
                                        classInfo.fields.push({
                                            name: fieldName,
                                            type: 'any',
                                            required: true
                                        });
                                    }
                                }
                            });
                            continue;
                        }

                        const method: MethodInfo = {
                            name: member.key.name,
                            signature: buildSignature(member.key.name, params, returnType, isAsync),
                            isAsync,
                            isStatic,
                            isAbstract: member.abstract || false,
                            parameters: params,
                            returnType,
                            description: getDescription(member)
                        };
                        classInfo.methods.push(method);
                    }
                }

                result.classes.push(classInfo);
            }

            // Interface Declaration
            if (t.isTSInterfaceDeclaration(node)) {
                const interfaceInfo: ClassInfo = {
                    name: node.id.name,
                    type: 'interface',
                    fields: [],
                    methods: [],
                    isErrorClass: false,
                    line: node.loc?.start.line || 0,
                    description: getDescription(node)
                };

                // Check extends
                if (node.extends) {
                    interfaceInfo.inherits = node.extends.map(ext => {
                        if (t.isIdentifier(ext.expression)) {
                            return ext.expression.name;
                        }
                        return 'unknown';
                    });
                }

                // Process interface body
                for (const member of node.body.body) {
                    if (t.isTSPropertySignature(member) && t.isIdentifier(member.key)) {
                        const field: FieldInfo = {
                            name: member.key.name,
                            type: typeToString(member.typeAnnotation),
                            required: !member.optional
                        };
                        interfaceInfo.fields.push(field);
                    }
                    if (t.isTSMethodSignature(member) && t.isIdentifier(member.key)) {
                        const params = extractParams(member.parameters);
                        const returnType = typeToString(member.typeAnnotation);
                        const method: MethodInfo = {
                            name: member.key.name,
                            signature: buildSignature(member.key.name, params, returnType, false),
                            isAsync: false,
                            isStatic: false,
                            isAbstract: false,
                            parameters: params,
                            returnType,
                            description: getDescription(member)
                        };
                        interfaceInfo.methods.push(method);
                    }
                }

                result.interfaces.push(interfaceInfo);
            }

            // Type Alias
            if (t.isTSTypeAliasDeclaration(node)) {
                const typeInfo: ClassInfo = {
                    name: node.id.name,
                    type: 'type',
                    fields: [],
                    methods: [],
                    isErrorClass: false,
                    line: node.loc?.start.line || 0,
                    description: getDescription(node)
                };

                // Extract fields from type literal
                if (t.isTSTypeLiteral(node.typeAnnotation)) {
                    for (const member of node.typeAnnotation.members) {
                        if (t.isTSPropertySignature(member) && t.isIdentifier(member.key)) {
                            typeInfo.fields.push({
                                name: member.key.name,
                                type: typeToString(member.typeAnnotation),
                                required: !member.optional
                            });
                        }
                    }
                }

                result.interfaces.push(typeInfo);
            }

            // Function Declaration
            if (t.isFunctionDeclaration(node) && node.id) {
                const params = extractParams(node.params);
                const returnType = typeToString(node.returnType);
                const isAsync = node.async;
                const isExported = t.isExportNamedDeclaration(parent) || t.isExportDefaultDeclaration(parent);

                const funcInfo: FunctionInfo = {
                    name: node.id.name,
                    signature: buildSignature(node.id.name, params, returnType, isAsync),
                    isAsync,
                    isExported,
                    parameters: params,
                    returnType,
                    line: node.loc?.start.line || 0,
                    description: getDescription(node)
                };
                result.functions.push(funcInfo);

                // Track for validation context
                currentFunction = node.id.name;
            }

            // Variable Declaration with arrow function
            if (t.isVariableDeclaration(node)) {
                for (const decl of node.declarations) {
                    if (t.isVariableDeclarator(decl) && t.isIdentifier(decl.id)) {
                        // Arrow function
                        if (t.isArrowFunctionExpression(decl.init)) {
                            const params = extractParams(decl.init.params);
                            const returnType = typeToString(decl.init.returnType);
                            const isAsync = decl.init.async;
                            const isExported = t.isExportNamedDeclaration(parent);

                            const funcInfo: FunctionInfo = {
                                name: decl.id.name,
                                signature: buildSignature(decl.id.name, params, returnType, isAsync),
                                isAsync,
                                isExported,
                                parameters: params,
                                returnType,
                                line: node.loc?.start.line || 0,
                                description: getDescription(node)
                            };
                            result.functions.push(funcInfo);
                        }

                        // Zod schema detection
                        if (t.isCallExpression(decl.init)) {
                            const code = generate(decl.init).code;
                            if (code.includes('z.object') || code.includes('z.string') || code.includes('z.number')) {
                                result.zodSchemas.push({
                                    name: decl.id.name,
                                    line: node.loc?.start.line || 0
                                });
                            }
                        }
                    }
                }
            }

            // Validation: if statement followed by throw
            if (t.isIfStatement(node)) {
                // Check if the consequent contains a throw
                let hasThrow = false;
                let throwArg: string = '';

                const checkForThrow = (n: t.Node) => {
                    if (t.isThrowStatement(n)) {
                        hasThrow = true;
                        if (n.argument) {
                            throwArg = generate(n.argument).code;
                        }
                    }
                    if (t.isBlockStatement(n)) {
                        for (const stmt of n.body) {
                            checkForThrow(stmt);
                        }
                    }
                };

                checkForThrow(node.consequent);

                if (hasThrow) {
                    const condition = generate(node.test).code;

                    // Extract error message from throw
                    let errorMessage = throwArg;
                    const msgMatch = throwArg.match(/['"`]([^'"`]+)['"`]/);
                    if (msgMatch) {
                        errorMessage = msgMatch[1];
                    }

                    result.validations.push({
                        function: currentFunction || 'anonymous',
                        condition,
                        errorMessage,
                        line: node.loc?.start.line || 0
                    });
                }
            }

            // Export tracking
            if (t.isExportNamedDeclaration(node)) {
                if (node.declaration) {
                    if (t.isClassDeclaration(node.declaration) && node.declaration.id) {
                        result.exports.push(node.declaration.id.name);
                    }
                    if (t.isFunctionDeclaration(node.declaration) && node.declaration.id) {
                        result.exports.push(node.declaration.id.name);
                    }
                    if (t.isVariableDeclaration(node.declaration)) {
                        for (const decl of node.declaration.declarations) {
                            if (t.isVariableDeclarator(decl) && t.isIdentifier(decl.id)) {
                                result.exports.push(decl.id.name);
                            }
                        }
                    }
                }
                if (node.specifiers) {
                    for (const spec of node.specifiers) {
                        if (t.isExportSpecifier(spec) && t.isIdentifier(spec.exported)) {
                            result.exports.push(spec.exported.name);
                        }
                    }
                }
            }

            // Recurse
            for (const key of Object.keys(node)) {
                const child = (node as any)[key];
                if (Array.isArray(child)) {
                    for (const c of child) {
                        if (c && typeof c === 'object' && 'type' in c) {
                            visit(c, node);
                        }
                    }
                } else if (child && typeof child === 'object' && 'type' in child) {
                    visit(child, node);
                }
            }

            // Reset function context
            if (t.isFunctionDeclaration(node) || t.isClassMethod(node)) {
                currentFunction = null;
            }
        };

        visit(ast.program);

        return result;
    }
}
