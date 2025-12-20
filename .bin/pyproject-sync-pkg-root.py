#!/usr/bin/env python3
"""
Sync dependencies from sub-packages to root pyproject.toml.

This script collects all production dependencies from packages in packages_py/
and appends them to the root pyproject.toml. It throws an error if duplicate
packages have conflicting version requirements.

Usage:
    python .bin/pyproject-sync-pkg-root.py

    # Dry run - show what would be added without modifying files
    python .bin/pyproject-sync-pkg-root.py --dry-run

    # Specify custom packages directory
    python .bin/pyproject-sync-pkg-root.py --packages-dir packages_py
"""

import argparse
import re
import sys
from pathlib import Path

# Try tomllib (Python 3.11+) or fall back to tomli
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        print("Error: tomllib (Python 3.11+) or tomli package required.")
        print("Install with: pip install tomli")
        sys.exit(1)

try:
    import tomlkit
except ImportError:
    print("Error: tomlkit package required for writing TOML files.")
    print("Install with: pip install tomlkit")
    sys.exit(1)


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


def normalize_package_name(name: str) -> str:
    """Normalize package name according to PEP 503."""
    return re.sub(r"[-_.]+", "-", name).lower()


def parse_version_spec(version_spec) -> tuple[str, dict | None]:
    """
    Parse a version specification.

    Returns:
        Tuple of (version_string, extras_dict or None)
    """
    if isinstance(version_spec, str):
        return version_spec, None
    elif isinstance(version_spec, dict):
        # Skip path dependencies (local packages)
        if "path" in version_spec:
            return None, None
        # Skip git dependencies
        if "git" in version_spec:
            return None, None
        version = version_spec.get("version", "")
        extras = {k: v for k, v in version_spec.items() if k != "version"}
        return version, extras if extras else None
    return None, None


def parse_pyproject_dependencies(pyproject_path: Path) -> dict[str, dict]:
    """
    Parse pyproject.toml and extract production dependencies.

    Returns:
        Dictionary mapping package names to {version, extras, source}.
    """
    if not pyproject_path.exists():
        return {}

    with open(pyproject_path, "rb") as f:
        pyproject_data = tomllib.load(f)

    poetry_deps = (
        pyproject_data.get("tool", {}).get("poetry", {}).get("dependencies", {})
    )

    packages = {}
    for name, version_spec in poetry_deps.items():
        # Skip python version constraint
        if name.lower() == "python":
            continue

        version, extras = parse_version_spec(version_spec)
        if version is None:
            continue

        normalized_name = normalize_package_name(name)
        packages[normalized_name] = {
            "name": name,  # Keep original name for output
            "version": version,
            "extras": extras,
            "source": str(pyproject_path),
        }

    return packages


def collect_subpackage_deps(packages_dir: Path) -> dict[str, list[dict]]:
    """
    Collect dependencies from all sub-packages.

    Returns:
        Dictionary mapping normalized package names to list of version specs
        (from different sub-packages).
    """
    all_deps: dict[str, list[dict]] = {}

    for pyproject_path in packages_dir.glob("*/pyproject.toml"):
        deps = parse_pyproject_dependencies(pyproject_path)
        for normalized_name, dep_info in deps.items():
            if normalized_name not in all_deps:
                all_deps[normalized_name] = []
            all_deps[normalized_name].append(dep_info)

    return all_deps


def parse_version_number(version: str) -> tuple:
    """
    Extract version number from version spec for comparison.

    Returns tuple of (major, minor, patch) or empty tuple if unparseable.
    """
    # Strip operators like ^, ~, >=, <=, ==, etc.
    version_num = re.sub(r'^[^0-9]*', '', version)
    if not version_num:
        return ()

    parts = version_num.split('.')
    try:
        return tuple(int(p) for p in parts[:3])
    except ValueError:
        return ()


def get_highest_version(versions: list[str]) -> str:
    """Get the highest version from a list of version specs."""
    parsed = [(v, parse_version_number(v)) for v in versions]
    # Sort by parsed version tuple, descending
    parsed.sort(key=lambda x: x[1], reverse=True)
    return parsed[0][0] if parsed else versions[0]


def check_version_conflicts(all_deps: dict[str, list[dict]]) -> dict[str, dict]:
    """
    Check for version conflicts across sub-packages.

    Returns:
        Dictionary of conflicts: {pkg_name: {versions: [...], deps: [...], highest: str}}
    """
    conflicts = {}

    for pkg_name, dep_list in all_deps.items():
        if len(dep_list) <= 1:
            continue

        # Get unique versions
        versions = list(set(dep["version"] for dep in dep_list))

        if len(versions) > 1:
            highest = get_highest_version(versions)
            conflicts[pkg_name] = {
                "versions": versions,
                "deps": dep_list,
                "highest": highest,
            }

    return conflicts


def resolve_conflicts(
    all_deps: dict[str, list[dict]],
    conflicts: dict[str, dict],
) -> None:
    """
    Resolve version conflicts by using the highest version.
    Modifies all_deps in place.
    """
    for pkg_name, conflict_info in conflicts.items():
        highest = conflict_info["highest"]
        # Update all deps to use the highest version
        for dep in all_deps[pkg_name]:
            dep["version"] = highest


def get_root_dependencies(root_pyproject: Path) -> dict[str, dict]:
    """Get current dependencies from root pyproject.toml."""
    return parse_pyproject_dependencies(root_pyproject)


