# Neo4j Context Provider for Microsoft Agent Framework (Python)

A context provider that enables AI agents to retrieve knowledge from Neo4j graph databases.

## Quick Start for Standalone Usage

This is a quick start guide for using the Neo4j Context Provider as a standalone package. For full samples and demos, see the [Running the Samples](#running-the-samples) section below.

### Installation

```bash
# Using pip
pip install agent-framework-neo4j --pre

# Using uv
uv add agent-framework-neo4j --prerelease=allow

# With Azure AI embeddings support
pip install agent-framework-neo4j[azure] --pre
```

### Basic Usage

```python
from agent_framework_neo4j import Neo4jContextProvider, Neo4jSettings

settings = Neo4jSettings()  # Loads from environment

provider = Neo4jContextProvider(
    uri=settings.uri,
    username=settings.username,
    password=settings.get_password(),
    index_name="chunkEmbeddings",
    index_type="vector",
    embedder=my_embedder,
)

async with provider:
    # Use with Microsoft Agent Framework
    pass
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

## Running the Samples

### Prerequisites

1. **Neo4j Database** - Get a free instance at [Neo4j AuraDB](https://neo4j.com/cloud/aura-free/)
2. **Azure Subscription** - For AI Foundry serverless models

### Setup

```bash
# Install dependencies
uv sync --prerelease=allow

# Provision Azure infrastructure (from samples directory)
cd samples
azd up
uv run setup_env.py

# Configure Neo4j in samples/.env
NEO4J_URI=neo4j+s://xxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password
```

### Run Samples

```bash
uv run start-samples      # Interactive menu
uv run start-samples 3    # Run specific demo
```

See [samples/README.md](samples/README.md) for detailed setup instructions.

## Available Samples

### Financial Documents Database

| Sample | Description |
|--------|-------------|
| **Basic Fulltext** | Keyword-based search using BM25 scoring |
| **Vector Search** | Semantic similarity search using Azure AI embeddings |
| **Graph-Enriched** | Vector search with graph traversal for rich context |

### Aircraft Domain Database

| Sample | Description |
|--------|-------------|
| **Maintenance Search** | Search maintenance records with aircraft context |
| **Flight Delays** | Search delay records with route information |
| **Component Health** | Search components with system hierarchy |

## Development

See [DEV_SETUP.md](DEV_SETUP.md) for development environment setup.

### Commands

```bash
# Run tests
uv run pytest

# Type checking
uv run mypy packages/agent-framework-neo4j/agent_framework_neo4j

# Linting
uv run ruff check packages/agent-framework-neo4j/agent_framework_neo4j

# Build
uv build --package agent-framework-neo4j
```

## Documentation

- [API Reference](docs/api_reference.md) - Public API documentation
- [Publishing Guide](docs/PUBLISH.md) - Build and publish to PyPI

## Public API

- `Neo4jContextProvider` - Main context provider class
- `Neo4jSettings` - Pydantic settings for Neo4j connection
- `AzureAISettings` - Pydantic settings for Azure AI
- `AzureAIEmbedder` - Azure AI embedding integration
- `FulltextRetriever` - Fulltext search retriever

## Project Structure

```
python/
├── packages/agent-framework-neo4j/   # Publishable PyPI library
├── samples/                           # Demo applications
├── tests/                             # Library tests
└── docs/                              # Python-specific documentation
```

## License

MIT
