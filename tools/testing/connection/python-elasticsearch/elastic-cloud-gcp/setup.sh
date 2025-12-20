#!/bin/bash
# Setup script for Elastic Cloud (GCP) connection test

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Setting up Elastic Cloud (GCP) connection test..."

# Create virtual environment if it doesn't exist
if [ ! -d "$SCRIPT_DIR/.venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$SCRIPT_DIR/.venv"
fi

# Activate virtual environment
source "$SCRIPT_DIR/.venv/bin/activate"

# Install dependencies
echo "Installing dependencies..."
pip install -r "$SCRIPT_DIR/requirements.txt"

echo ""
echo "Setup complete!"
echo ""
echo "To run the test:"
echo "  1. Set your Elastic Cloud credentials:"
echo "     export ELASTIC_CLOUD_ID='your-deployment:base64-encoded-cloud-id'"
echo "     export ELASTICSEARCH_API_KEY='your-api-key'"
echo ""
echo "  2. Run the test:"
echo "     source $SCRIPT_DIR/.venv/bin/activate"
echo "     python $SCRIPT_DIR/connect.py"
echo ""
echo "  Or use the run script:"
echo "     $SCRIPT_DIR/run.sh"
