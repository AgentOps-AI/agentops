#!/usr/bin/env bash

# $1 = Temporary directory path

if [ -z "$1" ]; then
  echo "Error: Temporary directory argument missing." >&2
  exit 1
fi

TEMP_DIR="$1"
STATUS_FILE="$TEMP_DIR/js_deps_status.txt"
MESSAGE_FILE="$TEMP_DIR/js_deps_message.txt"

JS_DEPS_STATUS=0 # Assume success
FINAL_MESSAGE=""
MISSING_TOOLS=""

# Check dependencies
if ! npx prettier --version &> /dev/null; then
    MISSING_TOOLS="Prettier"
    JS_DEPS_STATUS=2 # Warning
fi
if ! npx eslint --version &> /dev/null; then
    [ -n "$MISSING_TOOLS" ] && MISSING_TOOLS+=" and "
    MISSING_TOOLS+="ESLint"
    JS_DEPS_STATUS=2 # Warning
fi

if [ $JS_DEPS_STATUS -eq 0 ]; then
    FINAL_MESSAGE="JS/TS dependencies (prettier, eslint) found."
else
    FINAL_MESSAGE="$MISSING_TOOLS not installed. Run 'npm install'"
fi

# Write results to temporary files
echo "$JS_DEPS_STATUS" > "$STATUS_FILE"
echo "$FINAL_MESSAGE" > "$MESSAGE_FILE"

# Always exit 0
exit 0 