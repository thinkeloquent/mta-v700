#!/usr/bin/env python3
"""
Quick runner script - can be used without installing the package.

Usage:
    python run.py analyze . -o output.yaml
    python run.py analyze . -o output2.yaml
    python run.py info ./path/to/package
"""

import sys
from pathlib import Path

# Add src to path for direct execution
sys.path.insert(0, str(Path(__file__).parent / "src"))

from yaml_spec.cli import main

if __name__ == "__main__":
    main()
