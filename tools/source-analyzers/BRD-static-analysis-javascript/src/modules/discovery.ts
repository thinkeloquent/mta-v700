import { globby } from 'globby';
import path from 'path';

export enum FileType {
    MODEL = "model",
    CONTROLLER = "controller",
    SERVICE = "service",
    UTILITY = "utility",
    CONFIG = "config",
    TEST = "test",
    UNKNOWN = "unknown"
}

export interface SourceFile {
    path: string;
    name: string;
    extension: string;
    fileType: FileType;
    language: string;
}

export class DiscoveryEngine {
    private rootPath: string;
    private ignorePatterns: string[];

    constructor(rootPath: string, ignorePatterns: string[] = []) {
        this.rootPath = path.resolve(rootPath);
        this.ignorePatterns = [
            ...ignorePatterns,
            '**/node_modules/**',
            '**/dist/**',
            '**/build/**',
            '**/coverage/**',
            '**/.git/**'
        ];
    }

    async scan(): Promise<SourceFile[]> {
        const paths = await globby(['**/*.{js,jsx,ts,tsx,mjs,cjs}'], {
            cwd: this.rootPath,
            ignore: this.ignorePatterns,
            absolute: true
        });

        return paths.map(filePath => this.classifyFile(filePath)).filter((f): f is SourceFile => f !== null);
    }

    private classifyFile(filePath: string): SourceFile | null {
        const ext = path.extname(filePath).toLowerCase();
        const name = path.basename(filePath).toLowerCase();
        const dir = path.dirname(filePath).toLowerCase();

        // Language
        let language = 'unknown';
        if (['.js', '.jsx', '.cjs', '.mjs'].includes(ext)) language = 'javascript';
        if (['.ts', '.tsx', '.mts', '.cts'].includes(ext)) language = 'typescript';

        // Heuristics
        let fileType = FileType.UNKNOWN;
        if (name.includes('test') || name.includes('spec') || dir.includes('__tests__')) {
            fileType = FileType.TEST;
        } else if (name.includes('model') || name.includes('schema') || name.includes('entity') || name.includes('type')) {
            fileType = FileType.MODEL;
        } else if (name.includes('controller') || name.includes('route') || name.includes('api')) {
            fileType = FileType.CONTROLLER;
        } else if (name.includes('service') || name.includes('manager')) {
            fileType = FileType.SERVICE;
        } else if (name.includes('util') || name.includes('helper') || name.includes('common')) {
            fileType = FileType.UTILITY;
        } else if (name.includes('config') || name.includes('setting')) {
            fileType = FileType.CONFIG;
        }

        return {
            path: filePath,
            name: path.basename(filePath),
            extension: ext,
            fileType,
            language
        };
    }
}
