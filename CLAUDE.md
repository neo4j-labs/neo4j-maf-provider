# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Guidelines

- When proposing new features, write proposals in plain English only (no code). Keep proposals simple—this is a demo project.
- Use Python best practices and pydantic type safety where possible.
- **Always use the latest version of the Microsoft Agent Framework with Microsoft Foundry** for agent-related functionality. Reference the framework source at `/Users/ryanknight/projects/azure/agent-framework` and samples at `/Users/ryanknight/projects/azure/Agent-Framework-Samples`. See `AGENT_FRAMEWORK.md` for details.

## Project Overview

This is a **dual-language monorepo** containing the Neo4j Context Provider for Microsoft Agent Framework. Context providers are plugins that automatically inject relevant information into an agent's conversation before the AI model processes each message. This provider retrieves data from Neo4j knowledge graphs using vector or fulltext search, with optional graph traversal for rich context.

### Repository Structure

```
neo4j-maf-provider/
├── python/                            # Python implementation
│   ├── packages/agent-framework-neo4j/   # Publishable PyPI library
│   │   └── agent_framework_neo4j/        # Library source code
│   ├── samples/                           # Demo applications (self-contained)
│   │   ├── azure.yaml                     # azd configuration
│   │   ├── infra/                         # Azure Bicep templates
│   │   ├── scripts/                       # Setup scripts
│   │   ├── basic_fulltext/
│   │   ├── vector_search/
│   │   ├── graph_enriched/
│   │   ├── aircraft_domain/
│   │   └── shared/
│   ├── tests/                             # Library tests
│   └── docs/                              # Python documentation
├── dotnet/                            # .NET implementation (planned)
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

All Python commands should be run from the `python/` directory.

### Setup
```bash
cd python
uv sync --prerelease=allow     # Install dependencies (pre-release required for Agent Framework)

# Provision Azure infrastructure (from samples directory)
cd samples
azd up                         # Provision Microsoft Foundry
uv run setup_env.py            # Pull env vars from azd into .env
```

### Run Demos
```bash
cd python
uv run start-samples           # Interactive menu
uv run start-samples 3         # Run specific demo (1-7)
uv run start-samples a         # Run all demos
```

### Development
```bash
cd python
uv run pytest                  # Run tests
uv run mypy packages/agent-framework-neo4j/agent_framework_neo4j       # Type check
uv run ruff check packages/agent-framework-neo4j/agent_framework_neo4j # Lint
uv run ruff format packages/agent-framework-neo4j/agent_framework_neo4j # Format
```

### Build and Publish
```bash
cd python
uv build --package agent-framework-neo4j    # Build library
uv publish --package agent-framework-neo4j  # Publish to PyPI
```

## Architecture

### Core Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `Neo4jContextProvider` | `python/packages/.../agent_framework_neo4j/_provider.py` | Main context provider implementing `ContextProvider` interface |
| `ProviderConfig` | `python/packages/.../agent_framework_neo4j/_config.py` | Pydantic configuration validation |
| `Neo4jSettings` | `python/packages/.../agent_framework_neo4j/_settings.py` | Pydantic settings for Neo4j credentials |
| `AzureAISettings` | `python/packages/.../agent_framework_neo4j/_settings.py` | Pydantic settings for Azure AI |
| `AzureAIEmbedder` | `python/packages/.../agent_framework_neo4j/_embedder.py` | Azure AI embedding integration |
| `FulltextRetriever` | `python/packages/.../agent_framework_neo4j/_fulltext.py` | Fulltext search retriever |

### Search Flow

1. **invoking()** called → Provider receives conversation messages
2. Filter to USER/ASSISTANT messages, take recent N messages
3. Concatenate message text (no entity extraction)
4. Execute search based on `index_type`:
   - **vector**: Embed query → `db.index.vector.queryNodes()`
   - **fulltext**: Optional stop word filtering → `db.index.fulltext.queryNodes()`
   - **hybrid**: Both vector and fulltext search, combined scores
5. If `retrieval_query` provided: Execute custom Cypher for graph traversal
6. Format results → Return `Context(messages=[...])`

### Samples

Two databases are used in demos:
- **Financial Documents** (samples 1-4): SEC filings with Company, Document, Chunk, RiskFactor, Product nodes
- **Aircraft Domain** (samples 5-7): Maintenance events, components, flights, delays

## Environment Variables

### Neo4j Connection
```
NEO4J_URI                     # neo4j+s://xxx.databases.neo4j.io
NEO4J_USERNAME
NEO4J_PASSWORD
NEO4J_VECTOR_INDEX_NAME       # default: chunkEmbeddings
NEO4J_FULLTEXT_INDEX_NAME     # default: search_chunks
```

### Azure/Microsoft Foundry (populated by setup_env.py)
```
AZURE_AI_PROJECT_ENDPOINT     # Microsoft Foundry project endpoint
AZURE_AI_MODEL_NAME           # Chat model (default: gpt-4o)
AZURE_AI_EMBEDDING_NAME       # Embedding model (default: text-embedding-ada-002)
```

## Key Patterns

### Creating a Context Provider
```python
from agent_framework_neo4j import Neo4jContextProvider, Neo4jSettings

settings = Neo4jSettings()  # Loads from environment

provider = Neo4jContextProvider(
    uri=settings.uri,
    username=settings.username,
    password=settings.get_password(),
    index_name="chunkEmbeddings",
    index_type="vector",  # or "fulltext" or "hybrid"
    embedder=my_embedder,
    top_k=5,
    # Optional: graph enrichment via custom Cypher
    retrieval_query="""
        MATCH (node)-[:FROM_DOCUMENT]->(doc)
        RETURN node.text AS text, score, doc.title AS title
        ORDER BY score DESC
    """,
)

async with provider:
    # Use with agent
```

### Retrieval Query Requirements
- Must use `node` and `score` variables from index search
- Must return at least `text` and `score` columns
- Use `ORDER BY score DESC` to maintain relevance ranking

## Module Structure

### Library (`python/packages/agent-framework-neo4j/`)

Public API exported from `agent_framework_neo4j`:
- `Neo4jContextProvider` - Main context provider class
- `Neo4jSettings` - Neo4j connection settings
- `AzureAISettings` - Azure AI settings
- `AzureAIEmbedder` - Embedding generator
- `FulltextRetriever` - Fulltext search retriever

### Samples (`python/samples/`)

- `basic_fulltext/` - Fulltext search demos
- `vector_search/` - Vector similarity search demos
- `graph_enriched/` - Graph traversal enrichment demos
- `aircraft_domain/` - Domain-specific aircraft demos
- `shared/` - Shared utilities (agent config, logging, CLI)
