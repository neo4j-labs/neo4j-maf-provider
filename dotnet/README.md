# Neo4j Context Provider for Microsoft Agent Framework (.NET)

> **Status: Planned**
>
> The .NET implementation is planned for future development. See the [Python implementation](../python/README.md) for the currently available version.

## Planned Features

The .NET implementation will provide the same capabilities as the Python version:

| Feature | Description |
|---------|-------------|
| **Vector Search** | Semantic similarity search using embeddings |
| **Fulltext Search** | Keyword matching using BM25 scoring |
| **Hybrid Search** | Combined vector + fulltext for best results |
| **Graph Enrichment** | Traverse relationships after initial search |

## Planned Package

- **NuGet Package**: `Microsoft.Agents.AI.Neo4j` (planned)
- **Target Frameworks**: .NET 8.0+

## Planned Structure

```
dotnet/
├── src/
│   └── Microsoft.Agents.AI.Neo4j/    # Main library
├── samples/                           # Demo applications
├── tests/                             # Test suite
├── Directory.Build.props              # MSBuild properties
├── Directory.Packages.props           # Central package management
└── neo4j-provider.sln                 # Solution file
```

## Contributing

If you're interested in contributing to the .NET implementation, please open an issue to discuss the approach before starting work.

## Reference Implementation

The Python implementation serves as the reference:

- [Python Source](../python/packages/agent-framework-neo4j/)
- [Python API Reference](../python/docs/api_reference.md)
- [Architecture Documentation](../docs/architecture.md)
