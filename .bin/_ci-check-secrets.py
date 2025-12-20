#!/usr/bin/env python3
"""
CI Secret Scanner - Scan files for secrets with interactive redaction.

This script scans for secrets in files WITHOUT modifying git or git history.
It lists found secrets and prompts for user confirmation before redacting.

Usage:
    python .bin/ci-check-secrets.py [options] [directory]

Options:
    --scan-only, -s     Scan only, don't prompt for redaction (default)
    --interactive, -i   Interactive mode: prompt before redacting each file
    --auto-redact, -a   Automatically redact all secrets without prompting
    --output FILE       Write report to file
    --format FORMAT     Output format: text or json (default: text)
    --verbose, -v       Show verbose output
    --list-patterns     List all secret patterns and exit
    --include-entropy   Include high-entropy patterns (may have false positives)
    --ignore DIR [DIR]  Directories to ignore (in addition to defaults)

Examples:
    python .bin/ci-check-secrets.py                    # Scan current directory
    python .bin/ci-check-secrets.py --stream ./        # Stream results as found
    python .bin/ci-check-secrets.py -i ./              # Interactive mode
    python .bin/ci-check-secrets.py -a ./              # Auto-redact all
    python .bin/ci-check-secrets.py -a --output-only -o report.json ./  # Output file only
    python .bin/ci-check-secrets.py --replace-secrets ./__SPECS__ ./     # Replace secrets with ****
    python .bin/ci-check-secrets.py --ignore __SPECS__ __BACKUP__ ./     # Ignore specific directories
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


@dataclass
class SecretMatch:
    """Represents a found secret."""
    file: str
    line_number: int
    pattern_name: str
    matched_text: str
    redacted_text: str
    line_content: str


@dataclass
class ScanResult:
    """Results from scanning."""
    files_scanned: int = 0
    secrets_found: int = 0
    secrets_redacted: int = 0
    files_modified: int = 0
    matches: list = field(default_factory=list)


# =============================================================================
# Secret Patterns (add more patterns here as needed)
# =============================================================================
SECRET_PATTERNS = {
    # API Keys - Major providers
    "openai_api_key": r"sk-[a-zA-Z0-9]{20,}",
    "openai_api_key_env": r"OPENAI_API_KEY\s*[=:]\s*['\"]?sk-[a-zA-Z0-9]{20,}['\"]?",
    "anthropic_api_key": r"sk-ant-[a-zA-Z0-9\-_]{20,}",
    "anthropic_api_key_env": r"ANTHROPIC_API_KEY\s*[=:]\s*['\"]?sk-ant-[a-zA-Z0-9\-_]{20,}['\"]?",

    # AWS
    "aws_access_key": r"AKIA[0-9A-Z]{16}",
    "aws_secret_key": r"(?i)(aws_secret_access_key|aws_secret_key)\s*[=:]\s*['\"]?[A-Za-z0-9/+=]{40}['\"]?",
    "aws_session_token": r"(?i)aws_session_token\s*[=:]\s*['\"]?[A-Za-z0-9/+=]{100,}['\"]?",

    # GitHub
    "github_token": r"ghp_[a-zA-Z0-9]{36}",
    "github_oauth": r"gho_[a-zA-Z0-9]{36}",
    "github_app_token": r"ghu_[a-zA-Z0-9]{36}",
    "github_refresh_token": r"ghr_[a-zA-Z0-9]{36}",
    "github_fine_grained": r"github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59}",

    # Google/GCP
    "google_api_key": r"AIza[0-9A-Za-z\-_]{35}",
    "google_oauth_id": r"[0-9]+-[a-z0-9]{32}\.apps\.googleusercontent\.com",
    "gcp_service_account": r'"type"\s*:\s*"service_account"',

    # Slack
    "slack_token": r"xox[baprs]-[0-9]{10,13}-[0-9]{10,13}[a-zA-Z0-9-]*",
    "slack_webhook": r"https://hooks\.slack\.com/services/T[a-zA-Z0-9_]+/B[a-zA-Z0-9_]+/[a-zA-Z0-9_]+",

    # Stripe
    "stripe_secret": r"sk_live_[a-zA-Z0-9]{24,}",
    "stripe_publishable": r"pk_live_[a-zA-Z0-9]{24,}",
    "stripe_test_secret": r"sk_test_[a-zA-Z0-9]{24,}",

    # Twilio
    "twilio_api_key": r"SK[a-f0-9]{32}",
    "twilio_auth_token": r"(?i)twilio.*['\"][a-f0-9]{32}['\"]",

    # SendGrid
    "sendgrid_api_key": r"SG\.[a-zA-Z0-9\-_]{22}\.[a-zA-Z0-9\-_]{43}",

    # Mailchimp
    "mailchimp_api_key": r"[a-f0-9]{32}-us[0-9]{1,2}",

    # NPM
    "npm_token": r"npm_[a-zA-Z0-9]{36}",

    # PyPI
    "pypi_token": r"pypi-[a-zA-Z0-9]{50,}",

    # Docker Hub
    "docker_auth": r'"auth"\s*:\s*"[A-Za-z0-9+/=]{20,}"',

    # Atlassian (Jira/Confluence)
    "atlassian_token": r"(?i)(jira_api_token|confluence_api_token|atlassian_api_token)\s*[=:]\s*['\"]?[A-Za-z0-9]{24,}['\"]?",

    # Generic patterns (require longer tokens to avoid false positives)
    "bearer_token": r"(?i)bearer\s+[a-zA-Z0-9\-_.~+/]{20,}=*",
    "basic_auth": r"(?i)basic\s+[a-zA-Z0-9+/]{16,}=*",
    "authorization_header": r'(?i)["\']?authorization["\']?\s*[=:]\s*["\'][^"\']{20,}["\']',

    # Private keys
    "private_key_rsa": r"-----BEGIN RSA PRIVATE KEY-----",
    "private_key_openssh": r"-----BEGIN OPENSSH PRIVATE KEY-----",
    "private_key_ec": r"-----BEGIN EC PRIVATE KEY-----",
    "private_key_generic": r"-----BEGIN PRIVATE KEY-----",
    "private_key_pgp": r"-----BEGIN PGP PRIVATE KEY BLOCK-----",

    # Database connection strings
    "postgres_uri": r"postgres(?:ql)?://[^:]+:[^@]+@[^/]+/\w+",
    "mysql_uri": r"mysql://[^:]+:[^@]+@[^/]+/\w+",
    "mongodb_uri": r"mongodb(?:\+srv)?://[^:]+:[^@]+@[^/]+",
    "redis_uri": r"redis(?:s)?://[^:]+:[^@]+@[^/]+",

    # Environment variable assignments with secrets
    "env_password": r"(?i)(password|passwd|pwd)\s*[=:]\s*['\"]?[^\s'\"]{8,}['\"]?",
    "env_secret": r"(?i)(secret|secret_key|secretkey)\s*[=:]\s*['\"]?[^\s'\"]{8,}['\"]?",
    "env_api_key": r"(?i)(api_key|apikey)\s*[=:]\s*['\"]?[^\s'\"]{16,}['\"]?",
    "env_token": r"(?i)(access_token|auth_token|api_token)\s*[=:]\s*['\"]?[^\s'\"]{16,}['\"]?",

    # Figma
    "figma_token": r"figd_[a-zA-Z0-9\-_]{40,}",
    "figma_token_env": r"FIGMA_TOKEN\s*[=:]\s*['\"]?figd_[a-zA-Z0-9\-_]{40,}['\"]?",

    # Gemini/Google AI
    "gemini_api_key_env": r"GEMINI_API_KEY\s*[=:]\s*['\"]?[A-Za-z0-9\-_]{30,}['\"]?",

    # DigitalOcean
    "digitalocean_token": r"dop_v1_[a-f0-9]{64}",
    "digitalocean_spaces": r"(?i)spaces.*secret.*[=:]\s*['\"]?[A-Za-z0-9/+=]{40,}['\"]?",
}

# High-entropy patterns (disabled by default)
HIGH_ENTROPY_PATTERNS = {
    "high_entropy_hex": r"(?<![a-zA-Z0-9])[a-f0-9]{32,64}(?![a-zA-Z0-9])",
    "high_entropy_base64": r"(?<![a-zA-Z0-9+/])[A-Za-z0-9+/]{40,}={0,2}(?![a-zA-Z0-9+/=])",
}

# Patterns to exclude (false positives)
EXCLUDE_PATTERNS = [
    r"test-key",
    r"example-key",
    r"your-api-key",
    r"<api_key>",
    r"\$\{[^}]+\}",  # Variable interpolation
    r"process\.env\.",  # Environment variable reference
    r"os\.getenv\(",  # Python env reference
    r"os\.environ\[",  # Python env reference
    r"os\.environ\.get\(",  # Python env reference
    # YAML config env var references (key names, not actual values)
    r"env_\w+:\s*['\"]?[A-Z_]+['\"]?",  # env_client_secret: "AKAMAI_CLIENT_SECRET"
    r":\s*['\"]?[A-Z][A-Z0-9_]{3,}['\"]?\s*$",  # value is ENV_VAR_NAME (all caps with underscores)
    # Example/placeholder tokens in docs
    r"override-token",  # Example token
    r"example-token",  # Example token
    r"test-token",  # Test token
    r"sample-token",  # Sample token
    r"your-token",  # Placeholder token
    r"Bearer\s+\{",  # Template patterns
    r"Bearer\s+<",  # Template patterns
    r"Bearer\s+\.\.\.",  # Documentation ellipsis
    r"Bearer\s+\$",  # Variable reference
    r"Bearer\s+token",  # "Bearer token" documentation/description
    r"Bearer\s+auth",  # "Bearer auth" documentation/description
    r"bearer\s+auth",  # "bearer auth" in test descriptions
    r"\*\s+Bearer",  # JSDoc comments: * Bearer token handler
    r"//\s*Bearer",  # Single-line comments
    r"#\s*Bearer",  # Python/shell comments
    r"ApiKey",  # Type/class names
    r"apiKey['\"]?\s*:",  # Key names in objects
    r"api_key['\"]?\s*:",  # Key names in objects
    r"getApiKey",  # Method names
    r"get_api_key",  # Method names
    r"auth_types",  # Documentation
    r"AuthHandler",  # Class names
    r"formatAuthHeaderValue",  # Method names
    r"format_auth_header",  # Method names
    r"/health",  # URL paths
    r"/search",  # URL paths
    r"com/[a-z]+/[a-z]+",  # Package paths
    r"@[a-z]+/",  # NPM scopes
    # Type hints and annotations
    r":\s*str\]?$",  # Type hint ending with str
    r":\s*Optional\[",  # Optional type hints
    r"password:\s*str",  # Type hint
    r"secret:\s*str",  # Type hint
    r"api_key:\s*str",  # Type hint
    r"token:\s*str",  # Type hint
    # Python code patterns
    r"\.get\(['\"]password",  # dict.get("password")
    r"\.get\(['\"]api_key",  # dict.get("api_key")
    r"\.get\(['\"]secret",  # dict.get("secret")
    r"\.get\(['\"]token",  # dict.get("token")
    r"\[.password.\]",  # dict["password"]
    r"f['\"].*\{.*password",  # f-string with password variable
    r"f['\"].*\{.*secret",  # f-string with secret variable
    # Function calls with token/key in name
    r"get_api_token\(",  # factory.get_api_token("github")
    r"get_token\(",  # get_token()
    r"api_token\s*=",  # api_token = ...
    r"\.get_api_key\(",  # obj.get_api_key()
    # Keyword argument with variable reference (not literal value)
    r"password\s*=\s*password",  # password=password (variable)
    r"secret\s*=\s*secret",  # secret=secret (variable)
    r"token\s*=\s*token",  # token=token (variable)
    r"api_key\s*=\s*api_key",  # api_key=api_key (variable)
    r"pass\s*=\s*pass\b",  # pass=pass (variable, common short name)
    r"passwd\s*=\s*passwd",  # passwd=passwd (variable)
    # Logging/masking patterns
    r"mask.*password",
    r"redact.*secret",
    r"REDACTED",
]

# File extensions to skip (binary files)
SKIP_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.ico', '.pdf', '.zip', '.tar', '.gz',
    '.bz2', '.xz', '.7z', '.rar', '.exe', '.dll', '.so', '.dylib', '.bin',
    '.woff', '.woff2', '.ttf', '.eot', '.mp3', '.mp4', '.wav', '.avi', '.mov',
    '.pyc', '.pyo', '.class', '.o', '.obj', '.a', '.lib',
}

# Directories to skip
SKIP_DIRECTORIES = {
    '.git', 'node_modules', '__pycache__', '.venv', 'venv', 'env',
    '.tox', '.pytest_cache', '.mypy_cache', 'dist', 'build', '.eggs',
    'docs',  # Documentation often contains example credentials
    '*.egg-info', '.next', '.nuxt', '.cache', '__SPECS__', '__STAGE__'
}


def should_exclude(text: str, line_content: str = "") -> bool:
    """Check if matched text should be excluded as false positive."""
    combined = f"{text} {line_content}"
    for pattern in EXCLUDE_PATTERNS:
        if re.search(pattern, combined, re.IGNORECASE):
            return True

    # Additional context-based exclusions
    context_excludes = [
        "test case", "test_", "_test", "mock", "fixture",
        "documentation", "docstring", "comment", "example",
        "# ", "//", "/*", "'''", '"""',
        "class ", "def ", "function ", "const ", "let ", "var ",
        "interface ", "type ", "enum ",
        "| ", "|-", "+--",  # Table formatting
        "format", "returns", "description",
        "bearer_", "basic_", "x-api-key",  # Type names
        "auth_type", "auth type",
        "base64(",  # Encoding examples
        "{key}", "{token}", "{password}",  # Template placeholders
        # Python typing patterns
        ": str", ": optional[", ": str =", ": str]",
        "-> str", "-> optional",
        # Variable access patterns
        ".password", ".secret", ".api_key", ".token",
        "['password", '["password', "['secret", '["secret',
        "['api_key", '["api_key', "['token", '["token',
        # Common false positive contexts
        "self.password", "self.secret", "self.api_key",
        "config.password", "config.secret",
        "db_config.password", "redis_config.password",
        # Logging patterns
        "_mask_sensitive", "mask_sensitive",
        "password={'***'", "password=***",
        # Tests directory
        "/tests_", "/test_", "_test.py", "test_.py",
    ]
    line_lower = line_content.lower()
    for ctx in context_excludes:
        if ctx in line_lower:
            return True

    return False


