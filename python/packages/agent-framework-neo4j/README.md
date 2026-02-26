# agent-framework-neo4j

Neo4j Context Provider for Microsoft Agent Framework - RAG with knowledge graphs.

## Quick Install

```bash
pip install agent-framework-neo4j --pre

# With Azure AI embeddings support
pip install agent-framework-neo4j[azure] --pre
```

## Supported Platforms

- Python 3.10+
- Windows, macOS, Linux

## Setup

Configure Neo4j credentials via environment variables or constructor parameters:

```bash
# Environment variables
export NEO4J_URI="neo4j+s://xxx.databases.neo4j.io"
export NEO4J_USERNAME="neo4j"
export NEO4J_PASSWORD="your-password"
```

## Quick Start

### Basic Fulltext Search

```python
from agent_framework_neo4j import Neo4jContextProvider, Neo4jSettings

settings = Neo4jSettings()  # Loads from environment

provider = Neo4jContextProvider(
    uri=settings.uri,
    username=settings.username,
    password=settings.get_password(),
    index_name="search_chunks",
    index_type="fulltext",
)

async with provider:
    # Use with Microsoft Agent Framework agent
    pass
```

### Vector Search with Azure AI Embeddings

```python
from agent_framework_neo4j import Neo4jContextProvider, AzureAIEmbedder, AzureAISettings
from azure.identity.aio import AzureCliCredential

credential = AzureCliCredential()
ai_settings = AzureAISettings()  # Loads from AZURE_AI_* env vars

embedder = AzureAIEmbedder(
    endpoint=ai_settings.project_endpoint,
    model_name=ai_settings.embedding_model,
    credential=credential,
)

provider = Neo4jContextProvider(
    uri="neo4j+s://xxx.databases.neo4j.io",
    username="neo4j",
    password="your-password",
    index_name="chunkEmbeddings",
    index_type="vector",
    embedder=embedder,
    top_k=5,
)
```

### Hybrid Search (Vector + Fulltext)

```python
provider = Neo4jContextProvider(
    uri=settings.uri,
    username=settings.username,
    password=settings.get_password(),
    index_name="chunkEmbeddings",        # Vector index
    fulltext_index_name="search_chunks", # Fulltext index
    index_type="hybrid",
    embedder=embedder,
)
```

### Graph-Enriched Retrieval

Use custom Cypher queries to traverse relationships after the initial index search:

```python
provider = Neo4jContextProvider(
    uri=settings.uri,
    username=settings.username,
    password=settings.get_password(),
    index_name="chunkEmbeddings",
    index_type="vector",
    embedder=embedder,
    retrieval_query="""
        MATCH (node)-[:FROM_DOCUMENT]->(doc:Document)
        RETURN node.text AS text, score, doc.title AS title
        ORDER BY score DESC
    """,
)
```

**Retrieval query requirements:**
- Must use `node` and `score` variables from the index search
- Must return at least `text` and `score` columns
- Use `ORDER BY score DESC` to maintain relevance ranking

## Features

- **Vector Search** - Semantic similarity using embeddings
- **Fulltext Search** - Keyword matching with Lucene
- **Hybrid Search** - Combined vector + fulltext for best of both
- **Graph Enrichment** - Custom Cypher queries for relationship traversal
- **Message History** - Configurable conversation context windowing
- **Pydantic Settings** - Environment-based configuration with validation

## Configuration Parameters

### Connection

| Parameter | Description |
|-----------|-------------|
| `uri` | Neo4j connection URI |
| `username` | Database username |
| `password` | Database password |

### Search

| Parameter | Default | Description |
|-----------|---------|-------------|
| `index_name` | *required* | Name of the Neo4j index to query |
| `index_type` | `"vector"` | Search type: `"vector"`, `"fulltext"`, or `"hybrid"` |
| `fulltext_index_name` | `None` | Fulltext index name (required for hybrid) |
| `embedder` | `None` | Embedder for vector/hybrid search (required for those types) |
| `top_k` | `5` | Number of results to retrieve |
| `retrieval_query` | `None` | Custom Cypher for graph traversal |
| `message_history_count` | `10` | Recent messages used for search query |
| `filter_stop_words` | `None` | Filter stop words (defaults True for fulltext) |

## Environment Variables

| Variable | Description |
|----------|-------------|
| `NEO4J_URI` | Neo4j connection URI |
| `NEO4J_USERNAME` | Database username |
| `NEO4J_PASSWORD` | Database password |
| `NEO4J_INDEX_NAME` | Default index name |
| `NEO4J_VECTOR_INDEX_NAME` | Vector index name (default: chunkEmbeddings) |
| `NEO4J_FULLTEXT_INDEX_NAME` | Fulltext index name (default: search_chunks) |
| `AZURE_AI_PROJECT_ENDPOINT` | Azure AI project endpoint (for embeddings) |
| `AZURE_AI_EMBEDDING_NAME` | Embedding model name |

## More Examples

See the [samples directory](https://github.com/microsoft/agent-framework/tree/main/python/samples) for complete working examples.

## Documentation

- [Microsoft Agent Framework](https://aka.ms/agent-framework)
- [Agent Framework Python Packages](https://github.com/microsoft/agent-framework/tree/main/python/packages)
- [Neo4j GraphRAG Python](https://neo4j.com/docs/neo4j-graphrag-python/)

## License

MIT
