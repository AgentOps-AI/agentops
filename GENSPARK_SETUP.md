# GenSpark AI Developer Setup

This document describes the setup and workflow for the GenSpark AI Developer branch.

## Branch Information

- **Branch Name**: `genspark_ai_developer`
- **Purpose**: AI-assisted development and enhancements for AgentOps
- **Base Branch**: `main`

## Setup Completed

### ✅ Environment Configuration

1. **Branch Created**: `genspark_ai_developer` branch has been created and checked out
2. **Python Version**: Python 3.12.11
3. **Package Manager**: pip 25.0.1
4. **Pre-commit Hooks**: Installed and configured with ruff linter

### ✅ Dependencies Installed

The following dependency groups have been installed:

- **Core Dependencies**: All required packages from `pyproject.toml`
- **Development Tools**: pytest, ruff, mypy, and other dev tools
- **OpenTelemetry Stack**: Full observability stack for monitoring
- **Pre-commit**: Code quality enforcement tools

## Development Workflow

### Making Changes

1. **Make your code changes** in the appropriate files
2. **Test your changes** locally:
   ```bash
   pytest tests/
   ```

3. **MANDATORY: Commit immediately after changes**:
   ```bash
   git add .
   git commit -m "type(scope): description"
   ```

4. **Sync with remote before PR**:
   ```bash
   git fetch origin main
   git rebase origin/main
   # Resolve any conflicts, prioritizing remote code
   ```

5. **Squash all commits into one**:
   ```bash
   # Count your commits first
   git log --oneline
   # Squash N commits (replace N with your number)
   git reset --soft HEAD~N
   git commit -m "comprehensive commit message describing all changes"
   ```

6. **Push to remote**:
   ```bash
   git push -f origin genspark_ai_developer
   ```

7. **Create or Update Pull Request**:
   - Create PR from `genspark_ai_developer` to `main`
   - Include comprehensive description
   - Share PR link with team

### Commit Message Format

Use conventional commit format:
```
type(scope): description

Examples:
- feat(llms): add support for new LLM provider
- fix(client): resolve connection timeout issue
- docs(readme): update installation instructions
- test(integration): add tests for new feature
```

### Code Quality

Pre-commit hooks will automatically:
- Run ruff linter with auto-fix
- Format code with ruff-format
- Ensure code quality before each commit

## Repository Structure

```
agentops/
├── agentops/          # Main SDK package
│   ├── llms/         # LLM provider integrations
│   ├── sdk/          # Core SDK functionality
│   └── ...
├── app/              # Dashboard application
├── tests/            # Test suite
├── examples/         # Usage examples
├── docs/             # Documentation
└── pyproject.toml    # Project configuration
```

## Testing

Run tests with:
```bash
# All tests
pytest tests/

# Specific test file
pytest tests/llms/test_anthropic.py -v

# With coverage
coverage run -m pytest
coverage report
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed contribution guidelines.

## Important Notes

- **NO UNCOMMITTED CHANGES**: Every code change must be committed
- **SYNC BEFORE PR**: Always fetch and merge latest remote changes before creating PR
- **SQUASH COMMITS**: Combine all commits into one comprehensive commit
- **RESOLVE CONFLICTS**: Prioritize remote code when resolving conflicts
- **SHARE PR LINK**: Always provide the PR URL after creation/update

## Resources

- [Main README](README.md)
- [Contributing Guide](CONTRIBUTING.md)
- [AgentOps Documentation](https://docs.agentops.ai)
- [Discord Community](https://discord.gg/FagdcwwXRR)

## Setup Date

- **Created**: 2025-10-19
- **Python Version**: 3.12.11
- **Branch Status**: Clean, ready for development
