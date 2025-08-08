# Production Secret Rotation

In the event that production secrets need to be rotated, these are the concepts and services you need to be aware of. 

## JWT Secret

This key is shared between all environments to provide a common value for validating the Bearer token.

## Supabase

Public user authentication, Postgres data storage and S3 object storage are all connected to using various protocols. 

## Clickhouse

All trace/span data is stored in Clickhouse which uses user/password authentication.

# Services

The production stack spans across multiple services which all reference independent sets of environment variables. 

## API

`api.agentops.ai`

Handles authentication (transforming an API key into a Bearer) for the SDK and the Dashboard. Also provides read access to traces and metrics. Must be able to create and verify Bearer tokens, read & write to Supabase (via both the Supabase API and by direct connection to the Postgres server), read & write to Clickhouse and read & write to S3 object storage. 

### Secrets

Deployed and configured on Railway.

`JWT_SECRET_KEY`

`SUPABASE_KEY`

`SUPABASE_PASSWORD`

`CLICKHOUSE_PASSWORD`

`SUPABASE_S3_ACCESS_KEY_ID`

`SUPABASE_S3_SECRET_ACCESS_KEY`

## Collector

`otlp.agentops.ai:4318`

(`grpc.agentops.ai:4137` is also configured but may not be referenced)

Ingests traces from the SDK and writes them to Clickhouse. Must be able to verify Bearer tokens and access the production database. 

### Secrets

Deployed and configured on Railway.

`CLICKHOUSE_PASSWORD`

`JWT_SECRET`

## Dashboard

`app.agentops.ai`

Serves the frontend. Must be able to read & write to Supabase. 

### Secrets

Deployed and configured on Vercel.

```
NEXT_PUBLIC_SUPABASE_ANON_KEY
SUPABASE_SERVICE_ROLE_KEY
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY
NEXT_STRIPE_SECRET_KEY
NEXT_STRIPE_WEBHOOK_SECRET
```

## E2E
Stored in the GitHub repo secrets.
These should all be e2e specific

```
SUPABASE_DB_PASSWORD
SUPABASE_ACCESS_TOKEN
CYPRESS_PASSWORD
```