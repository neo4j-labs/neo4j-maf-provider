# Neo4j Context Provider for Microsoft Agent Framework

A context provider that enables AI agents to retrieve knowledge from Neo4j graph databases. Works with the [Microsoft Agent Framework](https://aka.ms/agent-framework).

## What is a Context Provider?

Context providers are an extensibility mechanism in the Microsoft Agent Framework that automatically inject relevant information into an agent's conversation before the AI model processes each message. They solve a fundamental problem: how do you give an AI agent access to your organization's knowledge without manually copy-pasting information into every conversation?

```
User sends message
       |
Agent Framework calls context provider's "invoking" method
       |
Provider searches external data source for relevant information
       |
Provider returns context to the agent
       |
Agent sends message + context to the AI model
       |
AI model responds with knowledge from your data
```

## Features

| Search Type | Description |
|-------------|-------------|
| **Vector** | Semantic similarity search using embeddings |
| **Fulltext** | Keyword matching using BM25 scoring |
| **Hybrid** | Combined vector + fulltext for best results |

| Mode | Description |
|------|-------------|
| **Basic** | Returns search results directly |
| **Graph-Enriched** | Traverses relationships after search for rich context |

## Language Support

| Language | Status | Documentation |
|----------|--------|---------------|
| **Python** | Available | [python/README.md](python/README.md) |
| **.NET** | Planned | Coming soon |


See [python/README.md](python/README.md) for complete documentation.

## Repository Structure

```
neo4j-maf-provider/
├── python/                    # Python implementation
│   ├── packages/              # Publishable PyPI library
│   ├── samples/               # Demo applications
│   ├── tests/                 # Test suite
│   └── docs/                  # Python documentation
├── dotnet/                    # .NET implementation (planned)
├── docs/                      # Shared documentation
├── README.md                  # This file
├── CONTRIBUTING.md            # Contribution guidelines
└── LICENSE                    # MIT license
```

## Documentation

### Shared Documentation

- [Architecture](docs/architecture.md) - Design principles, search flow, components

### Python Documentation

- [Python README](python/README.md) - Quick start and installation
- [Development Setup](python/DEV_SETUP.md) - Development environment
- [API Reference](python/docs/api_reference.md) - Public API
- [Publishing Guide](python/docs/PUBLISH.md) - PyPI publication

## Samples

The Python implementation includes demo applications:

| Category | Samples |
|----------|---------|
| **Financial Documents** | Basic fulltext, vector search, graph-enriched |
| **Aircraft Domain** | Maintenance search, flight delays, component health |

```bash
cd python
uv sync --prerelease=allow
uv run start-samples
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on contributing to this project.

## External Resources

- [Microsoft Agent Framework](https://aka.ms/agent-framework)
- [Agent Framework Python Packages](https://github.com/microsoft/agent-framework/tree/main/python/packages)
- [Neo4j GraphRAG Python](https://neo4j.com/docs/neo4j-graphrag-python/)
- [Neo4j AuraDB](https://neo4j.com/cloud/aura/)

## License

MIT