def merge_dependencies(
    root_deps: dict[str, dict],
    subpkg_deps: dict[str, list[dict]],
    verbose: bool = False,
) -> tuple[dict[str, dict], list[str]]:
    """
    Merge sub-package dependencies into root dependencies.

    Returns:
        Tuple of (merged_deps, list of new deps added).
    """
    merged = dict(root_deps)
    added = []

    for pkg_name, dep_list in subpkg_deps.items():
        if pkg_name not in merged:
            # Use the first occurrence's info
            dep_info = dep_list[0]
            merged[pkg_name] = dep_info
            added.append(f"{dep_info['name']} = \"{dep_info['version']}\"")
            if verbose:
                print(f"  [new] {pkg_name} from {dep_info['source']}")
        elif verbose:
            print(f"  [skip] {pkg_name} (already in root)")

    return merged, added


def update_root_pyproject(
    root_pyproject: Path,
    new_deps: dict[str, dict],
    dry_run: bool = False,
) -> None:
    """Update the root pyproject.toml with new dependencies."""
    with open(root_pyproject, "r") as f:
        content = f.read()

    doc = tomlkit.parse(content)

    # Get or create the dependencies section
    if "tool" not in doc:
        doc["tool"] = tomlkit.table()
    if "poetry" not in doc["tool"]:
        doc["tool"]["poetry"] = tomlkit.table()
    if "dependencies" not in doc["tool"]["poetry"]:
        doc["tool"]["poetry"]["dependencies"] = tomlkit.table()

    deps_table = doc["tool"]["poetry"]["dependencies"]

    # Add new dependencies
    for normalized_name, dep_info in sorted(new_deps.items()):
        original_name = dep_info["name"]
        # Check if already exists (by any name variant)
        existing_names = [normalize_package_name(k) for k in deps_table.keys()]
        if normalized_name in existing_names:
            continue

        version = dep_info["version"]
        extras = dep_info.get("extras")

        if extras:
            # Create inline table for deps with extras
            inline = tomlkit.inline_table()
            inline["version"] = version
            for k, v in extras.items():
                inline[k] = v
            deps_table[original_name] = inline
        else:
            deps_table[original_name] = version

    if dry_run:
        print("\n[DRY RUN] Would update root pyproject.toml with:")
        print(tomlkit.dumps(doc))
    else:
        with open(root_pyproject, "w") as f:
            f.write(tomlkit.dumps(doc))
        print(f"Updated {root_pyproject}")


def main():
    parser = argparse.ArgumentParser(
        description="Sync dependencies from sub-packages to root pyproject.toml"
    )
    parser.add_argument(
        "--packages-dir",
        type=Path,
        default=None,
        help="Directory containing sub-packages (default: packages_py)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be added without modifying files",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed output",
    )
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Auto-accept conflict resolution using highest version",
    )

    args = parser.parse_args()

    root = get_project_root()
    packages_dir = args.packages_dir or root / "packages_py"
    root_pyproject = root / "pyproject.toml"

    if not packages_dir.exists():
        print(f"Error: Packages directory not found: {packages_dir}", file=sys.stderr)
        sys.exit(1)

    if not root_pyproject.exists():
        print(f"Error: Root pyproject.toml not found: {root_pyproject}", file=sys.stderr)
        sys.exit(1)

    print(f"Scanning sub-packages in: {packages_dir}")

    # Collect dependencies from sub-packages
    subpkg_deps = collect_subpackage_deps(packages_dir)
    print(f"Found {len(subpkg_deps)} unique dependencies across sub-packages")
    if args.verbose:
        for pkg, deps in sorted(subpkg_deps.items()):
            sources = [Path(d['source']).parent.name for d in deps]
            print(f"  {pkg}: {deps[0]['version']} (from {', '.join(sources)})")

    # Check for version conflicts
    conflicts = check_version_conflicts(subpkg_deps)
    if conflicts:
        print("\nVersion conflicts detected:")
        for pkg_name, info in conflicts.items():
            print(f"\n  {pkg_name}:")
            for dep in info["deps"]:
                print(f"    - {dep['version']} in {Path(dep['source']).parent.name}")
            print(f"    → highest: {info['highest']}")

        # Prompt user (or auto-accept with --yes)
        if args.yes:
            response = "y"
        else:
            print("\nWould you like to resolve all conflicts using the highest version? [y/N] ", end="")
            try:
                response = input().strip().lower()
            except EOFError:
                response = "n"

        if response in ("y", "yes"):
            resolve_conflicts(subpkg_deps, conflicts)
            print("Conflicts resolved using highest versions.")
        else:
            print("Aborted. Please resolve version conflicts manually.", file=sys.stderr)
            sys.exit(1)

    # Get current root dependencies
    root_deps = get_root_dependencies(root_pyproject)
    print(f"Found {len(root_deps)} dependencies in root pyproject.toml")
    if args.verbose:
        for pkg in sorted(root_deps.keys()):
            print(f"  {pkg}: {root_deps[pkg]['version']}")

    # Merge dependencies
    if args.verbose:
        print("\nMerging dependencies:")
    merged_deps, added = merge_dependencies(root_deps, subpkg_deps, verbose=args.verbose)

    if not added:
        print("\nNo new dependencies to add. Root pyproject.toml is up to date.")
        return

    print(f"\nNew dependencies to add ({len(added)}):")
    for dep in added:
        print(f"  + {dep}")

    # Update root pyproject.toml
    update_root_pyproject(root_pyproject, merged_deps, dry_run=args.dry_run)

    if not args.dry_run:
        print("\nDone! Run 'poetry lock' to update the lock file.")


if __name__ == "__main__":
    main()
