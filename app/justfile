# AgentOps Development Commands
# 
# This justfile provides convenient commands for developing AgentOps.
# Make sure you have set up your environment variables first:
#   cp .env.example .env
#   cp api/.env.example api/.env  
#   cp dashboard/.env.example dashboard/.env.local

# Show all available commands
default:
    @echo "🚀 AgentOps Development Commands"
    @echo ""
    @echo "📋 Setup:"
    @echo "  setup              Set up development environment"
    @echo "  install            Install all dependencies"
    @echo ""
    @echo "🔧 API Development:"
    @echo "  api-native         Run API server natively (fastest)"
    @echo "  api-build          Build API Docker image"
    @echo "  api-run            Run API in Docker container"
    @echo "  api-test           Run API tests"
    @echo ""
    @echo "🎨 Frontend Development:"
    @echo "  fe-run             Run dashboard development server"
    @echo "  fe-build           Build dashboard for production"
    @echo "  fe-test            Run frontend tests"
    @echo ""
    @echo "🧹 Code Quality:"
    @echo "  lint               Run all linting checks"
    @echo "  format             Format all code"
    @echo "  test               Run all tests"
    @echo ""
    @echo "🐳 Docker:"
    @echo "  up                 Start all services with Docker Compose"
    @echo "  down               Stop all Docker services"
    @echo "  logs               View Docker logs"
    @echo ""
    @echo "💡 Tip: Run 'just setup' first if this is your first time!"

# Set up development environment
setup:
    @echo "🔧 Setting up AgentOps development environment..."
    @echo "📄 Copying environment files..."
    @if [ ! -f .env ]; then cp .env.example .env && echo "✅ Created .env"; fi
    @if [ ! -f api/.env ]; then cp api/.env.example api/.env && echo "✅ Created api/.env"; fi
    @if [ ! -f dashboard/.env.local ]; then cp dashboard/.env.example dashboard/.env.local && echo "✅ Created dashboard/.env.local"; fi
    @echo ""
    @echo "📦 Installing dependencies..."
    just install
    @echo ""
    @echo "✅ Setup complete!"
    @echo ""
    @echo "🔔 Next steps:"
    @echo "  1. Update your .env files with real credentials"
    @echo "  2. Set up external services (Supabase, ClickHouse, etc.)"
    @echo "  3. Run 'just api-run' and 'just fe-run' to start development"

# Install all dependencies
install:
    @echo "📦 Installing root dependencies..."
    bun install
    @echo "🐍 Installing Python dev dependencies..."
    uv pip install -r requirements-dev.txt
    @echo "🔧 Installing API dependencies..."
    cd api && uv pip install -e .
    @echo "⚛️ Installing dashboard dependencies..."
    cd dashboard && bun install
    @echo "✅ All dependencies installed!"

# --- Backend API Commands ---

# Run API server natively (fastest for development)
api-native:
    @echo "🚀 Starting API server natively..."
    cd api && uv run python run.py

# Build API Docker image  
api-build stripe_flag="":
    @echo "🐳 Building API Docker image..."
    ./scripts/just-api-build.sh {{stripe_flag}}

# Run API server in Docker container
api-run stripe_flag="":
    @echo "🐳 Starting API server in Docker..."
    ./scripts/just-api-run.sh {{stripe_flag}}

# Run API tests
api-test:
    @echo "🧪 Running API tests..."
    cd api && pytest

# --- Frontend Commands ---

# Run dashboard development server
fe-run:
    @echo "⚛️ Starting dashboard development server..."
    cd dashboard && bun install && bun run dev

# Build dashboard for production
fe-build:
    @echo "📦 Building dashboard for production..."
    cd dashboard && bun run build

# Run frontend tests
fe-test:
    @echo "🧪 Running frontend tests..."
    cd dashboard && bun test

# --- Code Quality Commands ---

# Run all linting checks
lint:
    @echo "🔍 Running linting checks..."
    bun run lint

# Format all code (runs ruff format for Python)
format:
    @echo "✨ Formatting code..."
    ruff format

# Run all tests
test:
    @echo "🧪 Running all tests..."
    just api-test
    just fe-test

# --- Docker Commands ---

# Start all services with Docker Compose
up:
    @echo "🐳 Starting all services with Docker Compose..."
    docker-compose up -d

# Stop all Docker services
down:
    @echo "🛑 Stopping all Docker services..."
    docker-compose down

# View Docker logs
logs:
    @echo "📋 Viewing Docker logs..."
    docker-compose logs -f

# Clean up Docker resources
clean:
    @echo "🧹 Cleaning up Docker resources..."
    docker-compose down -v
    docker system prune -f
