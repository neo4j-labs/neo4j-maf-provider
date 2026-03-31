# Releasing

Maintainer notes for publishing packages from this repo.

## Workflows

- NuGet release workflow: `.github/workflows/release-nuget.yml`
- PyPI release workflow: `.github/workflows/release-pypi.yml`

The release pipelines are intentionally split so publishing one package does not publish the other.

## NuGet

NuGet releases are triggered by pushing a tag with this format:

```bash
dotnet-vX.Y.Z
```

Example:

```bash
git tag dotnet-v1.2.3
git push origin dotnet-v1.2.3
```

What happens:

- GitHub Actions builds and tests the `.NET` solution
- packs `Neo4j.AgentFramework.GraphRAG`
- publishes the package to NuGet
- creates a GitHub release with the generated `.nupkg`

Requirements:

- GitHub environment `nuget`
- repository secret `NUGET_API_KEY`

## PyPI

PyPI releases are triggered by pushing a tag with this format:

```bash
python-vX.Y.Z
```

Example:

```bash
git tag python-v0.5.5
git push origin python-v0.5.5
```

What happens:

- GitHub Actions builds the Python package
- verifies that the tag version matches `python/packages/agent-framework-neo4j/pyproject.toml`
- publishes the package to PyPI
- creates a GitHub release with the generated distributions

Requirements:

- GitHub environment `pypi`
- trusted publishing configured for PyPI

## Notes

- Use `dotnet-v...` only when you want a NuGet release.
- Use `python-v...` only when you want a PyPI release.
- The `.NET` workflow derives the package version from the tag.
- The Python workflow requires the package version to already be updated in `pyproject.toml`.
