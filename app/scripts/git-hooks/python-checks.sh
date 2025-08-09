#!/usr/bin/env bash

# Function to get staged Python files anywhere in the repo
get_python_files() {
  # Ensure grep returns 0 exit code even if no match found, and echo "" for empty result
  git diff --cached --name-only --diff-filter=ACMR | grep '\.py$' || echo ""
}

# Function to run Python checks (using ruff - assumes ruff is installed and configured)
run_python_checks() {
  local STAGED_PYTHON_FILES=$(get_python_files)
  local PYTHON_STATUS=3  # Default to skipped

  if [ ! -z "$STAGED_PYTHON_FILES" ]; then
    echo "🔍 Running Python checks on staged files:"
    echo "$STAGED_PYTHON_FILES"

    # Check if uvx is available, fallback to ruff
    if command -v uvx &> /dev/null; then
        RUFF_CMD="uvx ruff"
        echo "🔍 Using uvx ruff (no local Python env required)"
    elif command -v ruff &> /dev/null; then
        RUFF_CMD="ruff"
        echo "🔍 Using local ruff installation"
    else
        echo "❌ Error: Neither uvx nor ruff is installed"
        echo "💡 Please install uv (recommended) or run:"
        echo "   uv pip install -r requirements-dev.txt"
        PYTHON_STATUS=1
        PYTHON_MESSAGE="Ruff is not installed (install uv or ruff)"
    fi

    if [ "$PYTHON_STATUS" != "1" ]; then
        # Run ruff format on staged Python files (paths relative to repo root)
        echo "🔍 Formatting staged Python files with $RUFF_CMD..."
        # Pass files directly to ruff; use --force-exclude if necessary based on ruff config
        echo "$STAGED_PYTHON_FILES" | xargs $RUFF_CMD format --force-exclude || true

        # Run ruff check with auto-fix on staged Python files
        echo "🔍 Linting and fixing staged Python files with $RUFF_CMD..."
        # Pass files directly to ruff; use --force-exclude if necessary
        echo "$STAGED_PYTHON_FILES" | xargs $RUFF_CMD check --fix --force-exclude || true

        # Add back the fixed/formatted files (paths relative to repo root)
        echo "✅ Adding fixed/formatted Python files back to staging..."
        echo "$STAGED_PYTHON_FILES" | xargs git add
        PYTHON_STATUS=0
        PYTHON_MESSAGE="Python files formatted and linted successfully"
    fi
  else
    PYTHON_MESSAGE="No staged Python files found"
    echo "✅ $PYTHON_MESSAGE"
  fi

  return 0  # Always return success
}

# Run the checks
run_python_checks 