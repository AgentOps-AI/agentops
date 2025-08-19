#!/bin/bash
# Script to handle 'just api-run' logic, including optional Stripe integration.

set -e # Exit immediately if a command exits with a non-zero status.

STRIPE_FLAG="${1:-}" # First argument is the stripe flag, default to empty
API_PORT="8000"      # Default API port
ENV_FILE="${API_ENV_FILE:-api/.env.dev}" # Use .env.dev by default, allow override with API_ENV_FILE

API_DOCKER_COMMAND=("docker" "run" "-p" "${API_PORT}:${API_PORT}" "--env-file" "$ENV_FILE" "--rm" "--name" "agentops-api-container" "agentops-api")

if [ "$STRIPE_FLAG" = "-s" ] || [ "$STRIPE_FLAG" = "--with-stripe" ]; then
    echo "Attempting to run API on port $API_PORT with Stripe integration (using scripts/run-api-with-stripe.sh)..."

    "$(dirname "$0")/run-api-with-stripe.sh" "$API_PORT" "${API_DOCKER_COMMAND[@]}"
else
    echo "Running API on port $API_PORT without Stripe integration (direct Docker run)..."
    "${API_DOCKER_COMMAND[@]}"
fi

echo "API execution finished (or was launched in background by run-api-with-stripe.sh)." 