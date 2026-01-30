# Publishing to PyPI

This guide covers building and publishing the `agent-framework-neo4j` package to PyPI.

## Prerequisites

1. PyPI account with API token
2. All tests passing (`uv run pytest`)
3. Type checks passing (`uv run mypy packages/agent-framework-neo4j/agent_framework_neo4j`)

## Version Management

Update versions in both files before publishing:

- `packages/agent-framework-neo4j/pyproject.toml` - the `version` field
- `packages/agent-framework-neo4j/agent_framework_neo4j/__init__.py` - the `__version__` variable

Both must match. Follow [semantic versioning](https://semver.org/):
- **major** (1.0.0) - Breaking changes
- **minor** (0.2.0) - New features, backwards compatible
- **patch** (0.1.1) - Bug fixes, backwards compatible

## Quick Publish

Use the publish script for a single-command build and publish:

```bash
./scripts/publish.sh <pypi-token>
```

The script:
1. Cleans the `dist/` directory
2. Builds the package with `uv build`
3. Publishes to PyPI with `uv publish`

## Manual Build

```bash
# Build the package (only the library, not samples)
uv build --package agent-framework-neo4j

# Verify the build artifacts
ls dist/
# Should show: agent_framework_neo4j-X.Y.Z.tar.gz and agent_framework_neo4j-X.Y.Z-py3-none-any.whl

# Optional: verify package builds without workspace sources
# This ensures the package works when installed from PyPI
uv build --package agent-framework-neo4j --no-sources
```

## Authentication

PyPI requires token authentication (username/password no longer supported).

### Option 1: Pass Token Directly

```bash
uv publish --token pypi-YOUR_TOKEN_HERE
```

### Option 2: Environment Variable

```bash
export UV_PUBLISH_TOKEN=pypi-YOUR_TOKEN_HERE
uv publish
```

### Option 3: Trusted Publisher (GitHub Actions)

No credentials needed when publishing from GitHub Actions. Configure a trusted publisher in your PyPI project settings.

See: https://docs.pypi.org/trusted-publishers/

## Generating a PyPI Token

1. Log in to https://pypi.org
2. Go to **Account Settings** → **API tokens**
3. Click **Add API token**
4. For first publish: create an account-scoped token
5. After first publish: create a project-scoped token for `agent-framework-neo4j`

## Publishing Workflow

Complete workflow from version bump to publish:

```bash
# 1. Update version in both files
#    - packages/agent-framework-neo4j/pyproject.toml
#    - packages/agent-framework-neo4j/agent_framework_neo4j/__init__.py

# 2. Review changes
git diff

# 3. Run tests
uv run pytest

# 4. Commit and tag
git add -A
git commit -m "Bump version to X.Y.Z"
git tag vX.Y.Z

# 5. Build and publish
./scripts/publish.sh $PYPI_TOKEN

# 6. Push to remote
git push && git push --tags
```

## Testing with TestPyPI

Before publishing to production PyPI, you can test with TestPyPI:

```bash
# Publish to TestPyPI
uv publish --index-url https://test.pypi.org/legacy/ --token $TEST_PYPI_TOKEN

# Install from TestPyPI to verify
pip install --index-url https://test.pypi.org/simple/ agent-framework-neo4j
```

## Package Naming

The package follows the Microsoft Agent Framework naming convention:

| Aspect | Value |
|--------|-------|
| **PyPI package name** | `agent-framework-neo4j` |
| **Python import** | `agent_framework_neo4j` |
| **Install command** | `pip install agent-framework-neo4j --pre` |

PyPI normalizes package names, so hyphens, underscores, and case are equivalent for installation.

## What Gets Published

Only the library package is published:
- `packages/agent-framework-neo4j/` - Published to PyPI

The following are **not** published:
- `samples/` - Demo applications (no build system)
- `tests/` - Library tests
- `docs/` - Documentation
- Root workspace configuration
