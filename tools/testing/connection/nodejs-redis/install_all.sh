#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "Installing dependencies for all Node.js Redis test suites..."

for dir in */; do
    if [ -f "${dir}package.json" ]; then
        echo ">>> Installing: ${dir}"
        (cd "$dir" && npm install --silent)
    fi
done

echo "All dependencies installed."
