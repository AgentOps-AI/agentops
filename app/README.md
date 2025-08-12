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
git clone https://github.com/AgentOps-AI/agentops
cd app
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
- **Issues**: [GitHub Issues](https://github.com/AgentOps-AI/AgentOps.Next/issues)
- **Discussions**: [GitHub Discussions](https://github.com/AgentOps-AI/AgentOps.Next/discussions)
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
