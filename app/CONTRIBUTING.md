# Contributing to AgentOps

Thank you for your interest in contributing to AgentOps! We welcome contributions from the community and are excited to see what you'll build.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Submitting Changes](#submitting-changes)
- [Code Style](#code-style)
- [Testing](#testing)
- [Documentation](#documentation)
- [Community](#community)

## 🤝 Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code. Please report unacceptable behavior to [conduct@agentops.ai](mailto:conduct@agentops.ai).

### Our Standards

- **Be respectful** and inclusive in your language and actions
- **Be collaborative** and help others learn and grow
- **Be constructive** when giving feedback
- **Focus on what's best** for the community and project

## 🚀 Getting Started

### Ways to Contribute

There are many ways to contribute to AgentOps:

- **🐛 Bug Reports**: Help us identify and fix issues
- **✨ Feature Requests**: Suggest new features or improvements
- **📝 Documentation**: Improve our docs, guides, and examples
- **💻 Code**: Fix bugs, implement features, or improve performance
- **🎨 Design**: Improve UI/UX, create graphics, or design assets
- **🧪 Testing**: Help test new features and report issues
- **💬 Community**: Help answer questions and support other users

### Before You Start

1. **Check existing issues** to see if your bug/feature is already being worked on
2. **Join our Discord** to discuss your ideas with the community
3. **Read this guide** to understand our development process
4. **Set up your development environment** following the instructions below

## 🛠️ Development Setup

### Prerequisites

Make sure you have the following installed:

- **Node.js** 18+ ([Download](https://nodejs.org/))
- **Python** 3.12+ ([Download](https://www.python.org/downloads/))
- **Docker & Docker Compose** ([Download](https://www.docker.com/get-started))
- **Bun** (recommended) or npm ([Install Bun](https://bun.sh/))
- **uv** (recommended for Python) ([Install uv](https://github.com/astral-sh/uv))
- **Git** ([Download](https://git-scm.com/downloads))

### Fork and Clone

1. **Fork the repository** on GitHub
2. **Clone your fork**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/agentops.git
   cd agentops
   ```
3. **Add the upstream remote**:
   ```bash
   git remote add upstream https://github.com/AgentOps-AI/agentops.git
   ```

### Environment Setup

1. **Copy environment files**:
   ```bash
   cp .env.example .env
   cp api/.env.example api/.env
   cp dashboard/.env.example dashboard/.env.local
   ```

2. **Set up external services** (see [External Services](#external-services) below)

3. **Install dependencies**:
   ```bash
   # Root dependencies (linting, formatting)
   bun install
   
   # Python dev dependencies
   uv pip install -r requirements-dev.txt
   
   # API dependencies
   cd api && uv pip install -e . && cd ..
   
   # Dashboard dependencies
   cd dashboard && bun install && cd ..
   ```

4. **Start development environment**:
   ```bash
   # Option 1: Use just commands (recommended)
   just api-run    # Start API server
   just fe-run     # Start frontend (in another terminal)
   
   # Option 2: Manual startup
   cd api && uv run python run.py &
   cd dashboard && bun dev &
   ```

### External Services

For development, you'll need to set up these external services:

#### Supabase (Required)
1. Create a project at [supabase.com](https://supabase.com)
2. Get your project URL and anon key from Settings → API
3. Update `.env` files with your credentials

#### ClickHouse (Required)
1. Sign up for [ClickHouse Cloud](https://clickhouse.com/cloud) (free tier available)
2. Create a database and get connection details
3. Update `.env` files with your credentials

#### PostgreSQL (Required)
Configure direct PostgreSQL connection for the API:
1. Use your Supabase PostgreSQL connection details
2. Update `.env` files with `POSTGRES_*` variables

#### Redis (Optional)
For caching (will fallback to SQLite for local development):
1. Set up Redis instance (local or cloud)
2. Update `.env` files with Redis connection details

#### Stripe (Optional - for billing features)
1. Create a [Stripe](https://stripe.com) account
2. Get test API keys from the dashboard
3. Update `.env` files with your credentials

## 🔄 Making Changes

### Branch Naming

Use descriptive branch names that follow this pattern:
- `feature/add-user-analytics` - New features
- `fix/dashboard-loading-issue` - Bug fixes
- `docs/update-api-guide` - Documentation updates
- `refactor/optimize-queries` - Code refactoring
- `test/add-integration-tests` - Test additions

### Development Workflow

1. **Create a new branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following our [code style guidelines](#code-style)

3. **Test your changes**:
   ```bash
   # Run tests
   cd api && pytest && ruff format
   cd dashboard && bun test
   
   # Run linting
   bun run lint
   ```

4. **Commit your changes**:
   ```bash
   git add .
   git commit -m "feat: add user analytics dashboard"
   ```

### Commit Message Format

We use [Conventional Commits](https://www.conventionalcommits.org/) for consistent commit messages:

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```bash
feat(dashboard): add real-time trace visualization
fix(api): resolve authentication token expiration
docs(readme): update installation instructions
test(api): add integration tests for billing endpoints
```

## 📤 Submitting Changes

### Pull Request Process

1. **Update your branch** with the latest changes:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Push your changes**:
   ```bash
   git push origin your-branch-name
   ```

3. **Create a Pull Request** on GitHub with:
   - **Clear title** describing the change
   - **Detailed description** explaining what and why
   - **Screenshots** for UI changes
   - **Testing instructions** for reviewers
   - **Issue references** (e.g., "Closes #123")

### Pull Request Template

```markdown
## Description
Brief description of changes made.

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing
- [ ] Tests pass locally
- [ ] Added/updated tests for changes
- [ ] Manual testing completed

## Screenshots (if applicable)
Add screenshots to help explain your changes.

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Code is commented where necessary
- [ ] Documentation updated
- [ ] No new warnings introduced
```

### Review Process

1. **Automated checks** must pass (linting, tests, build)
2. **Code review** by maintainers and community members
3. **Address feedback** and update your PR as needed
4. **Final approval** and merge by maintainers

## 🎨 Code Style

### JavaScript/TypeScript

We use **ESLint** and **Prettier** for consistent formatting:

```bash
# Check linting
bun run lint:js

# Fix linting issues
bun run lint:js --fix

# Format code
bun run format:js
```

**Key conventions:**
- Use **TypeScript** for type safety
- Prefer **const** and **let** over **var**
- Use **arrow functions** for short functions
- Use **async/await** over promises when possible
- Follow **React Hooks** best practices

### Python

We use **Ruff** for linting and formatting:

```bash
# Check linting
bun run lint:py

# Format code (runs 'ruff format')
bun run format:py
```

**Key conventions:**
- Follow **PEP 8** style guide
- Use **type hints** for function parameters and returns
- Prefer **f-strings** for string formatting
- Use **dataclasses** or **Pydantic** models for structured data
- Follow **FastAPI** best practices

### General Guidelines

- **Write clear, self-documenting code**
- **Add comments for complex logic**
- **Use meaningful variable and function names**
- **Keep functions small and focused**
- **Follow existing patterns in the codebase**

## 🧪 Testing

**Docker is required** to run tests since they create PostgreSQL & ClickHouse instances.

### Running Tests

```bash
# API tests (requires Docker)
cd api && pytest

# Frontend tests
cd dashboard && bun test

# Integration tests (requires Docker)
cd api && pytest tests/integration/

# End-to-end tests
cd dashboard && bun run test:e2e
```

### Writing Tests

#### API Tests (Python)
- Use **pytest** for test framework
- Use **fixtures** for test data setup
- Test **happy paths** and **error cases**
- Mock **external services** in unit tests

```python
def test_create_user_success(client, db_session):
    """Test successful user creation."""
    user_data = {"email": "test@example.com", "name": "Test User"}
    response = client.post("/users", json=user_data)
    assert response.status_code == 201
    assert response.json()["email"] == user_data["email"]
```

#### Frontend Tests (TypeScript)
- Use **Jest** and **React Testing Library**
- Test **user interactions** and **component behavior**
- Mock **API calls** and **external dependencies**

```typescript
test('displays user dashboard correctly', async () => {
  render(<Dashboard user={mockUser} />);
  expect(screen.getByText('Welcome, Test User')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'View Analytics' })).toBeInTheDocument();
});
```

### Test Coverage

- Aim for **80%+ code coverage**
- Focus on **critical paths** and **business logic**
- Include **edge cases** and **error scenarios**

## 📚 Documentation

### Types of Documentation

1. **Code Comments**: Explain complex logic and decisions
2. **API Documentation**: Auto-generated from code annotations
3. **User Guides**: Step-by-step instructions for users
4. **Developer Docs**: Technical implementation details

### Writing Guidelines

- **Be clear and concise**
- **Use examples** to illustrate concepts
- **Keep docs up-to-date** with code changes
- **Include screenshots** for UI features
- **Test instructions** to ensure they work

### Documentation Structure

```
docs/
├── api/              # API reference
├── guides/           # User guides
├── development/      # Developer documentation
├── deployment/       # Deployment guides
└── examples/         # Code examples
```

## 👥 Community

### Getting Help

- **GitHub Issues**: For bugs and feature requests
- **GitHub Discussions**: For questions and general discussion
- **Discord**: For real-time chat and community support
- **Email**: [support@agentops.ai](mailto:support@agentops.ai) for private matters

### Helping Others

- **Answer questions** in issues and discussions
- **Review pull requests** from other contributors
- **Share examples** and use cases
- **Write tutorials** and blog posts

### Recognition

We recognize contributors in several ways:
- **Contributors list** in README
- **Release notes** mention significant contributions
- **Swag and rewards** for major contributions
- **Maintainer status** for consistent, high-quality contributions

## 🏷️ Issue Labels

We use labels to categorize and prioritize issues:

- **`good first issue`**: Great for new contributors
- **`help wanted`**: Community contributions welcome
- **`bug`**: Something isn't working
- **`enhancement`**: New feature or improvement
- **`documentation`**: Documentation needs
- **`question`**: Further information requested
- **`priority: high`**: Urgent issues
- **`priority: low`**: Nice-to-have improvements

## 🎯 Roadmap

Check out our [public roadmap](https://github.com/AgentOps-AI/agentops/projects) to see what we're working on and where you can help.

### Current Focus Areas

- **Performance optimization** for large-scale deployments
- **Enhanced visualization** features
- **Integration ecosystem** expansion
- **Developer experience** improvements
- **Documentation** and **examples**

## ❓ FAQ

### How do I get started as a new contributor?

1. Look for issues labeled `good first issue`
2. Join our Discord to introduce yourself
3. Set up your development environment
4. Start with documentation or small bug fixes
5. Ask questions - we're here to help!

### What if I want to work on a big feature?

1. Open an issue to discuss your idea first
2. Get feedback from maintainers and community
3. Create a design document for complex features
4. Break the work into smaller, reviewable PRs
5. Keep the community updated on your progress

### How long does it take to get a PR reviewed?

- **Simple fixes**: Usually within 1-2 days
- **New features**: May take 3-7 days for thorough review
- **Complex changes**: Could take 1-2 weeks with multiple review rounds

We aim to provide initial feedback quickly and will let you know if we need more time.

### Can I contribute if I'm not a developer?

Absolutely! We welcome contributions in many forms:
- **Documentation** improvements
- **Design** and **UX** feedback  
- **Testing** and **bug reports**
- **Community support** and **advocacy**
- **Content creation** (blogs, tutorials, videos)

---

## 🙏 Thank You

Thank you for taking the time to contribute to AgentOps! Every contribution, no matter how small, helps make the project better for everyone.

If you have any questions or need help getting started, don't hesitate to reach out. We're excited to see what you'll build with us!

Happy coding! 🚀 