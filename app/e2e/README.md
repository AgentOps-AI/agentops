# End-to-End Testing

> **Note:** While this project may not have specific linting/formatting configurations, the repository uses shared development tools. Please see the [root README.md](../README.md#development-setup) for setup instructions if needed.

Running e2e scripts should validate that all components of the AgentOps platform work together properly.

## SDK-API

These are tests that:

1. Create an Agent
2. Attach the AO SDK
3. Run functions that should produce known outputs
4. Verifies that the expected data is in the DB
5. Deletes the data from the DB

## Prerequisites

1. You have Supabase running locally
2. You have the API running locally at port 8000

## CI/CD

Before tests can be run remotely, we need to configure the Dockerfile to start the API in a separate process before running the test file.