def redact_secret(text: str, pattern_name: str) -> str:
    """Redact a secret, keeping some context for identification."""
    if len(text) <= 8:
        return "[REDACTED]"

    # Keep first and last few chars for context
    prefix_len = min(4, len(text) // 4)
    suffix_len = min(4, len(text) // 4)

    return f"{text[:prefix_len]}...REDACTED...{text[-suffix_len:]}"


def scan_line(line: str, line_number: int, file_path: str, include_entropy: bool = False) -> list[SecretMatch]:
    """Scan a single line for secrets."""
    matches = []

    patterns_to_check = dict(SECRET_PATTERNS)
    if include_entropy:
        patterns_to_check.update(HIGH_ENTROPY_PATTERNS)

    for pattern_name, pattern in patterns_to_check.items():
        try:
            for match in re.finditer(pattern, line):
                matched_text = match.group(0)

                if should_exclude(matched_text, line):
                    continue

                if "example" in line.lower() or "sample" in line.lower():
                    continue

                redacted = redact_secret(matched_text, pattern_name)

                matches.append(SecretMatch(
                    file=file_path,
                    line_number=line_number,
                    pattern_name=pattern_name,
                    matched_text=matched_text,
                    redacted_text=redacted,
                    line_content=line.strip()[:200],
                ))
        except re.error:
            continue

    return matches


def scan_file(file_path: Path, verbose: bool = False, include_entropy: bool = False) -> list[SecretMatch]:
    """Scan a single file for secrets."""
    matches = []

    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line_number, line in enumerate(f, 1):
                line_matches = scan_line(line, line_number, str(file_path), include_entropy)
                matches.extend(line_matches)

                if verbose and line_matches:
                    for m in line_matches:
                        print(f"  [{m.pattern_name}] Line {m.line_number}: {m.redacted_text}")
    except Exception as e:
        if verbose:
            print(f"  Error reading file: {e}", file=sys.stderr)

    return matches


def should_skip_directory(dir_name: str, extra_ignore: set[str] | None = None) -> bool:
    """Check if directory should be skipped."""
    if dir_name.startswith('.'):
        return True
    if dir_name in SKIP_DIRECTORIES:
        return True
    if extra_ignore and dir_name in extra_ignore:
        return True
    return False


def collect_files(directory: Path, extra_ignore: set[str] | None = None) -> list[Path]:
    """Collect all scannable files, sorted by path for grouped output."""
    files_to_scan = []

    for root, dirs, files in os.walk(directory):
        # Filter out directories to skip
        dirs[:] = sorted([d for d in dirs if not should_skip_directory(d, extra_ignore)])

        for filename in files:
            if filename.startswith('.'):
                continue

            file_path = Path(root) / filename

            if file_path.suffix.lower() in SKIP_EXTENSIONS:
                continue

            files_to_scan.append(file_path)

    # Sort by full path so directories are grouped together
    return sorted(files_to_scan, key=lambda p: str(p))


def scan_directory(directory: Path, verbose: bool = False, include_entropy: bool = False, stream: bool = False, extra_ignore: set[str] | None = None) -> ScanResult:
    """Scan a directory for secrets (scan only, no modifications)."""
    result = ScanResult()

    # Collect and sort files first
    files_to_scan = collect_files(directory, extra_ignore)

    for file_path in files_to_scan:
        result.files_scanned += 1

        if verbose:
            print(f"Scanning: {file_path}", flush=True)

        matches = scan_file(file_path, verbose, include_entropy)

        if matches:
            result.secrets_found += len(matches)
            result.matches.extend(matches)

            # Stream output: print matches as they're found
            if stream:
                print(f"\n{file_path}:", flush=True)
                for m in matches:
                    print(f"  Line {m.line_number} [{m.pattern_name}]: {m.redacted_text}", flush=True)

    return result


def display_file_secrets(file_path: str, matches: list[SecretMatch]) -> None:
    """Display secrets found in a file."""
    print(f"\n{'=' * 70}")
    print(f"FILE: {file_path}")
    print(f"{'=' * 70}")
    print(f"Found {len(matches)} secret(s):\n")

    for i, m in enumerate(matches, 1):
        print(f"  {i}. Line {m.line_number} [{m.pattern_name}]")
        print(f"     Original: {m.matched_text[:50]}{'...' if len(m.matched_text) > 50 else ''}")
        print(f"     Redacted: {m.redacted_text}")
        print(f"     Context:  {m.line_content[:80]}{'...' if len(m.line_content) > 80 else ''}")
        print()


def prompt_user_for_file(file_path: str, matches: list[SecretMatch]) -> bool:
    """Prompt user to confirm redaction of secrets in a file."""
    display_file_secrets(file_path, matches)

    while True:
        response = input(f"Redact {len(matches)} secret(s) in this file? [y/n/q] (y=yes, n=no, q=quit): ").strip().lower()
        if response in ('y', 'yes'):
            return True
        elif response in ('n', 'no'):
            return False
        elif response in ('q', 'quit'):
            print("\nAborted by user.")
            sys.exit(0)
        else:
            print("Please enter 'y' for yes, 'n' for no, or 'q' to quit.")


def redact_secrets_in_file(file_path: Path, matches: list[SecretMatch]) -> int:
    """Redact secrets in a file. Returns number of secrets redacted."""
    if not matches:
        return 0

    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        # Group matches by line number
        by_line: dict[int, list[SecretMatch]] = {}
        for m in matches:
            if m.line_number not in by_line:
                by_line[m.line_number] = []
            by_line[m.line_number].append(m)

        # Apply replacements
        for line_num, line_matches in by_line.items():
            if line_num <= len(lines):
                line = lines[line_num - 1]
                for m in line_matches:
                    line = line.replace(m.matched_text, m.redacted_text)
                lines[line_num - 1] = line

        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)

        return len(matches)
    except Exception as e:
        print(f"Error modifying {file_path}: {e}", file=sys.stderr)
        return 0


def replace_secrets_with_stars(file_path: Path, matches: list[SecretMatch]) -> int:
    """Replace secrets with **** in a file. Returns number of secrets replaced."""
    if not matches:
        return 0

    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        # Group matches by line number
        by_line: dict[int, list[SecretMatch]] = {}
        for m in matches:
            if m.line_number not in by_line:
                by_line[m.line_number] = []
            by_line[m.line_number].append(m)

        # Apply replacements with ****
        for line_num, line_matches in by_line.items():
            if line_num <= len(lines):
                line = lines[line_num - 1]
                for m in line_matches:
                    line = line.replace(m.matched_text, "****")
                lines[line_num - 1] = line

        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)

        return len(matches)
    except Exception as e:
        print(f"Error modifying {file_path}: {e}", file=sys.stderr)
        return 0


