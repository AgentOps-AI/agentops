# AgentOps Next API Server

> **Note:** This project uses shared development configurations (linting, formatting) defined in the repository root. Please see the [root README.md](../../README.md#development-setup) for initial setup instructions and tooling details (Ruff).

## Authentication

Requests to protected endpoints (primarily `/opsboard/*` and `/v4/*`) require a valid Supabase JWT passed in the `Authorization: Bearer <token>` header. The API server validates this token using the `Depends(get_current_user)` dependency before processing the request.

## Billing & Subscription Management 💳

The API server integrates with Stripe to handle subscription billing, payment processing, and organization upgrades. This section covers the billing architecture, setup requirements, and available endpoints.

### Billing Architecture

The billing system follows this flow:
1. **Frontend** initiates billing actions (upgrade, cancel, reactivate) via API calls
2. **API Server** creates Stripe checkout sessions and manages subscription state
3. **Stripe Webhooks** notify the API of payment events and subscription changes
4. **Database** stores subscription status and organization premium status

### Stripe Integration Setup

#### Required Environment Variables

```bash
# Stripe API Configuration
STRIPE_SECRET_KEY=sk_test_... # or sk_live_... for production
STRIPE_WEBHOOK_SECRET=whsec_... # Webhook signing secret
STRIPE_SUBSCRIPTION_PRICE_ID=price_... # Your subscription plan price ID
APP_URL=http://localhost:3000 # Frontend URL for redirects
```

#### Webhook Configuration

Configure a Stripe webhook endpoint pointing to your API server:

**Production:**
- Endpoint URL: `https://your-api-domain.com/v4/stripe-webhook`
- Events to send: `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`, `charge.dispute.created`

**Local Development:**
Use the Stripe CLI to forward webhooks to your local server:
```bash
stripe listen --forward-to http://localhost:8000/v4/stripe-webhook
```

### Billing Endpoints

#### Organization Billing (`/opsboard/orgs/{org_id}/`)

- **`POST /create-checkout-session`**: Create a Stripe Checkout Session for upgrading to Pro
  - **Body**: `{ "price_id": "price_...", "discount_code": "optional_code" }`
  - **Returns**: `{ "clientSecret": "cs_..." }` for Stripe Elements
  - **Features**: 
    - Double-payment prevention (checks existing active subscriptions)
    - Discount code validation (promotion codes and coupons)
    - Idempotency keys for retry safety

- **`POST /cancel-subscription`**: Cancel an active subscription
  - **Body**: `{ "subscription_id": "sub_..." }`
  - **Action**: Sets `cancel_at_period_end=true` (subscription remains active until period end)
  - **Features**: Idempotency protection, validation checks

- **`POST /reactivate-subscription`**: Reactivate a cancelled subscription
  - **Action**: Sets `cancel_at_period_end=false` (continues billing)
  - **Features**: Idempotency protection, state validation

- **`POST /validate-discount-code`**: Validate promotion codes before checkout
  - **Body**: `{ "discount_code": "PROMO20" }`
  - **Returns**: Discount details and validity status

#### Webhook Handling (`/v4/stripe-webhook`)

The webhook endpoint processes these Stripe events:

- **`checkout.session.completed`**: Updates organization to Pro status after successful payment
- **`customer.subscription.updated`**: Handles subscription status changes (active, past_due, etc.)
- **`customer.subscription.deleted`**: Downgrades organization to free tier
- **`charge.dispute.created`**: Handles payment disputes and chargebacks

### Billing Data Model

Organizations store billing-related fields:

```python
class OrgModel:
    prem_status: PremStatus  # 'free' or 'pro'
    subscription_id: str     # Stripe subscription ID
    subscription_end_date: int  # Unix timestamp
    subscription_cancel_at_period_end: bool
```

### Error Handling & Monitoring

The billing system includes comprehensive error handling:

- **Structured Logging**: All billing operations log with structured data for monitoring
- **Webhook Replay Protection**: Events are processed idempotently
- **Database Transaction Safety**: Rollback on failures with detailed error logging
- **Stripe API Error Handling**: Graceful handling of Stripe API failures

### Security Features

- **Double-Payment Prevention**: Checks for existing active subscriptions before creating checkout sessions
- **Idempotency Keys**: All Stripe operations use unique idempotency keys to prevent duplicates
- **Webhook Signature Verification**: All webhook events are cryptographically verified
- **Permission Validation**: Only org admins/owners can manage billing

### Testing Billing Features

For local development:
1. Use Stripe test mode keys (`sk_test_...`, `price_test_...`)
2. Use test card numbers (e.g., `4242424242424242`)
3. Forward webhooks using `stripe listen`
4. Monitor webhook events in Stripe Dashboard

## API Endpoints

The API is divided into two main sections: `/opsboard` for user, organization, and project management, and `/v4` for trace and metric data retrieval. All endpoints listed below require JWT authentication.

### OpsBoard (`/opsboard`)

Handles core entity management.

*   **Users (`/opsboard/users`)**
    *   `GET /me`: Get details of the currently authenticated user.
    *   `PUT /me`: Update details of the currently authenticated user.
    *   `PUT /me/survey-complete`: Mark the authenticated user's survey as complete.
*   **Projects (`/opsboard/projects`)**
    *   `GET /`: Get all projects the user has access to (excludes Demo Org).
    *   `GET /{project_id}`: Get details for a specific project.
    *   `POST /`: Create a new project (Requires Admin/Owner role in the org).
    *   `PUT /{project_id}`: Update project name or environment (Requires Admin/Owner role in the org).
    *   `DELETE /{project_id}`: Delete a project (Requires Owner role in the org).
    *   `POST /{project_id}/regenerate-key`: Regenerate the API key for a project (Requires Admin/Owner role in the org).
*   **Organizations (`/opsboard/orgs`)**
    *   `GET /`: Get all organizations the user belongs to (excludes Demo Org).
    *   `GET /invites`: Get pending invitations *for* the authenticated user.
    *   `GET /{org_id}`: Get detailed information for a specific organization, including members.
    *   `POST /`: Create a new organization (user becomes Owner).
    *   `PUT /{org_id}`: Update organization name (Requires Admin/Owner role).
    *   `POST /{org_id}/invite`: Invite a user (by email) to the organization (Requires Admin/Owner role).
    *   `POST /{org_id}/accept-invite`: Accept a pending invitation for the authenticated user.
    *   `POST /{org_id}/remove-member`: Remove a specified user from the organization (Requires Admin/Owner role; cannot remove self or last Owner).
    *   `POST /{org_id}/change-role`: Change the role of a specified member (Requires Admin/Owner role; cannot change self or demote last Owner).
    *   `POST /{org_id}/create-checkout-session`: Create a Stripe Checkout Session for an organization to upgrade their plan.
    *   `POST /{org_id}/cancel-subscription`: Cancel the active Stripe subscription for an organization.

### V4 (`/v4`)

Handles trace and metrics data retrieval, primarily sourced from Clickhouse. These endpoints typically require a `project_id` query parameter.

*   **Traces (`/v4/traces`)**
    *   `GET /?project_id=<id>&...`: Get a list of traces for the specified `project_id`. Supports filtering by time range, span name, pagination (`limit`, `offset`), and sorting (`order_by`, `sort_order`).
    *   `GET /{trace_id}?project_id=<id>`: Get detailed information (including spans) for a specific `trace_id` belonging to the specified `project_id`.
*   **Metrics (`/v4/meterics`)** *(Note: Prefix is intentionally `meterics`)*
    *   `GET /project?project_id=<id>&...`: Get aggregated metrics (span counts, token usage, costs, durations, etc.) for the specified `project_id`. Supports filtering by time range (`start_time`, `end_time`).
*   **Webhooks (`/v4`)**
    *   `POST /stripe-webhook`: Handles incoming Stripe events (e.g., `checkout.session.completed`, subscription updates) to manage subscription statuses. Requires specific Stripe webhook configuration in your Stripe dashboard to point to this endpoint.

## Local Development Setup ⚙️

Install requirements using `uv` (recommended) or `pip`:

This API server powers the AgentOps dashboard frontend. You'll need to run this server locally to develop or test frontend features that interact with the API.

### 1. Environment Variables

First, set up your environment variables. Copy the example file:

```bash
cp .env.example .env
```

Then, **edit `.env`** and fill in the required values. **This step is crucial for both native and Docker setups.**

#### Required Environment Variables

The following variables are **required** for the API to function:

**Supabase Configuration:**
```bash
SUPABASE_URL="https://your-project-id.supabase.co"
SUPABASE_KEY="your-supabase-service-role-key"
JWT_SECRET_KEY="your-jwt-secret-key"
```

**ClickHouse Configuration:**
```bash
CLICKHOUSE_HOST="your-clickhouse-host.com"
CLICKHOUSE_USER="default"
CLICKHOUSE_PASSWORD="your-clickhouse-password"
CLICKHOUSE_DATABASE="otel_2"
```

#### Optional Environment Variables

**Stripe (for billing features):**
```bash
STRIPE_SECRET_KEY="sk_test_your_stripe_secret_key"
STRIPE_WEBHOOK_SECRET="whsec_your_webhook_secret"
STRIPE_SUBSCRIPTION_PRICE_ID="price_your_subscription_price_id"
```

**Monitoring:**
```bash
SENTRY_DSN="your-sentry-dsn"
DEBUG="true"  # Set to false in production
LOGGING_LEVEL="INFO"
```

See the `.env.example` file for the complete list of available configuration options.

Key environment variables include:
*   `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_JWT_SECRET`: For Supabase connection and JWT validation.
*   `DATABASE_URL`: For direct PostgreSQL connection (used by SQLAlchemy).
*   `STRIPE_SECRET_KEY`: Your Stripe secret API key.
    *   **Production**: Use your *live* mode secret key (e.g., `sk_live_...`) from the Stripe Dashboard.
    *   **Local/Development**: Use your *test* mode secret key (e.g., `sk_test_...`) from the Stripe Dashboard.
*   `STRIPE_WEBHOOK_SECRET`: Secret used to verify signatures of incoming webhooks from Stripe.
    *   **Production**: The signing secret for your *production* webhook endpoint, obtained from the Stripe Dashboard when you configure the endpoint.
    *   **Local/Development (using `stripe listen`)**: When using the Stripe CLI command `stripe listen --forward-to <your_local_api_webhook_url>`, the CLI will output a *temporary, local-only* webhook signing secret (e.g., `whsec_...`). You **must** use this specific secret in your local `.env` file for the API server to correctly verify events forwarded by `stripe listen`. This is different from your production webhook secret. If you use just api-build -s and just api run -s it will handle this secret for you, and you MUST delete it from your .env file if you hard coded it in the past.
*   `STRIPE_SUBSCRIPTION_PRICE_ID`: The specific Stripe Price ID for your primary subscription plan.
    *   **Production**: The ID of your *live* mode price (e.g., `price_...`) from the Stripe Dashboard.
    *   **Local/Development**: The ID of your *test* mode price (e.g., `price_...`) from the Stripe Dashboard, used for testing subscriptions.
*   `APP_URL`: The base URL of your frontend application (e.g., `http://localhost:3000`), used for constructing return URLs for Stripe.
*   `SQLALCHEMY_LOG_LEVEL`: (Optional) Set the logging level for SQLAlchemy. Can be "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL". Defaults to "INFO".
*   `DEBUG`: Set to `true` for detailed request logging.
*   `PROFILING_ENABLED`, `PROFILE_OUTPUT_DIR`, `PROFILING_FORMAT`: For request profiling.

### 2. Choose Your Setup Method:

#### Option A: Running Natively (Python) 🐍

Use this method if you want to run the server directly using your local Python environment.

1.  **Install Dependencies:**
    Use `uv` (recommended) or `pip`:

    ```bash
    # Using uv (faster):
    uv pip install -r requirements.txt

    # Or using pip:
    pip install -r requirements.txt
    ```

2.  **Run the Server:**

    ```bash
    python run.py
    ```

    The API should now be running, typically at `http://localhost:8000`.

#### Option B: Running with Docker 🐳

Use this method if you prefer using containers to manage dependencies and the runtime environment.

1.  **Build the Docker Image:**
    Make sure you're in the `api/` directory.

    ```bash
    docker build -t agentops-api .
    ```

2.  **Run the Docker Container:**
    This command maps port 8000, loads environment variables from your `.env` file (make sure you completed Step 1!), automatically removes the container on exit (`--rm`), and names the container.

    ```bash
    docker run -p 8000:8000 --env-file .env --rm --name agentops-api-container agentops-api
    ```

    The API should now be accessible at `http://localhost:8000`! 🎉

## Request Logging

The API logs basic information about all requests by default. To enable detailed request body logging, set the `DEBUG` environment variable to `true`:

```bash
# In your .env file
DEBUG=true
```

This will log the full request body for all POST, PUT, and PATCH requests, which is useful for debugging but may contain sensitive information.

## Profiling

The API includes request profiling functionality using [pyinstrument](https://github.com/joerick/pyinstrument).

### Setup

1. Enable profiling by setting the environment variable in your .env file:

   ```
   PROFILING_ENABLED=true
   ```

2. Optionally, set a custom output directory for profile files:

   ```
   PROFILE_OUTPUT_DIR=/path/to/profiles
   ```

3. Choose between HTML or Speedscope profiles:
   ```
   PROFILING_FORMAT=html # default
   ```
   or
   ```
   PROFILING_FORMAT=speedscope
   ```

Profile files are saved to the current directory or the configured `PROFILE_OUTPUT_DIR` with a timestamp in the filename.

### Viewing Profiles

- Speedscope profiles (.speedscope.json): Upload to [speedscope.app](https://www.speedscope.app/)
- HTML profiles (.html): Open in any browser