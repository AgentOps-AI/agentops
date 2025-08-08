#!/usr/bin/env bash

# Function to get staged JS/TS files anywhere in the repo
get_staged_js_ts_files() {
  # Ensure grep returns 0 exit code even if no match found, and echo "" for empty result
  git diff --cached --name-only --diff-filter=ACMR | grep -E '\.(js|jsx|ts|tsx)$' || echo ""
}

# Function to run JS/TS checks (using npx for repo-wide application)
run_js_ts_checks() {
  local STAGED_JS_TS_FILES=$(get_staged_js_ts_files)
  local JS_STATUS=3  # Default to skipped

  if [ ! -z "$STAGED_JS_TS_FILES" ]; then
    echo "🔍 Running JS/TS checks on staged files:"
    echo "$STAGED_JS_TS_FILES"

    # Check if prettier is available via npx
    if ! npx prettier --version &> /dev/null; then
        echo "❌ Error: prettier is not installed"
        echo "💡 Please run the following command from the repository root:"
        echo "   npm install"
        JS_STATUS=1
        JS_MESSAGE="Prettier is not installed"
    else
        # Run prettier on staged JS/TS files (paths relative to repo root)
        echo "🔍 Formatting staged JS/TS files with prettier..."
        # Assumes prettier config is discoverable (e.g., .prettierrc at root)
        echo "$STAGED_JS_TS_FILES" | xargs npx prettier --write --ignore-unknown || true

        # Check if eslint is available via npx
        if ! npx eslint --version &> /dev/null; then
            echo "❌ Error: eslint is not installed"
            echo "💡 Please run the following command from the repository root:"
            echo "   npm install"
            JS_STATUS=1
            JS_MESSAGE="ESLint is not installed"
        else
            # Run eslint with auto-fix on staged JS/TS files
            echo "🔍 Linting and fixing staged JS/TS files with eslint..."
            # Assumes eslint config is discoverable (e.g., .eslintrc.js at root)
            echo "$STAGED_JS_TS_FILES" | xargs npx eslint --fix || true

            # Add back the fixed/formatted files (paths relative to repo root)
            echo "✅ Adding fixed/formatted JS/TS files back to staging..."
            echo "$STAGED_JS_TS_FILES" | xargs git add
            JS_STATUS=0
            JS_MESSAGE="JS/TS files formatted and linted"
        fi
    fi
  else
    JS_MESSAGE="No staged JS/TS files found"
    echo "✅ $JS_MESSAGE"
  fi

  return 0  # Always return success
}

# Run the checks
run_js_ts_checks 