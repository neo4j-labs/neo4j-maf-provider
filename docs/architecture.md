# Architecture

## Overview

The Neo4j Context Provider integrates Neo4j knowledge graphs with Microsoft Agent Framework. It retrieves relevant context from Neo4j using vector, fulltext, or hybrid search, optionally enriching results through graph traversal.

## Context Provider Lifecycle

Context providers hook into the agent's request/response flow:

```
User sends message
       ↓
Agent Framework calls provider's "invoking" method
       ↓
Provider searches Neo4j for relevant information
       ↓
Provider returns Context(messages=[...])
       ↓
Agent sends message + context to the AI model
       ↓
AI model responds with knowledge from the graph
```

**Lifecycle methods:**

| Method | When Called | Purpose |
|--------|-------------|---------|
| `__aenter__` | Provider enters context | Connect to Neo4j, create retriever |
| `invoking` | Before each LLM call | Search knowledge graph, return context |
| `__aexit__` | Provider exits context | Close Neo4j connection |

## Key Design Principles

1. **No Entity Extraction** - Full message text is passed to the search index, letting Neo4j handle relevance ranking. This matches how Azure AI Search and Redis providers work in the Microsoft Agent Framework.

2. **Index-Driven Configuration** - Works with any Neo4j index; configure `index_name` and `index_type`. The provider doesn't assume a specific schema.

3. **Configurable Graph Enrichment** - Custom Cypher queries traverse relationships after initial search. Users define their own `retrieval_query` to control what context is returned.

## Search Flow

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         Neo4jContextProvider                                  │
│                                                                               │
│  invoking(messages) ──────────────────────────────────────────────────────►  │
│       │                                                                       │
│       ▼                                                                       │
│  ┌─────────────────┐                                                          │
│  │ Filter Messages │  Keep USER/ASSISTANT roles, take recent N               │
│  └────────┬────────┘                                                          │
│           │                                                                   │
│           ▼                                                                   │
│  ┌─────────────────┐                                                          │
│  │ Concatenate     │  query = "\n".join(msg.text for msg in messages)        │
│  │ Message Text    │  (NO entity extraction)                                 │
│  └────────┬────────┘                                                          │
│           │                                                                   │
│           ▼                                                                   │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                      Index Type Selection                               │  │
│  ├────────────────────┬────────────────────┬──────────────────────────────┤  │
│  │      VECTOR        │     FULLTEXT       │         HYBRID               │  │
│  │                    │                    │                              │  │
│  │  1. Embed query    │  1. Filter stop    │  1. Embed query              │  │
│  │  2. Vector search  │     words          │  2. Vector + Fulltext        │  │
│  │     via index      │  2. BM25 search    │  3. Combine scores           │  │
│  └────────────────────┴────────────────────┴──────────────────────────────┘  │
│           │                                                                   │
│           ▼                                                                   │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                    Graph Enrichment (if retrieval_query set)           │  │
│  │                                                                        │  │
│  │   Execute custom Cypher:                                               │  │
│  │   MATCH (node)-[:FROM_DOCUMENT]-(doc)                                  │  │
│  │   MATCH (doc)-[:FILED]-(company)                                       │  │
│  │   RETURN node.text, score, company.name, ...                           │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│           │                                                                   │
│           ▼                                                                   │
│  ┌─────────────────┐                                                          │
│  │ Format Context  │  Return Context(messages=[ChatMessage(...)])            │
│  └─────────────────┘                                                          │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Components

### Core Library (`packages/agent-framework-neo4j/`)

| Component | File | Purpose |
|-----------|------|---------|
| `Neo4jContextProvider` | `_provider.py` | Main provider implementing `ContextProvider` interface |
| `ProviderConfig` | `_config.py` | Pydantic model for configuration validation |
| `Neo4jSettings` | `_settings.py` | Environment-based settings with Pydantic |
| `AzureAISettings` | `_settings.py` | Azure AI embeddings configuration |
| `AzureAIEmbedder` | `_embedder.py` | neo4j-graphrag compatible embedder for Azure AI |
| `FulltextRetriever` | `_fulltext.py` | Custom fulltext search retriever |

### Integration with neo4j-graphrag

The provider uses the official `neo4j-graphrag` Python library for retrieval. This provides well-tested retrievers that handle vector search, fulltext search, and hybrid search.

