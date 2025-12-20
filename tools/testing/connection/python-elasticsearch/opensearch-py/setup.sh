#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "[opensearch-py] Setting up virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo "[opensearch-py] Installing dependencies..."
pip install -r requirements.txt

echo "[opensearch-py] Setup complete."
