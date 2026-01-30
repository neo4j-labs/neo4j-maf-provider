# Contributing to Neo4j Context Provider

Thank you for your interest in contributing to the Neo4j Context Provider for Microsoft Agent Framework!

## Getting Started

1. Fork the repository
2. Clone your fork locally
3. Set up the development environment for your language

### Python Development

```bash
cd python
uv sync --prerelease=allow
```

See [python/DEV_SETUP.md](python/DEV_SETUP.md) for detailed setup instructions.

### .NET Development

Coming soon.

## Development Workflow

1. Create a new branch from `main`
2. Make your changes
3. Run language-specific checks
4. Commit your changes
5. Push to your fork
6. Create a Pull Request

### Python Checks

Before submitting a PR, ensure all checks pass:

```bash
cd python

# Run tests
uv run pytest

# Type checking
uv run mypy packages/agent-framework-neo4j/agent_framework_neo4j

# Linting
uv run ruff check packages/agent-framework-neo4j/agent_framework_neo4j

# Format
uv run ruff format packages/agent-framework-neo4j/agent_framework_neo4j
```

## Code Style

### Python

- Line length: 120 characters
- Type hints: Required (strict mypy)
- Docstrings: Google style where needed
- Imports: Sorted by isort (via ruff)

See `python/pyproject.toml` for complete configuration.

### .NET

Coming soon.

## Pull Request Guidelines

- Keep PRs focused on a single change
- Include tests for new functionality
- Update documentation as needed
- Ensure all CI checks pass

## Reporting Issues

Please report issues at the repository's issue tracker. Include:

- A clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python/.NET version, etc.)

## Questions?

For questions about the project, open a discussion or issue in the repository.
