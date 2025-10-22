Restart local stack and verify

- Restart services:
  docker compose -f compose.yaml -f opentelemetry-collector/compose.yaml down --remove-orphans
  docker compose -f compose.yaml -f opentelemetry-collector/compose.yaml up -d

- Check logs:
  docker compose -f compose.yaml -f opentelemetry-collector/compose.yaml logs --since=90s api
  docker compose -f compose.yaml -f opentelemetry-collector/compose.yaml logs --since=90s dashboard
  docker compose -f compose.yaml -f opentelemetry-collector/compose.yaml logs --since=90s otelcollector
  docker compose -f compose.yaml -f opentelemetry-collector/compose.yaml logs --since=90s clickhouse

- Open dashboard:
  http://localhost:3000/signin

- Generate a trace (example):
  AGENTOPS_API_KEY=&lt;key&gt; \
  AGENTOPS_API_ENDPOINT=http://localhost:8000 \
  AGENTOPS_APP_URL=http://localhost:3000 \
  AGENTOPS_EXPORTER_ENDPOINT=http://localhost:4318/v1/traces \
  OPENAI_API_KEY=&lt;openai_key&gt; \
  python examples/openai/openai_example_sync.py

- Verify ClickHouse and dashboard:
  curl -s -u default:password "http://localhost:8123/?query=SELECT%20count()%20FROM%20otel_2.otel_traces%20WHERE%20TraceId%20=%20'&lt;TRACE_ID&gt;'"

  http://localhost:3000/traces?trace_id=&lt;TRACE_ID&gt;


Local ClickHouse (self-hosted)
- Set in .env:
  CLICKHOUSE_HOST=127.0.0.1
  CLICKHOUSE_PORT=8123
  CLICKHOUSE_USER=default
  CLICKHOUSE_PASSWORD=password
  CLICKHOUSE_DATABASE=otel_2
  CLICKHOUSE_SECURE=false
  CLICKHOUSE_ENDPOINT=http://clickhouse:8123
  CLICKHOUSE_USERNAME=default

- Start services (includes otelcollector + local ClickHouse):
  docker compose -f compose.yaml -f opentelemetry-collector/compose.yaml up -d

- Initialize ClickHouse schema:
  curl -u default:password 'http://localhost:8123/?query=CREATE%20DATABASE%20IF%20NOT%20EXISTS%20otel_2'
  curl --data-binary @app/clickhouse/migrations/0000_init.sql -u default:password 'http://localhost:8123/?query='

- Run example with local OTLP exporter:
  AGENTOPS_API_KEY=<your_key> \
  AGENTOPS_API_ENDPOINT=http://localhost:8000 \
  AGENTOPS_APP_URL=http://localhost:3000 \
  AGENTOPS_EXPORTER_ENDPOINT=http://localhost:4318/v1/traces \
  OPENAI_API_KEY=<openai_key> \
  python examples/openai/openai_example_sync.py

- Verify:
  - Dashboard: http://localhost:3000/traces?trace_id=<printed_id>
  - CH rows: curl -s -u default:password "http://localhost:8123/?query=SELECT%20count()%20FROM%20otel_2.otel_traces%20WHERE%20TraceId%20=%20'<TRACE_ID>'"
# AgentOps

