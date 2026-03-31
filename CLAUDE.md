# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Guidelines

- When proposing new features, write proposals in plain English only (no code). Keep proposals simple—this is a demo project.
- Use best practices for the respective language (Python: pydantic, type safety; .NET: nullable, async patterns).
- **Always use the latest version of the Microsoft Agent Framework with Microsoft Foundry** for agent-related functionality.

## Project Overview

This is a **dual-language monorepo** containing the Neo4j Context Provider for Microsoft Agent Framework. Context providers are plugins that automatically inject relevant information into an agent's conversation before the AI model processes each message. This provider retrieves data from Neo4j knowledge graphs using vector or fulltext search, with optional graph traversal for rich context.

### Repository Structure

```
neo4j-maf-provider/
├── python/                            # Python implementation
│   ├── packages/agent-framework-neo4j/   # Publishable PyPI library
│   │   └── agent_framework_neo4j/        # Library source code
│   ├── samples/                           # Demo applications
│   │   └── src/samples/                   # Sample modules
│   ├── tests/                             # Library tests
│   └── docs/                              # Python documentation
├── dotnet/                            # .NET implementation
│   ├── src/Neo4j.AgentFramework.GraphRAG/         # NuGet library
│   ├── samples/Neo4j.Samples/            # Demo console app
│   └── tests/Neo4j.AgentFramework.GraphRAG.Tests/ # Unit tests
├── examples/                          # Sample setup and provisioning
│   ├── SETUP.md                          # Setup guide
│   ├── main.bicep                        # Azure Bicep template
│   └── scripts/                          # Setup and seed scripts
├── azure.yaml                         # Azure Developer CLI config
├── .env.sample                        # Environment variable template
├── docs/                              # Shared documentation
├── README.md                          # Project landing page
├── CONTRIBUTING.md                    # Contribution guidelines
└── LICENSE
```

### Key Architecture

- **No entity extraction**: Full message text is passed to the search index, letting Neo4j handle relevance ranking
- **Index-driven configuration**: Works with any Neo4j index—configure `index_name` and `index_type`
- **Configurable graph enrichment**: Custom Cypher queries traverse relationships after initial search

## Commands

### Python

All Python commands should be run from the `python/` directory.

```bash
cd python
uv sync --prerelease=allow     # Install dependencies
uv run start-samples           # Interactive menu
uv run start-samples 3         # Run specific demo (1-8)
uv run pytest                  # Run tests
uv run mypy packages/agent-framework-neo4j/agent_framework_neo4j       # Type check
uv run ruff check packages/agent-framework-neo4j/agent_framework_neo4j # Lint
uv run ruff format packages/agent-framework-neo4j/agent_framework_neo4j # Format
uv build --package agent-framework-neo4j    # Build library
```

### .NET

All .NET commands should be run from the `dotnet/` directory.

```bash
cd dotnet
dotnet build                                    # Build all projects
dotnet test                                     # Run unit tests
dotnet run --project samples/Neo4j.Samples      # Run demos
dotnet pack src/Neo4j.AgentFramework.GraphRAG            # Create NuGet package
```

### Sample Setup (from repo root)

```bash
azd up                                 # Provision Azure AI Foundry
python examples/scripts/setup_env.py   # Sync env vars from azd to .env
python examples/scripts/seed_data.py   # Load demo data into Neo4j
```

## Architecture

### Core Components (Python)

| Component | Location | Purpose |
|-----------|----------|---------|
| `Neo4jContextProvider` | `python/packages/.../agent_framework_neo4j/_provider.py` | `BaseContextProvider` implementation |
| `ProviderConfig` | `python/packages/.../agent_framework_neo4j/_config.py` | Pydantic configuration validation |
| `Neo4jSettings` | `python/packages/.../agent_framework_neo4j/_settings.py` | Pydantic settings for Neo4j credentials |
| `AzureAIEmbedder` | `python/packages/.../agent_framework_neo4j/_embedder.py` | Azure AI embedding integration |
| `FulltextRetriever` | `python/packages/.../agent_framework_neo4j/_fulltext.py` | Fulltext search retriever |

### Core Components (.NET)

| Component | Location | Purpose |
|-----------|----------|---------|
| `Neo4jContextProvider` | `dotnet/src/Neo4j.AgentFramework.GraphRAG/Neo4jContextProvider.cs` | `AIContextProvider` implementation |
| `Neo4jContextProviderOptions` | `dotnet/src/Neo4j.AgentFramework.GraphRAG/Neo4jContextProviderOptions.cs` | Configuration with validation |
| `Neo4jSettings` | `dotnet/src/Neo4j.AgentFramework.GraphRAG/Neo4jSettings.cs` | Environment variable loader |
| `VectorRetriever` | `dotnet/src/Neo4j.AgentFramework.GraphRAG/Retrieval/VectorRetriever.cs` | Vector search via Cypher |
| `FulltextRetriever` | `dotnet/src/Neo4j.AgentFramework.GraphRAG/Retrieval/FulltextRetriever.cs` | Fulltext search via Cypher |
| `HybridRetriever` | `dotnet/src/Neo4j.AgentFramework.GraphRAG/Retrieval/HybridRetriever.cs` | Combined vector + fulltext |

### Search Flow

1. Provider receives invocation context (Python: `before_run()`, .NET: `ProvideAIContextAsync()`)
2. Filter to user/assistant messages with text, take recent N messages
3. Concatenate message text (no entity extraction)
4. Execute search based on `index_type`:
   - **vector**: Embed query → `db.index.vector.queryNodes()`
   - **fulltext**: Optional stop word filtering → `db.index.fulltext.queryNodes()`
   - **hybrid**: Both vector and fulltext search, combined scores
5. If `retrieval_query` provided: Execute custom Cypher for graph traversal
6. Format results and return as context messages

### Samples

Two databases are used in demos:
- **Financial Documents** (samples 1-4): SEC filings with Company, Document, Chunk, RiskFactor, Product nodes
- **Aircraft Domain** (samples 5-8): Maintenance events, components, flights, delays

## Environment Variables

### Neo4j Connection
```
NEO4J_URI                     # neo4j+s://xxx.databases.neo4j.io
NEO4J_USERNAME
NEO4J_PASSWORD
NEO4J_VECTOR_INDEX_NAME       # default: chunkEmbeddings
NEO4J_FULLTEXT_INDEX_NAME     # default: search_chunks
```

### Azure AI Foundry (populated by `python examples/scripts/setup_env.py`)
```
AZURE_AI_PROJECT_ENDPOINT     # Foundry project endpoint (Python)
AZURE_AI_SERVICES_ENDPOINT    # AI Services endpoint (used by .NET and seed_data.py)
AZURE_AI_MODEL_NAME           # Chat model (default: gpt-4o)
AZURE_AI_EMBEDDING_NAME       # Embedding model (default: text-embedding-3-small)
```

## Retrieval Query Requirements
- Must use `node` and `score` variables from index search
- Must return at least `text` and `score` columns
- Use `ORDER BY score DESC` to maintain relevance ranking
