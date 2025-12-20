import typer
import os
import sys
from typing import Optional
from .modules.discovery import DiscoveryEngine
from .modules.parser import PolyglotParser
from .modules.analyzer import SemanticAnalyzer, aggregate_analysis
from .modules.synthesis import SynthesisEngine

app = typer.Typer(
    help="BRD Static Analysis - Generate Business Requirements Documents from source code",
    add_completion=False
)


@app.command()
def main(
    path: str = typer.Argument(..., help="Path to source directory or file to analyze"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path (prints to console if not specified)"),
    format: str = typer.Option("yaml", "--format", "-f", help="Output format: yaml or json"),
    info: bool = typer.Option(False, "--info", help="Show tool information and exit")
):
    """
    Generate a BRD from the source code at PATH.

    If --output is not specified, prints to console.
    """
    if info:
        print("BRD Static Analysis Generator")
        print("Version: 0.1.0")
        print("")
        print("Supported languages:")
        print("  - Python (.py)")
        print("  - JavaScript (.js, .mjs, .cjs)")
        print("  - TypeScript (.ts, .tsx)")
        print("")
        print("Output formats:")
        print("  - YAML (default)")
        print("  - JSON")
        raise typer.Exit(0)

    print(f"Starting BRD generation for: {path}", file=sys.stderr)

    # 1. Discovery
    discovery = DiscoveryEngine(path)
    files = discovery.scan()
    print(f"Discovered {len(files)} relevant files.", file=sys.stderr)

    if not files:
        print("No source files found to analyze.", file=sys.stderr)
        raise typer.Exit(1)

    # 2. Parsing & Analysis
    parser = PolyglotParser()
    analyzer = SemanticAnalyzer()

    file_results = []

    for file in files:
        ast = parser.parse_file(file.path, file.language)
        if ast:
            results = analyzer.analyze(file, ast)
            file_results.append(results)

    # 3. Aggregate results
    project_name = os.path.basename(os.path.abspath(path))
    analysis = aggregate_analysis(project_name, file_results, len(files))

    print(f"Identified {len(analysis.data_models)} data models.", file=sys.stderr)
    print(f"Identified {len(analysis.api_methods)} API methods.", file=sys.stderr)
    print(f"Identified {len(analysis.validation_rules)} validation rules.", file=sys.stderr)

    # 4. Synthesis
    synthesizer = SynthesisEngine()
    result = synthesizer.generate_brd(analysis, format=format)

    # Output to file or console
    if output:
        # Ensure output directory exists
        output_dir = os.path.dirname(output)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        with open(output, "w") as f:
            f.write(result)
        print(f"BRD generated at: {output}", file=sys.stderr)
    else:
        print(result)


if __name__ == "__main__":
    app()
