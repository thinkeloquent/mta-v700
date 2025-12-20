#!/usr/bin/env python3
"""
Command-line interface for yaml-spec-generator.

Usage:
    yaml-spec analyze ./path/to/package -o spec.yaml
    yaml-spec analyze ./pkg1 ./pkg2 -o combined-spec.yaml
"""

import sys
from pathlib import Path
from typing import List, Optional

try:
    import click
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.syntax import Syntax
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    click = None

from .spec_generator import SpecGenerator
from .analyzer import CodeAnalyzer


def print_basic(msg: str, style: str = ""):
    """Basic print when rich is not available."""
    print(msg)


def print_error(msg: str):
    """Print error message."""
    if HAS_RICH:
        Console().print(f"[red]Error:[/red] {msg}")
    else:
        print(f"Error: {msg}", file=sys.stderr)


def print_success(msg: str):
    """Print success message."""
    if HAS_RICH:
        Console().print(f"[green]{msg}[/green]")
    else:
        print(msg)


def print_info(msg: str):
    """Print info message."""
    if HAS_RICH:
        Console().print(f"[blue]{msg}[/blue]")
    else:
        print(msg)


def main():
    """Main entry point."""
    if click is None:
        # Fallback CLI without click
        return main_fallback()

    return cli()


def main_fallback():
    """Fallback CLI when click is not available."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate YAML specifications from source code",
        prog="yaml-spec",
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze directories")
    analyze_parser.add_argument("directories", nargs="+", help="Directories to analyze")
    analyze_parser.add_argument("-o", "--output", help="Output file path")
    analyze_parser.add_argument("-n", "--name", help="Spec name")
    analyze_parser.add_argument("--no-tests", action="store_true", help="Exclude test files")
    analyze_parser.add_argument("--line-numbers", action="store_true", help="Include line numbers")
    analyze_parser.add_argument("--no-imports", action="store_true", help="Exclude imports")
    analyze_parser.add_argument("--no-constants", action="store_true", help="Exclude constants")

    # info command
    info_parser = subparsers.add_parser("info", help="Show analysis info")
    info_parser.add_argument("directory", help="Directory to analyze")

    args = parser.parse_args()

    if args.command == "analyze":
        run_analyze(
            directories=args.directories,
            output=args.output,
            name=args.name,
            include_tests=not args.no_tests,
            include_line_numbers=args.line_numbers,
            include_imports=not args.no_imports,
            include_constants=not args.no_constants,
        )
    elif args.command == "info":
        run_info(args.directory)
    else:
        parser.print_help()


if click:
    @click.group()
    @click.version_option(version="0.1.0", prog_name="yaml-spec")
    def cli():
        """Generate YAML specifications from source code.

        Analyzes Python, JavaScript, and TypeScript source files to produce
        structured YAML documentation.
        """
        pass

    @cli.command()
    @click.argument("directories", nargs=-1, required=True, type=click.Path(exists=True))
    @click.option("-o", "--output", type=click.Path(), help="Output file path")
    @click.option("-n", "--name", help="Spec name for the output")
    @click.option("--no-tests", is_flag=True, help="Exclude test files")
    @click.option("--line-numbers", is_flag=True, help="Include line numbers in output")
    @click.option("--no-imports", is_flag=True, help="Exclude import statements")
    @click.option("--no-constants", is_flag=True, help="Exclude constant definitions")
    @click.option("--preview", is_flag=True, help="Preview output without writing file")
    def analyze(
        directories: tuple,
        output: Optional[str],
        name: Optional[str],
        no_tests: bool,
        line_numbers: bool,
        no_imports: bool,
        no_constants: bool,
        preview: bool,
    ):
        """Analyze source directories and generate YAML specification.

        Examples:

            yaml-spec analyze ./src -o spec.yaml

            yaml-spec analyze ./pkg1 ./pkg2 -o combined.yaml -n "My Project"

            yaml-spec analyze ./src --preview
        """
        run_analyze(
            directories=list(directories),
            output=output if not preview else None,
            name=name,
            include_tests=not no_tests,
            include_line_numbers=line_numbers,
            include_imports=not no_imports,
            include_constants=not no_constants,
            preview=preview,
        )

    @cli.command()
    @click.argument("directory", type=click.Path(exists=True))
    def info(directory: str):
        """Show analysis summary for a directory.

        Displays statistics about the source code without generating a full spec.
        """
        run_info(directory)

    @cli.command()
    @click.argument("file", type=click.Path(exists=True))
    def file(file: str):
        """Analyze a single source file.

        Shows detailed analysis of a single file's structure.
        """
        run_file(file)


def run_analyze(
    directories: List[str],
    output: Optional[str] = None,
    name: Optional[str] = None,
    include_tests: bool = True,
    include_line_numbers: bool = False,
    include_imports: bool = True,
    include_constants: bool = True,
    preview: bool = False,
):
    """Run the analyze command."""
    # Validate directories
    for d in directories:
        if not Path(d).is_dir():
            print_error(f"Not a directory: {d}")
            sys.exit(1)

    print_info(f"Analyzing {len(directories)} director{'y' if len(directories) == 1 else 'ies'}...")

    generator = SpecGenerator(
        include_tests=include_tests,
        include_line_numbers=include_line_numbers,
        include_imports=include_imports,
        include_constants=include_constants,
    )

    try:
        yaml_str = generator.generate(
            directories=directories,
            output_path=output,
            spec_name=name,
        )

        if preview or not output:
            if HAS_RICH:
                console = Console()
                syntax = Syntax(yaml_str[:2000] + "\n..." if len(yaml_str) > 2000 else yaml_str, "yaml")
                console.print(Panel(syntax, title="Generated YAML Spec"))
            else:
                print(yaml_str[:2000])
                if len(yaml_str) > 2000:
                    print("... (truncated)")

        if output:
            print_success(f"Specification written to: {output}")

    except Exception as e:
        print_error(str(e))
        sys.exit(1)


def run_info(directory: str):
    """Run the info command."""
    if not Path(directory).is_dir():
        print_error(f"Not a directory: {directory}")
        sys.exit(1)

    print_info(f"Analyzing: {directory}")

    analyzer = CodeAnalyzer()
    try:
        analysis = analyzer.analyze_directory(directory)

        # Calculate statistics
        total_classes = sum(len(f.classes) for f in analysis.files)
        total_functions = sum(len(f.functions) for f in analysis.files)
        total_exceptions = sum(len(f.exceptions) for f in analysis.files)

        # Count by language
        lang_counts = {}
        for f in analysis.files:
            lang = f.language.value
            lang_counts[lang] = lang_counts.get(lang, 0) + 1

        # Count patterns
        pattern_counts = {}
        for f in analysis.files:
            for cls in f.classes:
                for pattern in cls.patterns:
                    pattern_counts[pattern.value] = pattern_counts.get(pattern.value, 0) + 1

        if HAS_RICH:
            console = Console()

            # Main info
            console.print(Panel(f"[bold]{analysis.name}[/bold]\n{analysis.path}"))

            if analysis.version:
                console.print(f"Version: {analysis.version}")
            if analysis.description:
                console.print(f"Description: {analysis.description}")

            # Statistics table
            table = Table(title="Statistics")
            table.add_column("Metric", style="cyan")
            table.add_column("Count", justify="right", style="green")

            table.add_row("Files", str(len(analysis.files)))
            table.add_row("Classes", str(total_classes))
            table.add_row("Functions", str(total_functions))
            table.add_row("Exceptions", str(total_exceptions))

            console.print(table)

            # Language breakdown
            if lang_counts:
                lang_table = Table(title="Languages")
                lang_table.add_column("Language", style="cyan")
                lang_table.add_column("Files", justify="right", style="green")

                for lang, count in sorted(lang_counts.items()):
                    lang_table.add_row(lang, str(count))

                console.print(lang_table)

            # Pattern breakdown
            if pattern_counts:
                pattern_table = Table(title="Detected Patterns")
                pattern_table.add_column("Pattern", style="cyan")
                pattern_table.add_column("Count", justify="right", style="green")

                for pattern, count in sorted(pattern_counts.items()):
                    pattern_table.add_row(pattern, str(count))

                console.print(pattern_table)

        else:
            print(f"\nPackage: {analysis.name}")
            print(f"Path: {analysis.path}")
            if analysis.version:
                print(f"Version: {analysis.version}")

            print(f"\nStatistics:")
            print(f"  Files: {len(analysis.files)}")
            print(f"  Classes: {total_classes}")
            print(f"  Functions: {total_functions}")
            print(f"  Exceptions: {total_exceptions}")

            print(f"\nLanguages:")
            for lang, count in sorted(lang_counts.items()):
                print(f"  {lang}: {count}")

            if pattern_counts:
                print(f"\nDetected Patterns:")
                for pattern, count in sorted(pattern_counts.items()):
                    print(f"  {pattern}: {count}")

    except Exception as e:
        print_error(str(e))
        sys.exit(1)


def run_file(file_path: str):
    """Run the file analysis command."""
    if not Path(file_path).is_file():
        print_error(f"Not a file: {file_path}")
        sys.exit(1)

    print_info(f"Analyzing: {file_path}")

    analyzer = CodeAnalyzer()
    try:
        analysis = analyzer.analyze_file(file_path)

        if HAS_RICH:
            console = Console()

            console.print(Panel(f"[bold]{analysis.path}[/bold]\nLanguage: {analysis.language.value}"))

            if analysis.module_docstring:
                console.print(f"\n[dim]{analysis.module_docstring}[/dim]")

            if analysis.classes:
                console.print("\n[bold]Classes:[/bold]")
                for cls in analysis.classes:
                    patterns = f" ({', '.join(p.value for p in cls.patterns)})" if cls.patterns else ""
                    console.print(f"  - {cls.name}{patterns}")
                    for method in cls.methods:
                        console.print(f"      .{method.name}()")

            if analysis.functions:
                console.print("\n[bold]Functions:[/bold]")
                for func in analysis.functions:
                    async_marker = "async " if func.is_async else ""
                    console.print(f"  - {async_marker}{func.name}()")

            if analysis.exceptions:
                console.print("\n[bold]Exceptions:[/bold]")
                for exc in analysis.exceptions:
                    console.print(f"  - {exc.name} extends {exc.base}")

        else:
            print(f"\nFile: {analysis.path}")
            print(f"Language: {analysis.language.value}")

            if analysis.classes:
                print("\nClasses:")
                for cls in analysis.classes:
                    print(f"  - {cls.name}")

            if analysis.functions:
                print("\nFunctions:")
                for func in analysis.functions:
                    print(f"  - {func.name}()")

    except Exception as e:
        print_error(str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
