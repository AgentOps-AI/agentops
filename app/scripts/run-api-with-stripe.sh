#!/bin/bash
# This script automates running the API with Stripe webhook listening.
# It fetches the webhook secret, starts 'stripe listen' in the background,
# and then runs the provided API command with the secret injected.

set -e # Exit immediately if a command exits with a non-zero status.

# --- Configuration ---
DEFAULT_API_PORT="8000" # Default API port if not provided as first argument
# Events Stripe CLI should listen for.
STRIPE_EVENTS="checkout.session.completed,subscription_schedule.canceled,subscription_schedule.completed,subscription_schedule.created,subscription_schedule.expiring,subscription_schedule.released"
# Command to run the API will be passed as arguments to this script after the optional port.

# --- Helper Functions ---
function check_command() {
  if ! command -v "$1" &> /dev/null; then
    echo "Error: Required command '$1' not found in PATH."
    echo "Please install '$1' and ensure it's in your PATH."
    exit 1
  fi
}

STRIPE_LISTEN_PID=""
SECRET_OUTPUT_FILE=""

function cleanup() {
  echo "Cleaning up... (called from LNO: ${BASH_LINENO[0]})"
  set +x # Turn off command printing during cleanup to reduce noise
  if [ -n "$STRIPE_LISTEN_PID" ] && ps -p "$STRIPE_LISTEN_PID" > /dev/null; then
    echo "Stopping background Stripe listen process (PID: $STRIPE_LISTEN_PID)..."
    kill "$STRIPE_LISTEN_PID"
    wait "$STRIPE_LISTEN_PID" 2>/dev/null || true # Allow wait to not cause script exit
    echo "Stripe listen process stopped."
  elif [ -n "$STRIPE_LISTEN_PID" ]; then # If PID was set but process not found
    echo "Background Stripe listen process (PID: $STRIPE_LISTEN_PID) was expected but not found or already stopped."
  else # If PID was never set for persistent listener
    echo "Background Stripe listen process was not started or its PID was not captured."
  fi
  if [ -n "$SECRET_OUTPUT_FILE" ] && [ -f "$SECRET_OUTPUT_FILE" ]; then
    echo "Removing temporary secret file (if not preserved for error): $SECRET_OUTPUT_FILE"
    # Check if we are exiting due to an error before removing, to preserve for inspection
    # This is a simple check; a more robust way would be to pass exit code to cleanup.
    # For now, if an error occurred in secret retrieval, it would have exited before successful rm.
    rm -f "$SECRET_OUTPUT_FILE"
  fi
}

# --- Main Script ---

# Trap exit signals to ensure cleanup
trap cleanup EXIT SIGINT SIGTERM

# Check for required tools
check_command "stripe"
check_command "mktemp"
check_command "grep"
check_command "sed"

# Determine API Port and API command
API_PORT="${1:-$DEFAULT_API_PORT}"
if [[ "$1" =~ ^[0-9]+$ ]]; then # if first arg is a port number
  shift # remove port from arguments, rest are the API command
fi

