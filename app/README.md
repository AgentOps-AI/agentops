# 5‑Minute Quickstart (Docker) — Recommended

Get the stack (API + Dashboard) up quickly using Docker Compose.

Prerequisites
- Docker
- Docker Compose

1) Copy env files
- From app/:
  - cp .env.example .env           # if present
  - cp api/.env.example api/.env   # if present
  - cp dashboard/.env.example dashboard/.env.local

2) Fill minimal env values
- API (api/.env)
  SUPABASE_URL=https://YOUR-PROJECT.supabase.co
  SUPABASE_KEY=YOUR_SUPABASE_SERVICE_ROLE_KEY
  JWT_SECRET_KEY=YOUR_RANDOM_JWT_SECRET
  CLICKHOUSE_HOST=your-host.clickhouse.cloud
  CLICKHOUSE_PORT=8443
  CLICKHOUSE_USER=default
  CLICKHOUSE_PASSWORD=your_clickhouse_password
  CLICKHOUSE_DATABASE=otel_2
  # Optional for billing/webhooks:
  # STRIPE_SECRET_KEY=...
  # STRIPE_SUBSCRIPTION_PRICE_ID=...
  # STRIPE_TOKEN_PRICE_ID=...
  # STRIPE_SPAN_PRICE_ID=...

- Dashboard (dashboard/.env.local)
  NEXT_PUBLIC_SUPABASE_URL=https://YOUR-PROJECT.supabase.co
  NEXT_PUBLIC_SUPABASE_ANON_KEY=YOUR_SUPABASE_ANON_KEY
  SUPABASE_SERVICE_ROLE_KEY=YOUR_SUPABASE_SERVICE_ROLE_KEY
  NEXT_PUBLIC_API_URL=http://localhost:8000
  NEXT_PUBLIC_APP_URL=http://localhost:3000

3) Start the stack
- cd app
- docker compose up -d

4) Verify
- API docs: http://localhost:8000/redoc
- Dashboard: http://localhost:3000

Notes
- ClickHouse typically requires TLS on port 8443.
- Auth flows require a Supabase service role key; without it, some pages may be limited.
- API docs: ensure API_DOMAIN includes "localhost" (e.g., API_DOMAIN=localhost:8000). Compose does not pass this by default; either add it to services.api.environment in compose.yaml or use the Manual Docker path below where we pass it via --env-file.

Troubleshooting
- If docker compose build fails with an error like:
  failed to calculate checksum of ... "/deploy/jockey": not found
  This happens because the API Dockerfile expects the app directory as the build context (so it can COPY deploy/jockey), while compose uses app/api. Use the Manual Docker path below (build with context app) or update compose.yaml to set build.context: ./ (repo app dir).

# 5‑Minute Quickstart (Local)
Manual Docker (workaround if Compose build fails)
- Build API from repo root so the Dockerfile can access deploy/jockey:
  cd <repo-root>
  docker build -f app/api/Dockerfile -t agentops-api app
- Build Dashboard:
  cd app/dashboard
  docker build -t agentops-dashboard .
- Create an env file for runtime (example placeholders):
  # app/.env (used for both containers via --env-file)
  # Frontend
  NEXT_PUBLIC_SUPABASE_URL=https://YOUR-PROJECT.supabase.co
  NEXT_PUBLIC_SUPABASE_ANON_KEY=YOUR_SUPABASE_ANON_KEY
  NEXT_PUBLIC_API_URL=http://localhost:8000
  NEXT_PUBLIC_APP_URL=http://localhost:3000
  NEXT_PUBLIC_PLAYGROUND=true
  # Backend
  SUPABASE_SERVICE_ROLE_KEY=YOUR_SUPABASE_SERVICE_ROLE_KEY
  JWT_SECRET_KEY=YOUR_RANDOM_JWT_SECRET
  API_DOMAIN=localhost:8000
  PROTOCOL=http
  CLICKHOUSE_HOST=your-host.clickhouse.cloud
  CLICKHOUSE_PORT=8443
  CLICKHOUSE_USER=default
  CLICKHOUSE_PASSWORD=your_clickhouse_password
  CLICKHOUSE_DATABASE=otel_2
