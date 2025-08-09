#!/usr/bin/env bash

# $1 = Temporary directory path

if [ -z "$1" ]; then
  echo "Error: Temporary directory argument missing." >&2
  exit 1
fi

TEMP_DIR="$1"
STATUS_FILE="$TEMP_DIR/unstaged_status.txt"
MESSAGE_FILE="$TEMP_DIR/unstaged_message.txt"

# Initialize status
UNSTAGED_STATUS=0  # Default to success
FINAL_MESSAGE="No unstaged changes detected"

# Check if formatting/fixing introduced unstaged changes to *staged* files
if ! git diff --cached --quiet --exit-code; then
  # echo "⚠️ Warning: Staged files were modified by formatters/linters." # Silenced
  # echo "   Please review the changes before committing."
  UNSTAGED_STATUS=2  # Warning
  FINAL_MESSAGE="Staged files were modified by hooks"
fi

# Check for *any* new unstaged changes (including untracked maybe? No, git diff doesn't show untracked)
if ! git diff --quiet --exit-code; then
  # Only update message if we didn't already detect modified staged files
  if [ $UNSTAGED_STATUS -ne 2 ]; then
      # echo "⚠️ Warning: Unstaged changes detected after running hooks." # Silenced
      # echo "   This might indicate issues during formatting or linting."
      UNSTAGED_STATUS=2  # Warning
      FINAL_MESSAGE="Other unstaged changes detected after hooks"
  fi
fi

# Write results to temporary files
echo "$UNSTAGED_STATUS" > "$STATUS_FILE"
echo "$FINAL_MESSAGE" > "$MESSAGE_FILE"

# Always exit 0 from this script
exit 0 
