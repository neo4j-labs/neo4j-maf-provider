# Python Development Setup

This guide covers setting up the Python development environment for the Neo4j Context Provider.

## Prerequisites

- Python 3.10 or later
- [uv](https://docs.astral.sh/uv/) - Fast Python package manager
- Git

## Quick Setup

```bash
# Clone the repository
git clone https://github.com/neo4j-partners/neo4j-maf-provider.git
cd neo4j-maf-provider/python

# Install dependencies (including dev dependencies)
uv sync --prerelease=allow
```

This creates a virtual environment in `.venv/` and installs all packages.

## Project Structure

```
python/
├── packages/
│   └── agent-framework-neo4j/     # Main library package
│       ├── pyproject.toml         # Package configuration
│       └── agent_framework_neo4j/ # Source code
├── samples/                       # Demo applications
│   ├── pyproject.toml            # Samples package config
│   └── src/samples/              # Sample source code
├── tests/                         # Test suite
├── docs/                          # Python documentation
├── pyproject.toml                 # Workspace configuration
└── uv.lock                        # Dependency lock file
```

## UV Workspace

This is a UV workspace monorepo with two packages:

| Package | Location | Purpose |
|---------|----------|---------|
| `agent-framework-neo4j` | `packages/agent-framework-neo4j/` | Publishable PyPI library |
| `neo4j-provider-samples` | `samples/` | Demo applications |

## Development Commands

### Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov

# Run specific test file
uv run pytest tests/test_provider.py

# Run specific test
uv run pytest tests/test_provider.py::TestProviderInit::test_init_fulltext
```

### Type Checking

```bash
# MyPy strict mode
uv run mypy packages/agent-framework-neo4j/agent_framework_neo4j
```

### Linting and Formatting

```bash
# Check for issues
uv run ruff check packages/agent-framework-neo4j/agent_framework_neo4j

# Auto-fix issues
uv run ruff check --fix packages/agent-framework-neo4j/agent_framework_neo4j

# Format code
uv run ruff format packages/agent-framework-neo4j/agent_framework_neo4j
```

### Building

```bash
# Build the library
uv build --package agent-framework-neo4j

# Output in dist/
ls dist/
# agent_framework_neo4j-0.1.0-py3-none-any.whl
# agent_framework_neo4j-0.1.0.tar.gz
```

## Running Samples

```bash
# Interactive menu
uv run start-samples

# Run specific sample (1-8)
uv run start-samples 3

# Run all samples
uv run start-samples a
```

## Environment Variables

Create `samples/.env` for running samples:

```bash
# Neo4j Connection
NEO4J_URI=neo4j+s://xxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password

# Azure AI (populated by setup_env.py)
AZURE_AI_PROJECT_ENDPOINT=https://...
AZURE_AI_MODEL_NAME=gpt-4o
AZURE_AI_EMBEDDING_NAME=text-embedding-ada-002
```

## IDE Setup

### VS Code

Recommended extensions:
- Python (Microsoft)
- Pylance
- Ruff

Settings (`.vscode/settings.json`):
```json
{
    "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
    "python.analysis.typeCheckingMode": "strict",
    "editor.formatOnSave": true,
    "[python]": {
        "editor.defaultFormatter": "charliermarsh.ruff"
    }
}
```

### PyCharm

1. Open the `python/` directory as your project root
2. Set the Python interpreter to `.venv/bin/python`
3. Mark `packages/agent-framework-neo4j/agent_framework_neo4j` as Sources Root
4. Mark `samples/src` as Sources Root

## Publishing

See [docs/PUBLISH.md](docs/PUBLISH.md) for the complete publishing guide.

Quick version:
```bash
# Update version in pyproject.toml and __init__.py, then:
./scripts/publish.sh $PYPI_TOKEN
```

## Troubleshooting

### uv sync fails

```bash
# Clear cache and retry
uv cache clean
uv sync --prerelease=allow
```

### Import errors

Ensure you're running from the `python/` directory:
```bash
cd python
uv run pytest
```

### Type checking errors

The library uses strict mypy. Common issues:
- Missing return type annotations
- Untyped function parameters
- Missing Optional[] for nullable values

## Code Style

- Line length: 120 characters
- Python version target: 3.10
- Type hints: Required (strict mypy)
- Docstrings: Google style (where needed)
- Imports: Sorted by isort (via ruff)

See `pyproject.toml` for complete ruff and mypy configuration.
