#!/usr/bin/env python3
"""
Clean unused files from directory and git history.

Usage:
    python .bin/clean_git_unused_files.py [--dry-run] [--path PATH]

Examples:
    python .bin/clean_git_unused_files.py              # Clean current directory
    python .bin/clean_git_unused_files.py --dry-run    # Preview what would be deleted
    python .bin/clean_git_unused_files.py --path ./src # Clean specific directory
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

# =============================================================================
# Files to clean (add more patterns here as needed)
# =============================================================================
PATTERNS_TO_CLEAN = [
    ".DS_Store",
    "Thumbs.db",
    "desktop.ini",
    # Add more patterns here:
    # "*.pyc",
    # "__pycache__",
    # ".env.local",
]


def run_command(cmd: list[str], dry_run: bool = False, capture: bool = True) -> subprocess.CompletedProcess:
    """Run a shell command."""
    if dry_run:
        print(f"  [DRY-RUN] Would run: {' '.join(cmd)}")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    result = subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
    )
    return result


def find_files(base_path: Path, pattern: str) -> list[Path]:
    """Find all files matching a pattern recursively."""
    if "*" in pattern:
        # Glob pattern
        return list(base_path.rglob(pattern))
    else:
        # Exact filename match
        return list(base_path.rglob(pattern))


def remove_from_filesystem(files: list[Path], dry_run: bool = False) -> int:
    """Remove files from filesystem."""
    count = 0
    for f in files:
        if f.exists():
            if dry_run:
                print(f"  [DRY-RUN] Would delete: {f}")
            else:
                try:
                    f.unlink()
                    print(f"  Deleted: {f}")
                    count += 1
                except OSError as e:
                    print(f"  Error deleting {f}: {e}", file=sys.stderr)
    return count


def remove_from_git_history(pattern: str, base_path: Path, dry_run: bool = False) -> bool:
    """
    Remove a file pattern from git history using git filter-repo or git filter-branch.

    Note: This is a destructive operation that rewrites git history.
    """
    # Check if we're in a git repo
    result = run_command(["git", "rev-parse", "--git-dir"], capture=True)
    if result.returncode != 0:
        print(f"  Not a git repository, skipping git history cleanup")
        return False

    # Check if git-filter-repo is available (preferred method)
    filter_repo_available = run_command(
        ["which", "git-filter-repo"], capture=True
    ).returncode == 0

    if filter_repo_available:
        # Use git-filter-repo (faster, safer)
        cmd = [
            "git", "filter-repo",
            "--invert-paths",
            "--path-glob", f"**/{pattern}",
            "--force",
        ]
        if dry_run:
            print(f"  [DRY-RUN] Would run: {' '.join(cmd)}")
            return True
        else:
            print(f"  Running git-filter-repo for pattern: {pattern}")
            result = run_command(cmd, capture=False)
            return result.returncode == 0
    else:
        # Fallback to git filter-branch (slower, but always available)
        cmd = [
            "git", "filter-branch",
            "--force",
            "--index-filter",
            f"git rm --cached --ignore-unmatch '**/{pattern}'",
            "--prune-empty",
            "--tag-name-filter", "cat",
            "--", "--all",
        ]
        if dry_run:
            print(f"  [DRY-RUN] Would run: git filter-branch to remove {pattern}")
            return True
        else:
            print(f"  Running git filter-branch for pattern: {pattern}")
            print(f"  (Consider installing git-filter-repo for faster performance)")
            result = run_command(cmd, capture=False)
            return result.returncode == 0


def add_to_gitignore(patterns: list[str], base_path: Path, dry_run: bool = False) -> None:
    """Ensure patterns are in .gitignore."""
    gitignore_path = base_path / ".gitignore"

    existing_patterns = set()
    if gitignore_path.exists():
        existing_patterns = set(gitignore_path.read_text().splitlines())

    patterns_to_add = [p for p in patterns if p not in existing_patterns]

    if not patterns_to_add:
        print("  All patterns already in .gitignore")
        return

    if dry_run:
        print(f"  [DRY-RUN] Would add to .gitignore: {patterns_to_add}")
        return

    with open(gitignore_path, "a") as f:
        f.write("\n# Auto-added by clean_git_unused_files.py\n")
        for p in patterns_to_add:
            f.write(f"{p}\n")

    print(f"  Added to .gitignore: {patterns_to_add}")


def clean_git_cache(patterns: list[str], dry_run: bool = False) -> None:
    """Remove patterns from git cache (staging area)."""
    for pattern in patterns:
        cmd = ["git", "rm", "-r", "--cached", "--ignore-unmatch", pattern]
        if dry_run:
            print(f"  [DRY-RUN] Would run: {' '.join(cmd)}")
        else:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0 and result.stdout:
                print(f"  Removed from git cache: {pattern}")


def main():
    parser = argparse.ArgumentParser(
        description="Clean unused files from directory and git history",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Patterns to clean:
  """ + "\n  ".join(PATTERNS_TO_CLEAN) + """

Examples:
  %(prog)s                      # Clean current directory
  %(prog)s --dry-run            # Preview changes without modifying
  %(prog)s --path ./src         # Clean specific directory
  %(prog)s --no-history         # Skip git history rewrite (faster)
        """,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be deleted without making changes",
    )
    parser.add_argument(
        "--path",
        type=str,
        default=".",
        help="Base path to clean (default: current directory)",
    )
    parser.add_argument(
        "--no-history",
        action="store_true",
        help="Skip rewriting git history (only delete files and update .gitignore)",
    )
    parser.add_argument(
        "--patterns",
        type=str,
        nargs="+",
        help="Additional patterns to clean (e.g., --patterns '*.log' '.env.local')",
    )

    args = parser.parse_args()
    base_path = Path(args.path).resolve()

    if not base_path.exists():
        print(f"Error: Path does not exist: {base_path}", file=sys.stderr)
        sys.exit(1)

    # Combine default patterns with any additional ones
    patterns = PATTERNS_TO_CLEAN.copy()
    if args.patterns:
        patterns.extend(args.patterns)

    print("=" * 60)
    print("Clean Git Unused Files")
    print("=" * 60)
    print(f"Base path: {base_path}")
    print(f"Patterns:  {patterns}")
    print(f"Dry run:   {args.dry_run}")
    print(f"Rewrite history: {not args.no_history}")
    print()

    # Step 1: Find and delete files from filesystem
    print("Step 1: Removing files from filesystem...")
    total_deleted = 0
    for pattern in patterns:
        files = find_files(base_path, pattern)
        if files:
            print(f"  Found {len(files)} file(s) matching '{pattern}'")
            total_deleted += remove_from_filesystem(files, args.dry_run)
        else:
            print(f"  No files found matching '{pattern}'")

    # Step 2: Remove from git cache
    print("\nStep 2: Removing from git cache...")
    clean_git_cache(patterns, args.dry_run)

    # Step 3: Add to .gitignore
    print("\nStep 3: Updating .gitignore...")
    add_to_gitignore(patterns, base_path, args.dry_run)

    # Step 4: Optionally rewrite git history
    if not args.no_history:
        print("\nStep 4: Rewriting git history...")
        print("  WARNING: This will rewrite git history!")
        if not args.dry_run:
            confirm = input("  Continue? [y/N]: ").strip().lower()
            if confirm != "y":
                print("  Skipped git history rewrite")
            else:
                for pattern in patterns:
                    remove_from_git_history(pattern, base_path, args.dry_run)
        else:
            for pattern in patterns:
                remove_from_git_history(pattern, base_path, args.dry_run)
    else:
        print("\nStep 4: Skipped git history rewrite (--no-history)")

    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    if args.dry_run:
        print("  This was a dry run. No changes were made.")
        print("  Run without --dry-run to apply changes.")
    else:
        print(f"  Files deleted: {total_deleted}")
        print("  .gitignore updated")
        if not args.no_history:
            print("  Git history rewritten (if confirmed)")
        print()
        print("  Next steps:")
        print("    git add .gitignore")
        print("    git commit -m 'chore: remove unused files and update .gitignore'")
        if not args.no_history:
            print("    git push --force-with-lease  # If history was rewritten")


if __name__ == "__main__":
    main()
