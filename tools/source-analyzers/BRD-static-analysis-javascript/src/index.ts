#!/usr/bin/env node
import { Command } from 'commander';
import path from 'path';
import fs from 'fs/promises';
import { DiscoveryEngine } from './modules/discovery.js';
import { PolyglotParser, ParsedFile } from './modules/parser.js';
import { SemanticAnalyzer } from './modules/analyzer.js';
import { SynthesisEngine } from './modules/synthesis.js';

const program = new Command();

program
    .name('brd-gen-js')
    .description('Generate a BRD from source code')
    .version('0.1.0');

program
    .command('generate')
    .argument('<path>', 'Path to source code')
    .option('-o, --output <file>', 'Output file path (prints to console if not specified)')
    .option('-f, --format <format>', 'Output format (yaml/json)', 'yaml')
    .action(async (sourcePath, options) => {
        console.log(`Starting BRD generation for: ${sourcePath}`);

        try {
            // 1. Discovery
            const discovery = new DiscoveryEngine(sourcePath);
            const files = await discovery.scan();
            console.log(`Discovered ${files.length} relevant files.`);

            // 2. Parsing
            const parser = new PolyglotParser();
            const parsedFiles: Array<{ sourceFile: typeof files[0]; parsed: ParsedFile }> = [];

            for (const file of files) {
                const parsed = await parser.parseFile(file.path, file.language);
                if (parsed) {
                    parsedFiles.push({ sourceFile: file, parsed });
                }
            }

            // 3. Analysis
            const analyzer = new SemanticAnalyzer();
            const analysis = analyzer.analyze(parsedFiles);
            analysis.projectName = path.basename(sourcePath);

            // Log summary
            console.log(`Identified ${analysis.dataModels.length} data models.`);
            console.log(`Identified ${analysis.apiSurface.totalMethods} API methods.`);
            console.log(`Identified ${analysis.validationRules.length} validation rules.`);

            // 4. Synthesis
            const synthesizer = new SynthesisEngine();
            const result = synthesizer.generateBRD(analysis, options.format);

            if (options.output) {
                await fs.writeFile(options.output, result);
                console.log(`BRD generated at: ${options.output}`);
            } else {
                console.log(result);
            }

        } catch (error) {
            console.error('Analysis failed:', error);
            process.exit(1);
        }
    });

program.parse();