def format_report(result: ScanResult, format_type: str = "text") -> str:
    """Format scan results as text or JSON."""
    if format_type == "json":
        return json.dumps({
            "files_scanned": result.files_scanned,
            "secrets_found": result.secrets_found,
            "secrets_redacted": result.secrets_redacted,
            "files_modified": result.files_modified,
            "matches": [asdict(m) for m in result.matches]
        }, indent=2)

    # Text format
    lines = [
        "=" * 60,
        "SECRET SCAN REPORT",
        "=" * 60,
        f"Files scanned:    {result.files_scanned}",
        f"Secrets found:    {result.secrets_found}",
        f"Secrets redacted: {result.secrets_redacted}",
        f"Files modified:   {result.files_modified}",
        "",
    ]

    if result.matches:
        lines.append("MATCHES:")
        lines.append("-" * 60)

        # Group by file
        by_file: dict[str, list[SecretMatch]] = {}
        for m in result.matches:
            if m.file not in by_file:
                by_file[m.file] = []
            by_file[m.file].append(m)

        for file_path, matches in by_file.items():
            lines.append(f"\n{file_path}:")
            for m in matches:
                lines.append(f"  Line {m.line_number} [{m.pattern_name}]:")
                lines.append(f"    Found: {m.redacted_text}")
    else:
        lines.append("No secrets found.")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Scan files for secrets with interactive redaction (no git history changes).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python .bin/ci-check-secrets.py                    # Scan current directory
  python .bin/ci-check-secrets.py --stream ./        # Stream results as found
  python .bin/ci-check-secrets.py -s ./src           # Scan only (no changes)
  python .bin/ci-check-secrets.py -i ./              # Interactive mode
  python .bin/ci-check-secrets.py -a ./              # Auto-redact all
  python .bin/ci-check-secrets.py -a --output-only -o report.json ./  # Output file only
  python .bin/ci-check-secrets.py --replace-secrets ./__SPECS__ ./     # Replace secrets with ****
  python .bin/ci-check-secrets.py --ignore __SPECS__ __BACKUP__ ./     # Ignore directories

