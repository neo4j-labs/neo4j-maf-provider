#!/bin/bash
# Publish agent-framework-neo4j to PyPI
# Usage: ./scripts/publish.sh <pypi-token>

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <pypi-token>"
    echo "Example: $0 pypi-AgEIcHlwaS5vcmcC..."
    exit 1
fi

TOKEN="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "Cleaning dist/..."
rm -rf dist/

echo "Building package..."
uv build --package agent-framework-neo4j

echo "Publishing to PyPI..."
uv publish --token "$TOKEN"

echo "Done!"
