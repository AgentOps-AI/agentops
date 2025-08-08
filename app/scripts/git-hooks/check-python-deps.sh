#!/usr/bin/env bash

# $1 = Temporary directory path

if [ -z "$1" ]; then
  echo "Error: Temporary directory argument missing." >&2
  exit 1
fi

TEMP_DIR="$1"
STATUS_FILE="$TEMP_DIR/python_deps_status.txt"
MESSAGE_FILE="$TEMP_DIR/python_deps_message.txt"

PYTHON_DEPS_STATUS=0 # Assume success
FINAL_MESSAGE=""

# Check for ruff
if ! command -v ruff &> /dev/null; then
    PYTHON_DEPS_STATUS=2 # Warning
    FINAL_MESSAGE="Ruff not installed. Install with: uv pip install -r requirements-dev.txt"
else
    FINAL_MESSAGE="Python dependencies (ruff) found."
fi

# Write results to temporary files
echo "$PYTHON_DEPS_STATUS" > "$STATUS_FILE"
echo "$FINAL_MESSAGE" > "$MESSAGE_FILE"

# Always exit 0
exit 0 