- Run API:
  docker run --rm -p 8000:8000 --env-file app/.env agentops-api
- In another terminal, run Dashboard:
  docker run --rm -p 3000:3000 --env-file app/.env agentops-dashboard
- Verify:
  API docs: http://localhost:8000/redoc
  Dashboard: http://localhost:3000


The fastest way to run the full stack (API + Dashboard) locally without Docker.

Prerequisites
- Python 3.12+
- Node.js 18+
- Bun
- uv
- just

1) Clone and enter the app folder
- cd app

2) Create env files from examples
- If present:
  - cp app/.env.example app/.env
- API:
  - cp app/api/.env.example app/api/.env
- Dashboard:
  - cp app/dashboard/.env.example app/dashboard/.env.local

3) Fill minimal env variables
- API: edit app/api/.env
  SUPABASE_URL=https://YOUR-PROJECT.supabase.co
  SUPABASE_KEY=YOUR_SUPABASE_SERVICE_ROLE_KEY
  JWT_SECRET_KEY=YOUR_RANDOM_JWT_SECRET
  CLICKHOUSE_HOST=your-host.clickhouse.cloud
  CLICKHOUSE_PORT=8443
  CLICKHOUSE_USER=default
  CLICKHOUSE_PASSWORD=your_clickhouse_password
  CLICKHOUSE_DATABASE=otel_2
  # Optional later: STRIPE_SECRET_KEY=..., STRIPE_*_PRICE_ID=...

- Dashboard: edit app/dashboard/.env.local
  NEXT_PUBLIC_SUPABASE_URL=https://YOUR-PROJECT.supabase.co
  NEXT_PUBLIC_SUPABASE_ANON_KEY=YOUR_SUPABASE_ANON_KEY
  SUPABASE_SERVICE_ROLE_KEY=YOUR_SUPABASE_SERVICE_ROLE_KEY
  NEXT_PUBLIC_API_URL=http://localhost:8000
  NEXT_PUBLIC_APP_URL=http://localhost:3000
  # Optional:
  NEXT_PUBLIC_ENVIRONMENT_TYPE=development
  NEXT_PUBLIC_PLAYGROUND=true

Notes
- Supabase service role key is required for authenticated API flows; you can still start the servers without it, but some pages will be limited. Get it in Supabase → Settings → API.
- ClickHouse is used for spans/sessions; use your cloud host on port 8443 (TLS). If you don’t have ClickHouse yet, you can still boot the servers; data views may be empty.

4) Install dependencies
- From the app folder:
  just install

- If "just" is not installed, run the manual equivalents:
  bun install
  uv pip install -r requirements-dev.txt
  cd api && uv pip install -e . && cd ..
  cd dashboard && bun install && cd ..

5) Start servers (two terminals)
- Terminal A (API):
  cd app
  just api-native
  # If "just" is not installed: cd api && uv run python run.py
- Terminal B (Dashboard):
  cd app
  just fe-run
  # If "just" is not installed: cd dashboard && bun run dev

6) Verify
- API docs: http://localhost:8000/redoc loads
- Dashboard: http://localhost:3000 loads

Common pitfalls
- API env file name: The API’s dev command uses .env.dev. Beginners should prefer just api-native (uses your .env). If you want hot reload from app/api, copy .env to .env.dev and run: just dev
- Missing Supabase keys: You can boot, but auth/data views may be limited until you add real keys.
- ClickHouse SSL/auth errors: Re‑check host/password; most cloud setups require 8443 over TLS.

Optional: Docker Compose
- If you prefer Docker later:
  cd app
  docker compose up -d
- Ensure your env files are set; see app/compose.yaml for mappings.


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
1. Use your Supabase PostgreSQL connection details
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