Exit codes:
  0 - No secrets found (or all redacted in auto mode)
  1 - Secrets found (useful for CI pipelines)
        """
    )

    parser.add_argument("directory", nargs="?", default=".",
                        help="Directory to scan (default: current directory)")
    parser.add_argument("-s", "--scan-only", action="store_true", default=True,
                        help="Scan only, don't modify files (default)")
    parser.add_argument("-i", "--interactive", action="store_true",
                        help="Interactive mode: prompt before redacting each file")
    parser.add_argument("-a", "--auto-redact", action="store_true",
                        help="Automatically redact all secrets without prompting")
    parser.add_argument("-o", "--output", type=str,
                        help="Output file for report")
    parser.add_argument("-f", "--format", choices=["text", "json"], default="text",
                        help="Output format (default: text)")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Verbose output")
    parser.add_argument("--list-patterns", action="store_true",
                        help="List all secret patterns and exit")
    parser.add_argument("--include-entropy", action="store_true",
                        help="Include high-entropy patterns (may have false positives)")
    parser.add_argument("--stream", action="store_true",
                        help="Stream output as secrets are found (real-time)")
    parser.add_argument("--output-only", action="store_true",
                        help="Suppress console output, write only to output file (requires -o)")
    parser.add_argument("--replace-secrets", type=str, metavar="DIR",
                        help="Replace secrets with **** in files under specified directory")
    parser.add_argument("--ignore", type=str, nargs="+", metavar="DIR",
                        help="Directories to ignore (e.g., --ignore node_modules .venv)")

    args = parser.parse_args()

    if args.list_patterns:
        print("Available secret patterns:")
        print("-" * 40)
        for name in sorted(SECRET_PATTERNS.keys()):
            print(f"  {name}")
        print("\nHigh-entropy patterns (use --include-entropy):")
        for name in sorted(HIGH_ENTROPY_PATTERNS.keys()):
            print(f"  {name}")
        return 0

    # Validate --output-only requires --output
    if args.output_only and not args.output:
        print("Error: --output-only requires -o/--output to be specified", file=sys.stderr)
        return 1

    quiet = args.output_only

    directory = Path(args.directory).resolve()

    if not directory.exists():
        print(f"Error: Directory '{directory}' does not exist.", file=sys.stderr)
        return 1

    if not directory.is_dir():
        print(f"Error: '{directory}' is not a directory.", file=sys.stderr)
        return 1

    # Determine mode
    mode = "SCAN ONLY"
    if args.replace_secrets:
        mode = "REPLACE SECRETS"
    elif args.interactive:
        mode = "INTERACTIVE"
    elif args.auto_redact:
        mode = "AUTO-REDACT"

    if not quiet:
        print("=" * 60)
        print("CI SECRET SCANNER")
        print("=" * 60)
        print(f"Directory: {directory}")
        print(f"Mode:      {mode}")
        if args.replace_secrets:
            print(f"Replace in: {args.replace_secrets}")
        print(f"Note:      This tool does NOT modify git history")
        print("=" * 60)
        print()

    # Convert ignore list to set if provided
    extra_ignore = set(args.ignore) if args.ignore else None

    # Scan directory
    result = scan_directory(
        directory,
        verbose=args.verbose and not quiet,
        include_entropy=args.include_entropy,
        stream=args.stream and not quiet,
        extra_ignore=extra_ignore,
    )

    if result.secrets_found == 0:
        if not quiet:
            print("No secrets found.")
        if args.output:
            with open(args.output, 'w') as f:
                f.write(format_report(result, args.format))
            if not quiet:
                print(f"\nReport written to: {args.output}")
        return 0

    if not quiet:
        print(f"\nFound {result.secrets_found} secret(s) in {len(set(m.file for m in result.matches))} file(s).")

    # Handle based on mode
    if args.replace_secrets:
        # Replace secrets with **** in files under specified directory
        replace_dir = Path(args.replace_secrets).resolve()
        if not replace_dir.exists():
            print(f"Error: Replace directory '{replace_dir}' does not exist.", file=sys.stderr)
            return 1

        # Group matches by file
        by_file: dict[str, list[SecretMatch]] = {}
        for m in result.matches:
            if m.file not in by_file:
                by_file[m.file] = []
            by_file[m.file].append(m)

        files_to_replace = [(f, matches) for f, matches in by_file.items() if f.startswith(str(replace_dir))]

        if not files_to_replace:
            if not quiet:
                print(f"\nNo files with secrets found under {replace_dir}")
        else:
            total_secrets = sum(len(matches) for _, matches in files_to_replace)
            if not quiet:
                print(f"\nFiles to update under {replace_dir}:")
                for f, matches in files_to_replace:
                    print(f"  {f} ({len(matches)} secret(s))")
                print()

            confirm = input(f"Replace {total_secrets} secret(s) in {len(files_to_replace)} file(s) with ****? [y/N]: ").strip().lower()
            if confirm == 'y':
                for file_path, matches in files_to_replace:
                    replaced = replace_secrets_with_stars(Path(file_path), matches)
                    result.secrets_redacted += replaced
                    if replaced > 0:
                        result.files_modified += 1
                        if not quiet:
                            print(f"  Replaced {replaced} secret(s) in {file_path}")

                if not quiet:
                    print(f"\nReplaced secrets in {result.files_modified} file(s)")
            else:
                if not quiet:
                    print("Aborted.")

    elif args.interactive or args.auto_redact:
        # Group matches by file
        by_file: dict[str, list[SecretMatch]] = {}
        for m in result.matches:
            if m.file not in by_file:
                by_file[m.file] = []
            by_file[m.file].append(m)

        for file_path, matches in by_file.items():
            if args.interactive:
                if prompt_user_for_file(file_path, matches):
                    redacted = redact_secrets_in_file(Path(file_path), matches)
                    result.secrets_redacted += redacted
                    if redacted > 0:
                        result.files_modified += 1
                        print(f"  Redacted {redacted} secret(s) in {file_path}")
                else:
                    print(f"  Skipped {file_path}")
            elif args.auto_redact:
                redacted = redact_secrets_in_file(Path(file_path), matches)
                result.secrets_redacted += redacted
                if redacted > 0:
                    result.files_modified += 1
                    if not quiet:
                        print(f"  Redacted {redacted} secret(s) in {file_path}")

        if not quiet:
            print()
            print("=" * 60)
            print("SUMMARY")
            print("=" * 60)
            print(f"Files scanned:    {result.files_scanned}")
            print(f"Secrets found:    {result.secrets_found}")
            print(f"Secrets redacted: {result.secrets_redacted}")
            print(f"Files modified:   {result.files_modified}")
    else:
        # Scan only mode - just display report
        if not quiet:
            report = format_report(result, args.format)
            print()
            print(report)

    # Write report if requested
    if args.output:
        with open(args.output, 'w') as f:
            f.write(format_report(result, args.format))
        if not quiet:
            print(f"\nReport written to: {args.output}")

    # Return non-zero if secrets were found and not all redacted
    remaining = result.secrets_found - result.secrets_redacted
    if remaining > 0:
        if not quiet:
            print(f"\nWARNING: {remaining} secret(s) remain in files.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
