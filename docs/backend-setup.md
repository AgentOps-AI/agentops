# Backend Services Setup Guide

This guide covers how to set up and run all the backend services and infrastructure components in the `app/` directory.

## 🏗️ Architecture Overview

The AgentOps backend consists of several interconnected services:

- **API Server** (`api/`) - FastAPI backend with authentication, billing, and data processing
- **Dashboard** (`dashboard/`) - Next.js frontend for visualization and management  
- **ClickHouse** - Analytics database for traces and metrics
- **Supabase** - Authentication and primary database
- **OpenTelemetry Collector** - Observability and tracing collection
- **Grafana** (optional) - Monitoring and visualization

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

- **Node.js** 18+ ([Download](https://nodejs.org/))
- **Python** 3.12+ ([Download](https://www.python.org/downloads/))
- **Docker & Docker Compose** ([Download](https://www.docker.com/get-started))
- **Bun** (recommended) or npm ([Install Bun](https://bun.sh/))
- **uv** (recommended for Python) ([Install uv](https://github.com/astral-sh/uv))
- **Just** (optional but recommended) ([Install Just](https://github.com/casey/just))

## 🚀 Quick Start

### 1. Environment Setup

The backend requires several environment files to be configured:

```bash
# Copy environment example files (if they exist)
cp .env.example .env                           # Root environment for Docker Compose
cp api/.env.example api/.env                   # API server configuration  
cp dashboard/.env.example dashboard/.env.local # Dashboard configuration
```

**Note**: Some environment example files may not exist yet. You'll need to create them based on the configuration templates below.

### 2. Install Dependencies

```bash
# Use the convenience command (if Just is installed)
just install

# Or install manually:
bun install                                    # Root dependencies (linting, formatting)
uv pip install -r requirements-dev.txt        # Python dev dependencies
cd api && uv pip install -e . && cd ..       # API dependencies
cd dashboard && bun install && cd ..         # Dashboard dependencies
```

### 3. Start All Services

```bash
# Option 1: Use Docker Compose (recommended for full stack)
docker-compose up -d

# Option 2: Use Just commands (recommended for development)
just api-run    # Start API server
just fe-run     # Start frontend (in another terminal)

# Option 3: Manual startup
cd api && uv run python run.py               # Start API natively
cd dashboard && bun dev                       # Start dashboard (in another terminal)
```

## 🔧 Service Configuration

### API Server Configuration

Create `api/.env` with the following variables:

```bash
# Supabase Configuration
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-supabase-service-role-key

# Application URLs
APP_URL=http://localhost:3000

# Database Configuration
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=9000
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=password
CLICKHOUSE_DATABASE=otel_2
CLICKHOUSE_SECURE=false
CLICKHOUSE_ENDPOINT=http://localhost:8123
CLICKHOUSE_USERNAME=default

# Security
JWT_SECRET_KEY=your-jwt-secret-key

# Monitoring (Optional)
SENTRY_DSN=your-sentry-dsn
SENTRY_ENVIRONMENT=development
LOGGING_LEVEL=INFO

# Stripe (Optional - for billing)
STRIPE_SECRET_KEY=sk_test_your_stripe_secret_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret
STRIPE_SUBSCRIPTION_PRICE_ID=price_your_subscription_price_id
```

### Dashboard Configuration

Create `dashboard/.env.local` with the following variables:

```bash
# Supabase Configuration
NEXT_PUBLIC_SUPABASE_URL=https://your-project-id.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
SUPABASE_PROJECT_ID=your-project-id

# Application URLs
NEXT_PUBLIC_APP_URL=http://localhost:3000
NEXT_PUBLIC_SITE_URL=http://localhost:3000

# Analytics and Monitoring (Optional)
NEXT_PUBLIC_POSTHOG_KEY=your-posthog-key
NEXT_PUBLIC_POSTHOG_HOST=https://us.i.posthog.com
NEXT_PUBLIC_SENTRY_DSN=your-sentry-dsn
NEXT_PUBLIC_SENTRY_ORG=your-sentry-org
NEXT_PUBLIC_SENTRY_PROJECT=your-sentry-project
NEXT_PUBLIC_SENTRY_ENVIRONMENT=development

# Application Configuration
NEXT_PUBLIC_SIGNIN_METHODS=email,github,google
NEXT_PUBLIC_ENVIRONMENT_TYPE=development
NEXT_PUBLIC_FALLBACK_API_KEY=your-fallback-api-key
NEXT_PUBLIC_PLAYGROUND=true

# Stripe Configuration (Optional)
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_your_stripe_publishable_key
STRIPE_SECRET_KEY=sk_test_your_stripe_secret_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret
```

### Docker Compose Configuration

Create `.env` in the app root with the following variables:

```bash
# Supabase Configuration
NEXT_PUBLIC_SUPABASE_URL=https://your-project-id.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
SUPABASE_PROJECT_ID=your-project-id

# Application URLs
APP_URL=http://localhost:3000
NEXT_PUBLIC_SITE_URL=http://localhost:3000

# ClickHouse Configuration
CLICKHOUSE_HOST=clickhouse
CLICKHOUSE_PORT=9000
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=password
CLICKHOUSE_DATABASE=otel_2
CLICKHOUSE_SECURE=false
CLICKHOUSE_ENDPOINT=http://clickhouse:8123
CLICKHOUSE_USERNAME=default

# Security
JWT_SECRET_KEY=your-jwt-secret-key
LOGGING_LEVEL=INFO

# Monitoring (Optional)
SENTRY_DSN=your-sentry-dsn
SENTRY_ENVIRONMENT=development
NEXT_PUBLIC_POSTHOG_KEY=your-posthog-key
NEXT_PUBLIC_POSTHOG_HOST=https://us.i.posthog.com

# Stripe (Optional)
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_your_stripe_publishable_key
NEXT_STRIPE_SECRET_KEY=sk_test_your_stripe_secret_key
NEXT_STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret

# Feature Flags
NEXT_PUBLIC_SIGNIN_METHODS=email,github,google
NEXT_PUBLIC_ENVIRONMENT_TYPE=development
NEXT_PUBLIC_PLAYGROUND=true
```

## 🗄️ Database Setup

### Supabase Setup

1. Create a new project at [supabase.com](https://supabase.com)
2. Go to Settings → API to get your keys and URL
3. Run the database migrations:
   ```bash
   cd app/supabase
   # Follow the setup instructions in supabase/readme.md
   ```

### ClickHouse Setup

ClickHouse is used for analytics and trace storage. You can either:

**Option 1: Use Docker (Recommended for development)**
```bash
# ClickHouse will start automatically with docker-compose up
docker-compose up clickhouse -d
```

**Option 2: ClickHouse Cloud**
1. Sign up for [ClickHouse Cloud](https://clickhouse.com/cloud)
2. Create a database and get connection details
3. Update your environment variables with the cloud connection details

## 📊 Observability Setup

### OpenTelemetry Collector

The OpenTelemetry collector handles trace and metrics collection:

```bash
# Start the collector (included in docker-compose)
docker-compose up otelcollector -d

# Or run standalone
cd app/opentelemetry-collector
docker-compose up -d
```

The collector exposes these ports:
- `4317` - OTLP gRPC receiver
- `4318` - OTLP HTTP receiver
- `1888` - pprof extension
- `13133` - health check extension
- `55679` - zpages extension

### Grafana (Optional)

For monitoring and visualization:

```bash
# Uncomment the Grafana section in opentelemetry-collector/compose.yaml
# Then run:
cd app/opentelemetry-collector
docker-compose up grafana -d
```

Access Grafana at `http://localhost:3001`

## 🛠️ Development Commands

### Using Just (Recommended)

```bash
# Setup everything
just setup

# API Development
just api-native          # Run API natively (fastest for development)
just api-build           # Build API Docker image
just api-run             # Run API in Docker container
just api-test            # Run API tests

# Frontend Development  
just fe-run              # Run dashboard development server
just fe-build            # Build dashboard for production
just fe-test             # Run frontend tests

# Docker Management
just up                  # Start all services with Docker Compose
just down                # Stop all Docker services
just logs                # View Docker logs
just clean               # Clean up Docker resources

# Code Quality
just lint                # Run all linting checks
just format              # Format all code
just test                # Run all tests

# View all available commands
just
```

### Manual Commands

```bash
# API Server
cd api && uv run python run.py

# Dashboard
cd dashboard && bun dev

# Docker Compose
docker-compose up -d                    # Start all services
docker-compose down                     # Stop all services
docker-compose logs -f                  # View logs
docker-compose up api -d                # Start only API service
docker-compose up dashboard -d          # Start only dashboard service
```

## 🔍 Service URLs

Once running, you can access:

- **Dashboard**: http://localhost:3000
- **API Documentation**: http://localhost:8000/redoc
- **API Interactive Docs**: http://localhost:8000/docs
- **ClickHouse**: http://localhost:8123
- **OpenTelemetry Health Check**: http://localhost:13133
- **Grafana** (if enabled): http://localhost:3001

## 🧪 Testing

```bash
# Run all tests
just test

# Run API tests only
cd api && pytest

# Run frontend tests only
cd dashboard && bun test

# Run linting
just lint
# or
bun run lint

# Run formatting
just format
# or
bun run format
```

## 🚀 Production Deployment

### Environment Variables for Production

Update your environment files with production values:

```bash
# Security
DEBUG=false
LOGGING_LEVEL=WARNING
JWT_SECRET_KEY=strong-production-secret

# URLs
PROTOCOL=https
API_DOMAIN=api.yourdomain.com
APP_DOMAIN=yourdomain.com
NEXT_PUBLIC_APP_URL=https://yourdomain.com

# Frontend
NEXT_PUBLIC_ENVIRONMENT_TYPE=production
NEXT_PUBLIC_PLAYGROUND=false
```

### Docker Deployment

```bash
# Build production images
docker-compose -f compose.yaml build

# Start production services
docker-compose -f compose.yaml up -d
```

## 🔧 Troubleshooting

### Common Issues

**1. Port Conflicts**
```bash
# Check what's running on ports
lsof -i :3000  # Dashboard
lsof -i :8000  # API
lsof -i :9000  # ClickHouse
lsof -i :8123  # ClickHouse HTTP

# Kill processes if needed
kill -9 <PID>
```

**2. Database Connection Issues**
- Verify Supabase credentials in environment files
- Check ClickHouse is running: `docker-compose ps`
- Test ClickHouse connection: `curl http://localhost:8123/ping`

**3. Docker Issues**
```bash
# Clean up Docker resources
just clean
# or
docker-compose down -v
docker system prune -f

# Rebuild images
docker-compose build --no-cache
```

**4. Environment Variable Issues**
- Ensure all required environment files exist
- Check for typos in variable names
- Verify URLs don't have trailing slashes
- Make sure secrets are properly escaped

### Logs and Debugging

```bash
# View service logs
docker-compose logs api
docker-compose logs dashboard
docker-compose logs clickhouse
docker-compose logs otelcollector

# Follow logs in real-time
docker-compose logs -f

# API server logs (when running natively)
cd api && uv run python run.py

# Enable debug logging
export LOGGING_LEVEL=DEBUG
```

## 🔐 Security Considerations

### Development
- Use strong JWT secrets
- Keep environment files out of version control
- Use HTTPS in production
- Regularly rotate API keys and secrets

### Production
- Use environment-specific secrets
- Enable rate limiting
- Configure proper CORS policies
- Use secure database connections
- Enable audit logging

## 📚 Additional Resources

- [API Documentation](api/README.md) - Detailed API setup and endpoints
- [Dashboard Documentation](dashboard/README.md) - Frontend development guide
- [Contributing Guide](CONTRIBUTING.md) - Development workflow and standards
- [Docker Compose Reference](https://docs.docker.com/compose/)
- [Supabase Documentation](https://supabase.com/docs)
- [ClickHouse Documentation](https://clickhouse.com/docs)