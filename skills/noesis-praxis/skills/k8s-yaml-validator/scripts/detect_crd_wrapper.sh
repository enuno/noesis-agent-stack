#!/bin/bash
# Wrapper script for detect_crd.py that handles PyYAML dependency
# Creates a temporary venv if PyYAML is not available

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/detect_crd.py"

# Check if we have arguments
if [ $# -lt 1 ]; then
    echo "Usage: detect_crd_wrapper.sh <yaml-file>" >&2
    exit 1
fi

YAML_FILE="$1"

# Try to run with system Python first
if python3 -c "import yaml" 2>/dev/null; then
    # PyYAML is available, run directly
    python3 "$PYTHON_SCRIPT" "$YAML_FILE"
    exit $?
fi

# PyYAML not available. Noesis-reviewed skill copy: do not silently create a venv
# and pip-install a dependency on your behalf.
echo "Error: PyYAML is required but not found in system Python." >&2
echo "Install it yourself first, e.g.:" >&2
echo "  pip3 install --user pyyaml   # or your OS package manager" >&2
echo "then re-run this script." >&2
exit 1

# Run the script
python3 "$PYTHON_SCRIPT" "$YAML_FILE"

# Cleanup happens automatically via trap
