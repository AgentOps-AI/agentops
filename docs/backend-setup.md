# AgentOps Backend Setup Guide

This guide provides comprehensive instructions for setting up and running the AgentOps backend services, including the API server, databases, and supporting infrastructure.

## 📋 Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Detailed Service Setup](#detailed-service-setup)
- [Development Workflow](#development-workflow)
- [Production Deployment](#production-deployment)
- [Troubleshooting](#troubleshooting)

## Overview

The AgentOps backend consists of several interconnected services that work together to provide observability for AI agents:

- **API Server** - FastAPI backend handling authentication, data processing, and business logic
- **ClickHouse** - Time-series database for storing traces and analytics data
- **Supabase/PostgreSQL** - Primary database for user data, organizations, and metadata
- **OpenTelemetry Collector** - Ingests and processes telemetry data
- **Docker Compose** - Orchestrates all services for local development

## Prerequisites

Before setting up the backend, ensure you have:

### Required Software

- **Python 3.12+** - [Download](https://www.python.org/downloads/)
- **Docker & Docker Compose** - [Download](https://www.docker.com/get-started)
- **uv** (recommended) or pip - [Install uv](https://github.com/astral-sh/uv)
- **Just** (optional but recommended) - [Install Just](https://github.com/casey/just)

### External Services

You'll need accounts and credentials for:

1. **Supabase** - Authentication and primary database
2. **ClickHouse Cloud** (or self-hosted) - Analytics database
3. **Stripe** (optional) - Payment processing
4. **Sentry** (optional) - Error monitoring

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Dashboard     │────▶│   API Server     │────▶│   ClickHouse    │
│  (Next.js)      │     │   (FastAPI)      │     │   (Analytics)   │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │                           │
                               ▼                           │
                        ┌──────────────────┐              │
                        │    Supabase      │              │
                        │  (PostgreSQL)    │              │
                        └──────────────────┘              │
                               ▲                           │
                               │                           ▼
                        ┌──────────────────┐     ┌─────────────────┐
                        │  Auth Service    │     │  OTel Collector │
                        └──────────────────┘     └─────────────────┘
```

## Quick Start

### 1. Clone and Navigate to App Directory

```bash
git clone https://github.com/AgentOps-AI/AgentOps.git
cd agentops/app
```

### 2. Set Up Environment Variables

```bash
# Copy environment templates
cp .env.example .env
cp api/.env.example api/.env
cp dashboard/.env.example dashboard/.env.local
```

### 3. Configure External Services

Edit the `.env` files with your credentials:

#### Supabase Configuration
```env
# In .env and api/.env
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# PostgreSQL Direct Connection
POSTGRES_HOST=db.your-project.supabase.co
POSTGRES_PORT=5432
POSTGRES_USER=postgres.your-project
POSTGRES_PASSWORD=your-password
POSTGRES_DATABASE=postgres
```

#### ClickHouse Configuration
```env
# In .env and api/.env
CLICKHOUSE_HOST=your-host.clickhouse.cloud
CLICKHOUSE_PORT=8443
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=your-password
CLICKHOUSE_DATABASE=agentops
CLICKHOUSE_SECURE=true
CLICKHOUSE_ENDPOINT=https://your-host.clickhouse.cloud:8443
```

### 4. Install Dependencies

```bash
# Install root dependencies
bun install

# Install Python dev dependencies
uv pip install -r requirements-dev.txt

# Install API dependencies
cd api && uv pip install -e . && cd ..

# Install Dashboard dependencies (if running frontend)
cd dashboard && bun install && cd ..
```

### 5. Start Backend Services

#### Option A: Using Just (Recommended)

```bash
# Start API server natively (fastest for development)
just api-native

# Or run API in Docker
just api-build
just api-run
```

#### Option B: Using Docker Compose

```bash
# Start all backend services
docker-compose up -d

# View logs
docker-compose logs -f
```

#### Option C: Manual Start

```bash
# Start API server
cd api
uv run python run.py
```

## Detailed Service Setup

### API Server (FastAPI)

The API server is the core backend service handling all business logic.

**Location**: `/app/api`

**Key Features**:
- RESTful API endpoints
- WebSocket support for real-time updates
- Authentication via JWT tokens
- Integration with ClickHouse and PostgreSQL
- Stripe billing integration

**Configuration** (`api/.env`):
```env
# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=true
LOGGING_LEVEL=INFO

# Security
JWT_SECRET_KEY=your-secret-key-here

# Database URLs
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# External Services
STRIPE_SECRET_KEY=sk_test_...
SENTRY_DSN=https://...@sentry.io/...
```

**Running the API**:
```bash
# Development (with hot reload)
cd api
uv run python run.py

# Production
uv run gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

### ClickHouse Database

ClickHouse stores time-series data for traces and analytics.

**Local Setup with Docker**:
```bash
# Start ClickHouse container
docker run -d \
  --name clickhouse \
  -p 9000:9000 \
  -p 8123:8123 \
  -e CLICKHOUSE_DB=agentops \
  -e CLICKHOUSE_USER=default \
  -e CLICKHOUSE_PASSWORD=password \
  clickhouse/clickhouse-server:latest
```

**Schema Setup**:
The API server automatically creates required tables on startup. Key tables include:
- `otel_traces` - Distributed tracing data
- `otel_logs` - Log entries
- `analytics_events` - Custom analytics events

### OpenTelemetry Collector

The OTel collector ingests telemetry data from agents.

**Location**: `/app/opentelemetry-collector`

**Configuration**:
- Receives data on ports 4317 (gRPC) and 4318 (HTTP)
- Processes and exports to ClickHouse
- JWT authentication for secure ingestion

**Running with Docker Compose**:
```bash
# The collector is included in the main compose.yaml
docker-compose up otelcollector
```

### PostgreSQL/Supabase

Stores user data, organizations, and metadata.

**Key Tables**:
- `users` - User accounts
- `organizations` - Organization data
- `projects` - Projects within organizations
- `api_keys` - API key management
- `billing_subscriptions` - Stripe subscription data

**Database Migrations**:
```bash
# Run migrations
cd api
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"
```

## Development Workflow

### 1. Local Development Setup

```bash
# Terminal 1: Start API server with hot reload
just api-native

# Terminal 2: Start frontend (optional)
just fe-run

# Terminal 3: Start supporting services
docker-compose up clickhouse otelcollector
```

### 2. Testing

```bash
# Run API tests
cd api
pytest

# Run specific test file
pytest tests/test_auth.py

# Run with coverage
pytest --cov=app --cov-report=html
```

### 3. Database Management

```bash
# Connect to ClickHouse
docker exec -it clickhouse clickhouse-client

# Connect to PostgreSQL
psql $DATABASE_URL

# View ClickHouse tables
SHOW TABLES FROM agentops;

# Query traces
SELECT * FROM otel_traces LIMIT 10;
```

### 4. Debugging

**API Debugging**:
- Enable debug mode: `DEBUG=true` in `.env`
- Access API docs: http://localhost:8000/docs
- View logs: Check console output or Docker logs

**Database Debugging**:
- ClickHouse UI: http://localhost:8123/play
- PostgreSQL: Use any PostgreSQL client
- Check connection: `curl http://localhost:8123/ping`

## Production Deployment

### Docker Compose Production

```bash
# Use production compose file
docker-compose -f compose.yaml up -d

# Scale API servers
docker-compose up -d --scale api=3
```

### Environment Variables for Production

```env
# Security
DEBUG=false
LOGGING_LEVEL=WARNING

# URLs
PROTOCOL=https
API_DOMAIN=api.yourdomain.com
APP_DOMAIN=app.yourdomain.com

# Database Connections
CLICKHOUSE_SECURE=true
DATABASE_URL=postgresql://user:pass@prod-host:5432/dbname
```

### Health Checks

The API provides health check endpoints:

```bash
# Basic health check
curl http://localhost:8000/health

# Detailed health with database status
curl http://localhost:8000/health/detailed
```

## Troubleshooting

### Common Issues

#### 1. ClickHouse Connection Failed

**Error**: `Connection refused to ClickHouse`

**Solution**:
```bash
# Check if ClickHouse is running
docker ps | grep clickhouse

# Check ClickHouse logs
docker logs clickhouse

# Test connection
curl http://localhost:8123/ping
```

#### 2. Authentication Errors

**Error**: `Invalid authentication credentials`

**Solution**:
- Verify Supabase keys in `.env`
- Check JWT_SECRET_KEY is set
- Ensure service role key is used for API

#### 3. Database Migration Issues

**Error**: `alembic.util.exc.CommandError`

**Solution**:
```bash
# Check current migration status
cd api
alembic current

# Reset migrations (development only)
alembic downgrade base
alembic upgrade head
```

#### 4. Port Conflicts

**Error**: `bind: address already in use`

**Solution**:
```bash
# Find process using port
lsof -i :8000

# Kill process
kill -9 <PID>

# Or use different port
PORT=8001 uv run python run.py
```

### Logging and Monitoring

**View API Logs**:
```bash
# Docker logs
docker-compose logs -f api

# Native logs
tail -f api/logs/app.log
```

**Enable Verbose Logging**:
```env
LOGGING_LEVEL=DEBUG
```

**Monitor Performance**:
- ClickHouse metrics: http://localhost:8123/metrics
- API metrics: http://localhost:8000/metrics
- OTel collector: http://localhost:55679/debug/tracez

### Getting Help

If you encounter issues:

1. Check the [GitHub Issues](https://github.com/AgentOps-AI/AgentOps/issues)
2. Review logs for error messages
3. Join our [Discord community](https://discord.gg/agentops)
4. Email support: support@agentops.ai

## Next Steps

- Set up the [Dashboard Frontend](./frontend-setup.md)
- Configure [Production Deployment](./deployment.md)
- Integrate the [AgentOps SDK](./sdk-integration.md)
- Review [API Documentation](http://localhost:8000/docs)