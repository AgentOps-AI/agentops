#!/bin/bash
# Script to handle 'just api-build' logic, including optional Stripe/jq checks.

set -e # Exit immediately if a command exits with a non-zero status.

STRIPE_FLAG="${1:-}" # First argument is the stripe flag, default to empty

if [ "$STRIPE_FLAG" = "-s" ] || [ "$STRIPE_FLAG" = "--with-stripe" ]; then
    echo "Performing pre-build checks for Stripe integration tools..."
    echo "Checking for Stripe CLI..."
    if ! command -v stripe > /dev/null; then
        echo "Warning: Stripe CLI not found or not in PATH."
        echo "         'just api-run -s' (or running with Stripe) might fail to set up Stripe webhooks automatically."
        echo "         Please install Stripe CLI from https://stripe.com/docs/stripe-cli and add it to your PATH."
    else
        echo "Stripe CLI found."
    fi
    echo "Checking for jq..."
    if ! command -v jq > /dev/null; then
        echo "Warning: jq (JSON processor) not found or not in PATH."
        echo "         'just api-run -s' (or running with Stripe) might fail to set up Stripe webhooks automatically."
        echo "         Please install jq (e.g., 'pacman -S jq' in MINGW64/Git Bash, or download from https://stedolan.github.io/jq/download/)."
    else
        echo "jq found."
    fi
else
    echo "Skipping Stripe/jq checks for this build (pass '-s' or '--with-stripe' to include them via 'just api-build -s')."
fi

echo "Building Docker image for the backend API..."

docker build -f api/Dockerfile -t agentops-api .
echo "Docker image build complete." 