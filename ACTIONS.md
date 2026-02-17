# GitHub Actions CI/CD Proposal

This document proposes a GitHub Actions workflow to automate testing, building, and publishing the `agent-framework-neo4j` Python library to PyPI.

## Executive Summary

Implement a modern CI/CD pipeline using GitHub Actions with PyPI Trusted Publishing (OIDC-based authentication). This approach eliminates the need for long-lived API tokens and follows 2025 best practices for secure Python package publishing.

---

## Part 1: PyPI Setup

### For a New Package (Pending Publisher)

If the package does not yet exist on PyPI, configure a "pending publisher" before the first release:

1. Sign in to [PyPI](https://pypi.org) with the account that will own the package
2. Navigate to **Your account** → **Publishing**
3. Under "Add a new pending publisher", fill in:
   - **PyPI Project Name**: `agent-framework-neo4j`
   - **Owner**: The GitHub username or organization (e.g., `microsoft` or your org)
   - **Repository name**: `neo4j-maf-provider`
   - **Workflow name**: `release.yml` (the exact filename under `.github/workflows/`)
   - **Environment name**: `pypi` (strongly recommended for security)
4. Click **Add**

Once the first successful publish occurs, the pending publisher automatically converts to an active publisher.

### For an Existing Package

If the package already exists on PyPI:

1. Navigate to [https://pypi.org/manage/project/agent-framework-neo4j/settings/publishing/](https://pypi.org/manage/project/agent-framework-neo4j/settings/publishing/)
2. Under "Add a new publisher", select **GitHub** and fill in:
   - **Owner**: Your GitHub organization or username
   - **Repository name**: `neo4j-maf-provider`
   - **Workflow name**: `release.yml`
   - **Environment name**: `pypi`
3. Click **Add**

### TestPyPI (Recommended for Testing)

Repeat the above steps on [TestPyPI](https://test.pypi.org) to enable testing the publishing workflow before production releases. Use a separate workflow file or environment name (e.g., `testpypi`).

---

## Part 2: GitHub Repository Setup

### Create a Protected Environment

1. Go to **Settings** → **Environments** in the GitHub repository
2. Click **New environment** and name it `pypi`
3. Configure protection rules:
   - **Required reviewers**: Add 1-2 maintainers who must approve releases
   - **Wait timer**: Optional delay (e.g., 5 minutes) to allow cancellation
   - **Deployment branches**: Restrict to `main` branch only

This environment gate ensures releases require manual approval from trusted maintainers.

### Branch Protection Rules

1. Go to **Settings** → **Branches** → **Add branch protection rule**
2. For branch name pattern `main`, enable:
   - Require pull request reviews before merging
   - Require status checks to pass before merging
   - Require branches to be up to date before merging
   - Select the CI workflow jobs as required status checks

### No Secrets Required

With Trusted Publishing, no API tokens or secrets need to be stored in GitHub. The OIDC token exchange handles authentication automatically.

---

## Part 3: Workflow Architecture

The pipeline should consist of two separate workflows:

### Workflow 1: Continuous Integration (`ci.yml`)

Triggered on every push and pull request. Runs all quality checks.

**Triggers:**
- Push to any branch
- Pull requests to `main`

**Jobs:**

1. **Test Matrix**: Run tests across Python 3.10, 3.11, and 3.12
2. **Lint**: Run Ruff linting checks
3. **Type Check**: Run mypy strict type checking
4. **Build Verification**: Ensure package builds successfully

### Workflow 2: Release Publishing (`release.yml`)

Triggered when a version tag is pushed (e.g., `v0.1.0`). Builds and publishes to PyPI.

**Triggers:**
- Push of tags matching `v*` pattern (e.g., `v0.1.0`, `v1.0.0-beta.1`)

**Jobs:**

1. **Test**: Re-run the full test suite to ensure tag is clean
2. **Build**: Build the distribution packages (wheel and sdist)
3. **Publish**: Upload to PyPI using Trusted Publishing

---

## Part 4: Tests to Run

The CI pipeline must execute the following quality checks from the `python/` directory:

### Unit Tests

Run the pytest test suite with coverage reporting:

- **Command**: `uv run pytest --cov --cov-report=xml`
- **Tests location**: `python/tests/`
- **Current test coverage**: The test file `test_provider.py` includes:
  - Settings validation tests (environment loading, defaults)
  - Provider initialization tests (required parameters, defaults, validation)
  - Graph enrichment configuration tests

### Type Checking

Run mypy in strict mode on the library code:

- **Command**: `uv run mypy packages/agent-framework-neo4j/agent_framework_neo4j`
- **Configuration**: Uses strict mode with Pydantic plugin (defined in `pyproject.toml`)

### Linting

Run Ruff for style and correctness checks:

- **Command**: `uv run ruff check packages/agent-framework-neo4j/agent_framework_neo4j`
- **Rules**: E, W, F, I, B, C4, UP, ARG, SIM (defined in `pyproject.toml`)

### Format Verification

Verify code formatting matches Ruff's style:

- **Command**: `uv run ruff format --check packages/agent-framework-neo4j/agent_framework_neo4j`

### Build Verification

Ensure the package builds successfully:

- **Command**: `uv build --package agent-framework-neo4j`
- **Outputs**: Wheel (`.whl`) and source distribution (`.tar.gz`) in `dist/`

---

## Part 5: Workflow Details

### CI Workflow Behavior

- Uses `astral-sh/setup-uv` action with caching enabled for fast dependency installation
- Runs `uv sync --locked --all-extras --dev` to install from lockfile
- Executes test matrix in parallel across Python versions
- Lint and type-check jobs can run in parallel with tests
- All jobs must pass before PRs can be merged

### Release Workflow Behavior

- Only runs on version tags (prevents accidental releases)
- Requires the protected `pypi` environment (manual approval)
- Builds artifacts in one job, publishes in a separate job (security best practice)
- Uses `pypa/gh-action-pypi-publish` action with Trusted Publishing
- Automatically generates signed attestations for all distribution files
- No tokens or passwords needed in the workflow

### Key Workflow Requirements

1. **Permissions**: The publish job must have `id-token: write` permission for OIDC
2. **Environment**: The publish job must use `environment: pypi` to match PyPI configuration
3. **Artifact passing**: Build and publish must be separate jobs; artifacts passed via `actions/upload-artifact` and `actions/download-artifact`
4. **Version pinning**: Pin action versions to specific tags (e.g., `@v7`) rather than branch refs

---

## Part 6: Security Best Practices

### Trusted Publishing Benefits

- **No stored secrets**: Eliminates risk of token theft or leakage
- **Short-lived tokens**: OIDC tokens expire automatically (typically 15 minutes)
- **Audit trail**: All publishes tied to specific workflow runs
- **Digital attestations**: Sigstore-signed attestations verify package provenance

### Workflow Security

- **Separate build and publish jobs**: The job that builds artifacts should not have publish permissions
- **Protected environment**: Manual approval required before publishing
- **Branch restrictions**: Only allow releases from `main` branch
- **Pinned action versions**: Prevents supply chain attacks via mutable refs

### Repository Security

- **Branch protection**: Require PR reviews and status checks before merging
- **No force pushes**: Prevent history rewriting on `main`
- **Signed commits**: Consider requiring GPG-signed commits for releases

---

## Part 7: Release Process

With this setup, the release process becomes:

1. Update version in `python/packages/agent-framework-neo4j/pyproject.toml`
2. Create and push a version tag: `git tag v0.1.0 && git push origin v0.1.0`
3. The release workflow triggers automatically
4. A maintainer approves the deployment in the GitHub Actions UI
5. Package is published to PyPI with signed attestations

---

## Part 8: Optional Enhancements

### TestPyPI Integration

Add a separate workflow or job to publish to TestPyPI on pre-release tags (e.g., `v0.1.0-rc.1`). This allows testing the full publish flow without affecting production.

### Changelog Generation

Consider using `actions/create-release` or similar to auto-generate GitHub Releases with changelogs from commit messages or a CHANGELOG file.

### Dependabot for Actions

Enable Dependabot to keep GitHub Actions up to date:

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
```

### Coverage Reporting

Upload coverage reports to Codecov or Coveralls for PR visibility:

- Requires adding `CODECOV_TOKEN` secret (for private repos)
- Use `codecov/codecov-action` after pytest runs

---

## References

- [Python Packaging Guide: Publishing with GitHub Actions](https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/)
- [PyPI Trusted Publishers Documentation](https://docs.pypi.org/trusted-publishers/)
- [GitHub Actions: Configuring OIDC for PyPI](https://docs.github.com/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-pypi)
- [uv GitHub Actions Integration](https://docs.astral.sh/uv/guides/integration/github/)
- [pypa/gh-action-pypi-publish](https://github.com/pypa/gh-action-pypi-publish)
- [Modern Python Package CI/CD with uv and Trusted Publishing](https://dwflanagan.com/blog/til-publishing-packages/)
- [GitHub Actions for Python (2025)](https://ber2.github.io/posts/2025_github_actions_python/)
