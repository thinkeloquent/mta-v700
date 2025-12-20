#!/bin/bash
# Run script for Elastic Cloud (GCP) connection test

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if virtual environment exists
if [ ! -d "$SCRIPT_DIR/.venv" ]; then
    echo "Virtual environment not found. Running setup first..."
    "$SCRIPT_DIR/setup.sh"
fi

# Activate virtual environment and run
source "$SCRIPT_DIR/.venv/bin/activate"
python "$SCRIPT_DIR/connect.py"