**Retriever Selection:**

| index_type | retrieval_query | Retriever Used |
|------------|-----------------|----------------|
| vector | None | `VectorRetriever` |
| vector | Set | `VectorCypherRetriever` |
| hybrid | None | `HybridRetriever` |
| hybrid | Set | `HybridCypherRetriever` |
| fulltext | Any | `FulltextRetriever` (custom) |

### Search Types

| Search Type | Best For | How It Works |
|-------------|----------|--------------|
| **Vector** | Semantic similarity—finds conceptually related content | Embeds query → searches vector index → ranks by cosine similarity |
| **Fulltext** | Keyword matching—finds content with specific terms | Tokenizes query → searches fulltext index → ranks by BM25 |
| **Hybrid** | Best of both—combines semantic and keyword | Runs both searches → combines scores |

## Async Design

neo4j-graphrag retrievers are synchronous. The provider wraps them with `asyncio.to_thread()` for async compatibility:

```python
# Retriever creation (makes DB calls during __init__)
self._retriever = await asyncio.to_thread(self._create_retriever)

# Search execution
result = await asyncio.to_thread(
    self._retriever.search,
    query_text=query_text,
    top_k=self._top_k,
)
```

## Configuration Validation

The provider uses Pydantic for comprehensive validation:

```python
class ProviderConfig(BaseModel):
    # Field validators ensure positive values
    @field_validator("top_k")
    def top_k_must_be_positive(cls, v): ...

    # Model validator checks interdependencies
    @model_validator(mode="after")
    def validate_config(self):
        # Hybrid requires fulltext_index_name
        # Vector/hybrid requires embedder
        ...
```

**Validation rules:**
- `index_type="hybrid"` requires `fulltext_index_name`
- `index_type="vector"` or `"hybrid"` requires `embedder`
- `top_k` and `message_history_count` must be ≥ 1

## The Retrieval Query Pattern

When using graph enrichment, the `retrieval_query` parameter defines how to traverse the graph after the initial search. Requirements:

1. Use `node` variable (the search result node)
2. Use `score` variable (the relevance score)
3. Return at least `text` and `score` columns
4. Use `ORDER BY score DESC` to maintain ranking

**Example:**
```cypher
MATCH (node)-[:FROM_DOCUMENT]->(doc:Document)
MATCH (doc)<-[:FILED]-(company:Company)
OPTIONAL MATCH (company)-[:FACES_RISK]->(risk:RiskFactor)
RETURN
    node.text AS text,
    score,
    company.name AS company,
    collect(DISTINCT risk.name) AS risks
ORDER BY score DESC
```

## Connection Management

The provider uses Python's async context manager pattern:

```python
async with Neo4jContextProvider(...) as provider:
    # Provider connected, retriever ready
    async with ChatAgent(context_providers=provider) as agent:
        # Use agent
# Connection automatically closed
```

**Lifecycle:**
1. `__aenter__`: Create driver → verify connectivity → create retriever
2. Use provider for searches
3. `__aexit__`: Close driver, clean up retriever

## Result Formatting

Search results are formatted into readable context for the LLM:

```
[Score: 0.892] [company: Apple Inc] [risks: Competition, Supply Chain]
The Company's products compete with many other products...
```

The formatter:
1. Extracts score from metadata
2. Formats other metadata fields as `[key: value]`
3. Appends the text content

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NEO4J_URI` | Connection URI | Required |
| `NEO4J_USERNAME` | Database username | Required |
| `NEO4J_PASSWORD` | Database password | Required |
| `NEO4J_INDEX_NAME` | Default index name | None |
| `NEO4J_VECTOR_INDEX_NAME` | Vector index name | `chunkEmbeddings` |
| `NEO4J_FULLTEXT_INDEX_NAME` | Fulltext index name | `search_chunks` |
| `AZURE_AI_PROJECT_ENDPOINT` | Azure AI endpoint | Required for embeddings |
| `AZURE_AI_EMBEDDING_NAME` | Embedding model | `text-embedding-ada-002` |

## Future Work

### Additional Retrievers

The neo4j-graphrag library supports additional retrievers:
- `Text2CypherRetriever` - Natural language to Cypher generation
- Custom retrievers for specific use cases