if [ $# -eq 0 ]; then
  echo "Error: No API command provided."
  echo "Usage: $0 [API_PORT] <command_to_run_api...>"
  echo "Example: $0 8000 docker compose up my-api-service"
  exit 1
fi
API_RUN_COMMAND=("$@")

echo "Attempting to obtain Stripe webhook secret..."
echo "You may be prompted to authenticate with Stripe in your browser."

SECRET_OUTPUT_FILE=$(mktemp)
if [ -z "$SECRET_OUTPUT_FILE" ]; then
    echo "Error: Could not create temporary file."
    exit 1
fi
echo "Stripe CLI output for secret retrieval will be logged to: $SECRET_OUTPUT_FILE"

stripe listen --format JSON --forward-to "http://localhost:${API_PORT}/v4/stripe-webhook" --events "${STRIPE_EVENTS}" --skip-update > "${SECRET_OUTPUT_FILE}" 2>&1 &
STRIPE_SECRET_PID_TEMP=$!
echo "Started temporary Stripe listen for secret (PID: $STRIPE_SECRET_PID_TEMP). Waiting for secret..."

sleep 1 

if ! ps -p "$STRIPE_SECRET_PID_TEMP" > /dev/null; then
    echo "Error: Stripe listen process for secret retrieval (PID: $STRIPE_SECRET_PID_TEMP) seems to have died immediately after start."
    echo "--- Output from Stripe CLI (from $SECRET_OUTPUT_FILE) --- BEGIN --- "
    cat "${SECRET_OUTPUT_FILE}"
    echo "--- Output from Stripe CLI (from $SECRET_OUTPUT_FILE) ---  END  --- "
    exit 1 
fi    

timeout=300 # 5 minutes
elapsed=0
secret_found=false
WEBHOOK_SECRET=""

while [ $elapsed -lt $timeout ]; do
  if ! ps -p "$STRIPE_SECRET_PID_TEMP" > /dev/null; then
    echo "Error: Stripe listen process for secret retrieval (PID: $STRIPE_SECRET_PID_TEMP) died prematurely during wait loop."
    echo "--- Output from Stripe CLI (from $SECRET_OUTPUT_FILE) --- BEGIN --- "
    cat "${SECRET_OUTPUT_FILE}"
    echo "--- Output from Stripe CLI (from $SECRET_OUTPUT_FILE) ---  END  --- "
    exit 1 
  fi

  if grep -q "Your webhook signing secret is" "${SECRET_OUTPUT_FILE}"; then
    WEBHOOK_SECRET=$(grep "Your webhook signing secret is" "${SECRET_OUTPUT_FILE}" | sed -n 's/.*Your webhook signing secret is \(whsec_[^[:space:]]*\).*/\1/p' | tr -d '[:space:]')
    if [ -n "$WEBHOOK_SECRET" ]; then
      secret_found=true
      echo "Stripe webhook secret identified from text output."
      break
    fi
  fi
  
  JQ_SECRET=$(jq -r '.secret' "${SECRET_OUTPUT_FILE}" 2>/dev/null)
  if [ $? -eq 0 ] && [ -n "$JQ_SECRET" ] && [ "$JQ_SECRET" != "null" ]; then
    WEBHOOK_SECRET=$JQ_SECRET
    secret_found=true
    echo "Stripe webhook secret identified from JSON output."
    break
  fi
  
  sleep 1
  elapsed=$((elapsed + 1))
  if [ $((elapsed % 10)) -eq 0 ]; then
    echo "Still waiting for Stripe secret... ($elapsed/$timeout seconds) (Temp PID: $STRIPE_SECRET_PID_TEMP is alive)"
  fi
done

if ps -p "$STRIPE_SECRET_PID_TEMP" > /dev/null; then
  echo "Stopping temporary Stripe listen for secret (PID: $STRIPE_SECRET_PID_TEMP)..."
  kill "$STRIPE_SECRET_PID_TEMP"
  wait "$STRIPE_SECRET_PID_TEMP" 2>/dev/null || true
  echo "Temporary Stripe listen stopped."
fi

if [ "$secret_found" = false ]; then 
  echo "Error: Timed out waiting for Stripe webhook secret after $timeout seconds."
  echo "--- Final output from Stripe CLI (from $SECRET_OUTPUT_FILE) --- BEGIN --- "
  cat "${SECRET_OUTPUT_FILE}"
  echo "--- Final output from Stripe CLI (from $SECRET_OUTPUT_FILE) ---  END  --- "
  echo "!!! Preserving temporary secret file for inspection due to timeout: $SECRET_OUTPUT_FILE !!!"
  exit 1 
fi

if [ -z "$WEBHOOK_SECRET" ]; then 
  echo "Error: Logic failure - secret_found is true but WEBHOOK_SECRET is empty."
  echo "!!! Preserving temporary secret file for inspection due to empty secret: $SECRET_OUTPUT_FILE !!!"
  exit 1 
fi

if [ -f "$SECRET_OUTPUT_FILE" ]; then
    echo "Secret obtained, removing temporary file: $SECRET_OUTPUT_FILE"
    rm -f "$SECRET_OUTPUT_FILE"
    SECRET_OUTPUT_FILE="" 
fi
echo "Stripe Webhook Secret obtained successfully: whsec_... (masked)"

# Now, start the actual 'stripe listen' in the background that will stay running
echo "Starting persistent background Stripe listen process..."
# Using --skip-update to prevent auto-updates.
stripe listen --forward-to "http://localhost:${API_PORT}/v4/stripe-webhook" --events "${STRIPE_EVENTS}" --skip-update &
STRIPE_LISTEN_PID=$!
echo "Persistent Stripe listen command launched. Captured PID: [$STRIPE_LISTEN_PID]"

if [ -z "$STRIPE_LISTEN_PID" ]; then
    echo "Critical Error: Failed to capture PID of persistent Stripe listen process immediately after launch (PID was empty)."
    exit 1 # Should not happen if stripe listen & itself doesn't error out before $! is assigned
fi

echo "Waiting a moment for persistent Stripe listen (PID: $STRIPE_LISTEN_PID) to initialize..."
sleep 3 # Increased sleep slightly

if ! ps -p "$STRIPE_LISTEN_PID" > /dev/null; then
  echo "Error: Persistent background Stripe listen process (PID: $STRIPE_LISTEN_PID) failed to start or died shortly after starting."
  echo "Check for errors in the terminal output above from Stripe CLI (it logs directly when run with '&')."
  # STRIPE_LISTEN_PID is kept so cleanup knows which PID it was attempting to manage
  exit 1 # This will trigger cleanup
fi
echo "Persistent background Stripe listen started (PID: $STRIPE_LISTEN_PID). Forwarding events."
echo "API logs will follow. Stripe listen logs will be mixed with API logs."
echo "---"

# Run the API command with the webhook secret
echo "Executing API command with injected -e STRIPE_WEBHOOK_SECRET=whsec_... (masked)"

# API_RUN_COMMAND is ("docker" "run" "-p" "8000:8000" ...)
# We want ("docker" "run" "-e" "STRIPE_WEBHOOK_SECRET=value" "-p" "8000:8000" ...)
CMD_ARRAY=()
CMD_ARRAY+=("${API_RUN_COMMAND[0]}") # docker
CMD_ARRAY+=("${API_RUN_COMMAND[1]}") # run
CMD_ARRAY+=("-e")
CMD_ARRAY+=("STRIPE_WEBHOOK_SECRET=${WEBHOOK_SECRET}")
# Add the rest of the original command, skipping the first two elements ("docker" "run")
# This assumes that API_RUN_COMMAND always starts with "docker run"
# Ensure elements from index 2 onwards are correctly appended.
if [ ${#API_RUN_COMMAND[@]} -gt 2 ]; then
    CMD_ARRAY+=("${API_RUN_COMMAND[@]:2}")
fi

"${CMD_ARRAY[@]}"

API_EXIT_CODE=$?
echo "API command exited with code $API_EXIT_CODE."
exit $API_EXIT_CODE 