[![License: ELv2](https://img.shields.io/badge/License-ELv2-blue.svg)](https://www.elastic.co/licensing/elastic-license)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Node.js 18+](https://img.shields.io/badge/node.js-18+-green.svg)](https://nodejs.org/)

AgentOps is a comprehensive observability platform for AI agents and applications. Monitor, debug, and optimize your AI systems with real-time tracing, metrics, and analytics.

## 🚀 Features

- **Real-time Monitoring**: Track AI agent performance and behavior in real-time
- **Distributed Tracing**: Full visibility into multi-step AI workflows
- **Cost Analytics**: Monitor and optimize AI model costs across providers
- **Error Tracking**: Comprehensive error monitoring and alerting
- **Team Collaboration**: Multi-user dashboard with role-based access
- **Billing Management**: Integrated subscription and usage-based billing

## 🏗️ Architecture

This monorepo contains:

- **API Server** (`api/`) - FastAPI backend with authentication, billing, and data processing
- **Dashboard** (`dashboard/`) - Next.js frontend for visualization and management
- **Landing Page** (`landing/`) - Marketing website
- **ClickHouse** - Analytics database for traces and metrics
- **Supabase** - Authentication and primary database
- **Docker Compose** - Local development environment

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

- **Node.js** 18+ ([Download](https://nodejs.org/))
- **Python** 3.12+ ([Download](https://www.python.org/downloads/))
- **Docker & Docker Compose** ([Download](https://www.docker.com/get-started))
- **Bun** (recommended) or npm ([Install Bun](https://bun.sh/))
- **uv** (recommended for Python) ([Install uv](https://github.com/astral-sh/uv))

## 🐳 Quickstart (Docker Compose) — Recommended

Run the full stack with Docker. This is the easiest, most reliable path for local setup.

1) Prerequisites
- Docker and Docker Compose installed

2) Create env file
Create app/.env with the variables referenced by compose.yaml. Minimal required values:

- Supabase
  - NEXT_PUBLIC_SUPABASE_URL=https://YOUR_PROJECT_ID.supabase.co
  - NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
  - SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
  - SUPABASE_PROJECT_ID=YOUR_PROJECT_ID
- URLs
  - APP_URL=http://localhost:3000
  - NEXT_PUBLIC_SITE_URL=http://localhost:3000
- Auth
  - JWT_SECRET_KEY=replace-with-long-random-secret
- ClickHouse
  - CLICKHOUSE_HOST=your-clickhouse-host
  - CLICKHOUSE_PORT=8443
  - CLICKHOUSE_USER=default
  - CLICKHOUSE_PASSWORD=your-clickhouse-password
  - CLICKHOUSE_DATABASE=otel_2
  - CLICKHOUSE_SECURE=true
- Optional
  - NEXT_PUBLIC_ENVIRONMENT_TYPE=development
  - NEXT_PUBLIC_PLAYGROUND=true
  - NEXT_PUBLIC_POSTHOG_KEY=
  - NEXT_PUBLIC_SENTRY_DSN=
  - NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=
  - NEXT_STRIPE_SECRET_KEY=
  - NEXT_STRIPE_WEBHOOK_SECRET=

Tip: Use app/.env.example as a starting point:
cp app/.env.example app/.env

3) Run with compose
From app/:
- docker compose up -d
- docker compose ps
- View logs: docker compose logs -f api and docker compose logs -f dashboard

4) Verify
- API docs: http://localhost:8000/docs
- Dashboard: http://localhost:3000

5) Troubleshooting (Compose)
- CORS: APP_URL must be http://localhost:3000 so API allows dashboard origin.
- Supabase: API requires service role key; anon is only for dashboard.
- ClickHouse: Use port 8443 with CLICKHOUSE_SECURE=true; ensure your IP is allowlisted in ClickHouse Cloud.
- Stripe: Optional unless testing billing. If testing webhooks, set NEXT_STRIPE_WEBHOOK_SECRET and run stripe listen.
- Ports busy: Stop any native servers using ports 3000/8000 before compose.
- Logs: Check docker compose logs -f api and docker compose logs -f dashboard for errors.

## How to get credentials

Supabase
- Create a project at https://supabase.com
- Project URL (for NEXT_PUBLIC_SUPABASE_URL): Settings → API → Project URL
- Anon key (for NEXT_PUBLIC_SUPABASE_ANON_KEY): Settings → API → anon public
- Service role key (for SUPABASE_SERVICE_ROLE_KEY and SUPABASE_KEY on API): Settings → API → service_role secret
- Project ID (for SUPABASE_PROJECT_ID): It’s the subdomain in your Project URL, or Settings → General → Reference ID
- Database connection for API:
  - SUPABASE_HOST, SUPABASE_PORT, SUPABASE_DATABASE, SUPABASE_USER, SUPABASE_PASSWORD
  - Find in Settings → Database → Connection info (use the pooled/primary host and 5432; user is usually postgres.&lt;project_id&gt;)

ClickHouse Cloud
- Create a service at https://clickhouse.com/cloud
- Host and port:
  - CLICKHOUSE_HOST: your-service-name.region.clickhouse.cloud
  - CLICKHOUSE_PORT: 8443
  - CLICKHOUSE_SECURE: true
- Auth:
  - CLICKHOUSE_USER: default (or a user you create)
  - CLICKHOUSE_PASSWORD: from the service connection string
- Database:
  - CLICKHOUSE_DATABASE: otel_2 (default in this repo; adjust if needed)
- Network access:
  - Add your machine IP to the ClickHouse Cloud IP allowlist

Notes
- API docs are enabled in Docker when PROTOCOL=http, API_DOMAIN=localhost:8000, and APP_DOMAIN=localhost:3000 are passed via compose (already configured).
- Keep APP_URL=http://localhost:3000 to avoid CORS issues between dashboard and API.
## 🧩 Beginner Quickstart (Local Dev)

This section is a step-by-step guide to get the API and Dashboard running locally using your own Supabase and ClickHouse credentials. It focuses on the minimum setup for development.

1) Install prerequisites
- Node.js 18+ and Bun
- Python 3.12+ and uv
- Docker (optional, for compose)
- Redis (optional; only needed for rate-limiting/session cache)

2) Prepare environment files
Create and fill these files with your own values (see minimal env lists below).

- API: app/api/.env
- Dashboard: app/dashboard/.env.local
- Optional (for Docker Compose): app/.env

Minimal env for API (app/api/.env):
- Core URLs
  - PROTOCOL=http
  - API_DOMAIN=localhost:8000
  - APP_DOMAIN=localhost:3000
- Auth
  - JWT_SECRET_KEY=your-long-random-secret
- Supabase connection
  - SUPABASE_URL=https://your-project-id.supabase.co
  - SUPABASE_KEY=your-service-role-key
  - SUPABASE_HOST=your-supabase-pg-host
  - SUPABASE_PORT=5432
  - SUPABASE_DATABASE=postgres
  - SUPABASE_USER=postgres.your-project-id
  - SUPABASE_PASSWORD=your-supabase-db-password
- ClickHouse connection
  - CLICKHOUSE_HOST=your-clickhouse-host
  - CLICKHOUSE_PORT=8443
  - CLICKHOUSE_USER=default
  - CLICKHOUSE_PASSWORD=your-clickhouse-password
  - CLICKHOUSE_DATABASE=otel_2
- Optional
  - SQLALCHEMY_LOG_LEVEL=WARNING
  - REDIS_HOST=localhost
  - REDIS_PORT=6379
  - STRIPE_SECRET_KEY=sk_test_...
  - STRIPE_SUBSCRIPTION_PRICE_ID=price_...
  - STRIPE_TOKEN_PRICE_ID=price_...
  - STRIPE_SPAN_PRICE_ID=price_...

Notes:
- The API expects a Supabase service role key for backend operations. An anon key is not sufficient.
- Ensure APP_DOMAIN/API_DOMAIN/PROTOCOL resolve to http://localhost:3000 and http://localhost:8000 for CORS.

Minimal env for Dashboard (app/dashboard/.env.local):
- Supabase
  - NEXT_PUBLIC_SUPABASE_URL=https://your-project-id.supabase.co
  - NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
  - SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
  - SUPABASE_PROJECT_ID=your-project-id
- URLs
  - NEXT_PUBLIC_API_URL=http://localhost:8000
  - NEXT_PUBLIC_APP_URL=http://localhost:3000
  - NEXT_PUBLIC_SITE_URL=http://localhost:3000
- Optional
  - NEXT_PUBLIC_ENVIRONMENT_TYPE=development
  - NEXT_PUBLIC_PLAYGROUND=true
  - NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...
  - NEXT_PUBLIC_POSTHOG_KEY=
  - NEXT_PUBLIC_SENTRY_DSN=

3) Install dependencies
From the repository root (app/):
- bun install
- uv pip install -r requirements-dev.txt

API:
- cd api && uv pip install -e . && cd ..

Dashboard:
- cd dashboard && bun install && cd ..

4) Run locally (native)
Terminal A (API):
- cd app/api
- uv run python run.py
- Verify API docs at http://localhost:8000/redoc

Terminal B (Dashboard):
- cd app/dashboard
- bun run dev
- Open http://localhost:3000

5) Alternative: Docker Compose
If you prefer containers or need a consistent env:
- Create app/.env using the variables referenced in compose.yaml (NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_PROJECT_ID, APP_URL, JWT_SECRET_KEY, CLICKHOUSE_* vars, etc.)
- From app/: docker compose up -d
- Verify: http://localhost:3000 and http://localhost:8000/redoc

6) Verification checklist
- API: http://localhost:8000/redoc loads without 5xx errors
- Dashboard: http://localhost:3000 loads and can reach the API (open browser console; no CORS/network errors)
- If billing flows are needed, configure Stripe and run stripe listen --forward-to http://localhost:8000/v4/stripe-webhook and set STRIPE_WEBHOOK_SECRET in app/api/.env

7) Troubleshooting
- CORS errors: Ensure APP_URL in API resolves to http://localhost:3000. This is derived from PROTOCOL and APP_DOMAIN in app/api/.env.
- 401/403 on API endpoints: The API validates Supabase JWTs. Log in via the dashboard (Supabase project must be configured) so requests include Authorization: Bearer <token>.
- Supabase errors: API requires a service role key (SUPABASE_KEY) and correct Postgres parameters (host/user/password). Check your Supabase project settings.
- ClickHouse connection refused/timeout: Use port 8443, set correct user/password/database, ensure your IP is allowlisted in ClickHouse Cloud.
- Stripe errors: Only required for billing features. For local, use test keys and stripe listen to populate STRIPE_WEBHOOK_SECRET.
- Redis not found: Optional for development. Install and start Redis if enabling rate limiting or session cache, or leave REDIS_* unset to skip those features.
- Ports busy: Ensure nothing else is running on 3000 or 8000, or adjust the mapped ports and corresponding env URLs.


