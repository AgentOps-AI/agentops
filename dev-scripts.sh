#!/bin/bash
# Development Helper Scripts for AgentOps

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Check current branch
check_branch() {
    CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
    if [ "$CURRENT_BRANCH" != "genspark_ai_developer" ]; then
        print_warning "You are on branch '$CURRENT_BRANCH', not 'genspark_ai_developer'"
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# Setup development environment
setup() {
    print_status "Setting up development environment..."
    
    # Install dependencies
    print_status "Installing dependencies..."
    pip install -e ".[dev]"
    
    # Install pre-commit hooks
    print_status "Installing pre-commit hooks..."
    python3 -m pre_commit install
    
    # Create .env file if it doesn't exist
    if [ ! -f .env ]; then
        print_warning ".env file not found. Creating from .env.example..."
        cp .env.example .env
        print_warning "Please edit .env file with your actual API keys"
    fi
    
    print_status "Setup complete!"
}

# Run tests
test() {
    print_status "Running tests..."
    pytest tests/ -v
}

# Run tests with coverage
test_coverage() {
    print_status "Running tests with coverage..."
    coverage run -m pytest
    coverage report
    coverage html
    print_status "Coverage report generated in htmlcov/index.html"
}

# Run linter
lint() {
    print_status "Running linter..."
    python3 -m pre_commit run --all-files
}

# Sync with upstream
sync() {
    check_branch
    print_status "Syncing with upstream main..."
    
    # Fetch latest changes
    git fetch origin main
    
    # Check for uncommitted changes
    if ! git diff-index --quiet HEAD --; then
        print_error "You have uncommitted changes. Please commit or stash them first."
        exit 1
    fi
    
    # Rebase on main
    print_status "Rebasing on origin/main..."
    git rebase origin/main
    
    print_status "Sync complete!"
}

# Squash commits
squash() {
    check_branch
    
    # Count commits ahead of main
    COMMITS_AHEAD=$(git rev-list --count origin/main..HEAD)
    
    if [ "$COMMITS_AHEAD" -eq 0 ]; then
        print_warning "No commits to squash"
        exit 0
    fi
    
    print_status "Found $COMMITS_AHEAD commits ahead of main"
    read -p "Squash all $COMMITS_AHEAD commits? (y/n) " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "Squashing commits..."
        git reset --soft HEAD~$COMMITS_AHEAD
        
        print_status "Enter commit message (Ctrl+D when done):"
        COMMIT_MSG=$(cat)
        
        git commit -m "$COMMIT_MSG"
        print_status "Commits squashed successfully!"
        print_warning "Don't forget to push with: git push -f origin genspark_ai_developer"
    fi
}

# Create PR workflow
prepare_pr() {
    check_branch
    print_status "Preparing for Pull Request..."
    
    # Sync with main
    print_status "Step 1: Syncing with main..."
    sync
    
    # Squash commits
    print_status "Step 2: Squashing commits..."
    squash
    
    # Push to remote
    print_status "Step 3: Pushing to remote..."
    read -p "Push to origin? (y/n) " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git push -f origin genspark_ai_developer
        print_status "Pushed successfully!"
        print_status "Next step: Create PR from genspark_ai_developer to main"
        print_status "GitHub URL: https://github.com/MrBomaye/agentops/compare/main...genspark_ai_developer"
    fi
}

# Show help
help() {
    echo "AgentOps Development Scripts"
    echo ""
    echo "Usage: ./dev-scripts.sh [command]"
    echo ""
    echo "Commands:"
    echo "  setup          - Setup development environment"
    echo "  test           - Run tests"
    echo "  test_coverage  - Run tests with coverage report"
    echo "  lint           - Run linter and code formatter"
    echo "  sync           - Sync with upstream main branch"
    echo "  squash         - Squash all commits into one"
    echo "  prepare_pr     - Complete workflow: sync, squash, push"
    echo "  help           - Show this help message"
}

# Main script logic
case "$1" in
    setup)
        setup
        ;;
    test)
        test
        ;;
    test_coverage)
        test_coverage
        ;;
    lint)
        lint
        ;;
    sync)
        sync
        ;;
    squash)
        squash
        ;;
    prepare_pr)
        prepare_pr
        ;;
    help|*)
        help
        ;;
esac