## 🛠️ Quick Start


### 1. Clone the Repository

```bash
git clone https://github.com/AgentOps-AI/agentops.git
```

### 2. Set Up Environment Variables

Copy the environment example files and fill in your values:

```bash
# Root environment (for Docker Compose)
cp .env.example .env

# API environment
cp api/.env.example api/.env

# Dashboard environment  
cp dashboard/.env.example dashboard/.env.local
```

**Important**: You'll need to set up external services first. See [External Services Setup](#external-services-setup) below.

### 3. Install Dependencies

```bash
# Install root dependencies (linting, formatting tools)
bun install

# Install Python dev dependencies
uv pip install -r requirements-dev.txt

# Install API dependencies
cd api && uv pip install -e . && cd ..

# Install Dashboard dependencies
cd dashboard && bun install && cd ..
```

### 4. Start Development Environment

```bash
# Start all services with Docker Compose
docker-compose up -d

# Or use the convenience script
just api-run    # Start API server
just fe-run     # Start frontend in another terminal
```

Visit:
- Dashboard: http://localhost:3000
- API Docs: http://localhost:8000/redoc

## 🔧 External Services Setup

AgentOps requires several external services. Here's how to set them up:

### Supabase (Required)

**Option A: Local Development (Recommended)**

1. Install Supabase CLI: `brew install supabase/tap/supabase` (or see [docs](https://supabase.com/docs/guides/cli))
2. Initialize and start Supabase locally:
   ```bash
   cd app  # Make sure you're in the app directory
   supabase init
   supabase start
   ```
3. The local Supabase will provide connection details. Update your `.env` files with:
   ```
   SUPABASE_URL=http://127.0.0.1:54321
   SUPABASE_KEY=<anon-key-from-supabase-start-output>
   ```
4. Run migrations: `supabase db push`

For Linux environments with CLI install issues, see docs/local_supabase_linux.md for a manual binary install and env mapping steps.
**Option B: Cloud Supabase**

1. Create a new project at [supabase.com](https://supabase.com)
2. Go to Settings → API to get your keys
3. Update your `.env` files with:
   ```
   SUPABASE_URL=https://your-project-id.supabase.co
   SUPABASE_KEY=your-anon-key
   ```

### ClickHouse (Required)

1. Sign up for [ClickHouse Cloud](https://clickhouse.com/cloud) or self-host
2. Create a database and get connection details
3. Update your `.env` files with:
   ```
   CLICKHOUSE_HOST=your-host.clickhouse.cloud
   CLICKHOUSE_USER=default
   CLICKHOUSE_PASSWORD=your-password
   CLICKHOUSE_DATABASE=your-database
   ```

### PostgreSQL (Required)

Configure direct PostgreSQL connection:

**For Local Supabase:**
```
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=54322  # Note: Different port than Supabase API
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DATABASE=postgres

# Also add these for SQLAlchemy connections:
SUPABASE_HOST=127.0.0.1
SUPABASE_PORT=54322
SUPABASE_USER=postgres
SUPABASE_PASSWORD=postgres
SUPABASE_DATABASE=postgres
```

**For Cloud Supabase:**
1. Use your Supabase PostgreSQL connection details from Settings → Database
2. Update your `.env` files with:
   ```
   POSTGRES_HOST=your-supabase-host
   POSTGRES_PORT=5432
   POSTGRES_USER=postgres.your-project-id
   POSTGRES_PASSWORD=your-password
   POSTGRES_DATABASE=postgres
   ```

### Stripe (Optional - for billing)

1. Create a [Stripe](https://stripe.com) account
2. Get your API keys from the dashboard
3. Update your `.env` files with:
   ```
   STRIPE_SECRET_KEY=sk_test_...
   STRIPE_PUBLISHABLE_KEY=pk_test_...
   ```

### Additional Services (Optional)

- **Sentry**: Error monitoring - [sentry.io](https://sentry.io)
- **PostHog**: Analytics - [posthog.com](https://posthog.com)
- **GitHub OAuth**: Social login - [GitHub Apps](https://github.com/settings/applications/new)

## 🏃‍♂️ Development Workflow

### Using Just Commands (Recommended)

```bash
# API Development
just api-native          # Run API natively (faster for development)
just api-docker-build    # Build API Docker image
just api-docker-run      # Run API in Docker

# Frontend Development  
just fe-run              # Run dashboard development server

# View all available commands
just
```

### Manual Development

```bash
# Start API server
cd api && uv run python run.py

# Start dashboard (in another terminal)
cd dashboard && bun dev

# Start landing page (in another terminal)  
cd landing && bun dev
```

## 🧪 Testing

```bash
# Run API tests
cd api && pytest

# Run frontend tests
cd dashboard && bun test

# Run linting
bun run lint

# Run formatting
bun run format
```

## 🔍 Troubleshooting

### Authentication Issues

**Problem: Login succeeds but immediately redirects back to login page**

This is usually caused by cookie configuration issues between the frontend and backend.

**Solutions:**

1. **Check your environment URLs**: Ensure `NEXT_PUBLIC_API_URL` in dashboard points to your API server:
   ```bash
   # dashboard/.env.local
   NEXT_PUBLIC_API_URL=http://localhost:8000  # For local development
   ```

2. **Verify JWT secret**: Make sure `JWT_SECRET_KEY` is set in your API `.env`:
   ```bash
   # api/.env
   JWT_SECRET_KEY=your-secret-key-at-least-32-chars
   ```

3. **For local development with different ports**: The API automatically adjusts cookie settings for localhost. No manual configuration needed.

4. **For production or custom domains**: Ensure your API and dashboard share the same root domain for cookies to work.

### Database Connection Issues

**Problem: SQLAlchemy connection errors**

Ensure all Supabase database variables are set in `api/.env`:
```bash
SUPABASE_HOST=127.0.0.1      # For local Supabase
SUPABASE_PORT=54322          # Note: Different from API port
SUPABASE_USER=postgres
SUPABASE_PASSWORD=postgres
SUPABASE_DATABASE=postgres
```

### Supabase Seed Data Issues

**Problem: Duplicate key or missing table errors during `supabase start`**

The seed.sql file may have issues. You can temporarily comment out problematic inserts or check if migrations are missing.

## 📦 Production Deployment

### Using Docker Compose

```bash
# Build and start production services
docker-compose -f compose.yaml up -d
```

### Environment Variables for Production

Update your `.env` files with production values:

```bash
# Core settings
PROTOCOL="https"
API_DOMAIN="api.yourdomain.com"
APP_DOMAIN="yourdomain.com"

# Security
DEBUG="false"
LOGGING_LEVEL="WARNING"

# Frontend
NEXT_PUBLIC_ENVIRONMENT_TYPE="production"
NEXT_PUBLIC_PLAYGROUND="false"
```

### Deployment Platforms

AgentOps can be deployed on:

- **Docker Compose** (recommended for self-hosting)
- **Kubernetes** (helm charts available)
- **Cloud platforms** (AWS, GCP, Azure)
- **Vercel** (frontend) + **Railway/Fly.io** (backend)

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and add tests
4. Run linting and tests: `bun run lint && bun run test`
5. Commit your changes: `git commit -m 'Add amazing feature'`
6. Push to the branch: `git push origin feature/amazing-feature`
7. Open a Pull Request

### Code Style

This project uses:
- **ESLint + Prettier** for JavaScript/TypeScript
- **Ruff** for Python
- **Pre-commit hooks** for automatic formatting

## 📚 Documentation

- [API Documentation](api/README.md)
- [Dashboard Documentation](dashboard/README.md)
- [Deployment Guide](docs/deployment.md)
- [Contributing Guide](CONTRIBUTING.md)

## 📄 License

This project is licensed under the Elastic License 2.0 - see the [LICENSE](LICENSE) file for details.

**Key License Points:**
- ✅ Free to use, modify, and distribute
- ✅ Commercial use allowed
- ❌ Cannot provide as a hosted/managed service to third parties
- ❌ Cannot circumvent license key functionality
- ❌ Cannot remove licensing notices

For more information, visit [elastic.co/licensing/elastic-license](https://www.elastic.co/licensing/elastic-license).

## 🆘 Support

- **Documentation**: Check our [docs](docs/)
- **Issues**: [GitHub Issues](https://github.com/AgentOps-AI/agentops/issues)
- **Discussions**: [GitHub Discussions](https://github.com/AgentOps-AI/agentops/discussions)
- **Email**: support@agentops.ai

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/), [Next.js](https://nextjs.org/), [Supabase](https://supabase.com/), and [ClickHouse](https://clickhouse.com/)
- Inspired by the open source community
- Special thanks to all our contributors

---

## Development Setup (Detailed)

This monorepo uses centralized configurations for linting and formatting to ensure consistency across projects.

**Prerequisites:**

- Node.js (Version specified in root `package.json` -> engines)
- bun (usually comes with Node.js)
- Python (Version specified in `api/pyproject.toml` -> requires-python, used by Ruff)
- pip or uv (uv recommended for faster Python dependency management)

**Installation:**

1.  **Install Root Node.js Dev Dependencies:**
    ```bash
    # From the repository root
    bun install
    ```

    This installs ESLint, Prettier, TypeScript, Husky, and other shared tools defined in the root `package.json`.

2.  **Install Root Python Dev Dependencies:**

    ```bash
    # From the repository root
    # Using uv (recommended):
    uv pip install -r requirements-dev.txt

    # Or using pip:
    pip install -r requirements-dev.txt
    ```
    This installs Ruff, defined in the root `requirements-dev.txt`. The `uv.lock` file ensures consistent versions across the monorepo.

3.  **Install Project-Specific Dependencies:** Navigate to the specific project directory (e.g., `dashboard/`, `api/`, `landing/`) and follow their respective setup instructions (e.g., `bun install`, `pip install -e .` or `uv pip install -e .`).

**Linting & Formatting:**

- **Configuration:**
  - **JavaScript/TypeScript:** ESLint (`.eslintrc.json`) and Prettier (`prettier.config.js`) configurations are located at the repository root.
  - **Python:** Ruff (`ruff.toml`) configuration is located at the repository root.
  - Specific projects (like `dashboard/`) may have their own `.eslintrc.json` that _extends_ the root configuration for project-specific overrides.
- **Pre-commit Hook:** Husky is set up (`.husky/pre-commit`) to automatically format and lint staged files (JS/TS/Python) using the root configurations before you commit.
- **Manual Checks:** You can run checks manually from the root directory using scripts defined in the root `package.json`:

  ```bash
  # Lint JS/TS files
  bun run lint:js

  # Lint Python files
  bun run lint:py

  # Format JS/TS files
  bun run format:js

  # Format Python files
  bun run format:py

  # Run all linting
  bun run lint

  # Run all formatting
  bun run format
  ```

- **IDE Integration:** For the best experience, configure your IDE (e.g., VS Code) with the appropriate extensions (ESLint, Prettier, Ruff) to get real-time feedback and auto-formatting on save.

### Running Services (Convenience)

A `justfile` is provided at the root for convenience in running the primary services from the project root directory. After completing the setup and installation steps within each service directory (`api/`, `dashboard/`), you can use:

- `just api-native`: Runs the backend API server natively.
- `just api-docker-build`: Builds the backend API Docker image.
- `just api-docker-run`: Runs the backend API server in Docker.
- `just dash`: Runs the frontend dashboard development server.

Refer to the README files in `api/` and `dashboard/` for detailed setup instructions (environment variables, dependencies) before using these commands.

## Procedure

### Feature branch workflow

1. Choose a ticket or feature to build
2. Create a new branch with a descriptive name
3. Complete the feature with this branch
4. Once the feature is finished, create a Pull Request with a brief explanation of the changes
5. With at least one review, merge the feature branch into main

### PR's

- No squash commit (green square maxxing)
- At least one review before merge
- `Main` is protected
- Emergency `Main` merges without reviews need to be justified in the PR
- The PR description should fit the PR template.
- Linear tickets closed should be referenced (i.e. `Closes ENG-123`)

### Commit Formatting

`type(service): description`

_Examples_:

- feat(supabase): added user table
- fix(app): spacing issue on dashboard
- test(app): login component testing
