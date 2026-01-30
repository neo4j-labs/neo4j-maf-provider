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
| `thread_created` | New conversation thread | Capture per-operation thread ID for memory scoping |
| `invoking` | Before each LLM call | Search knowledge graph and memories, return context |
| `invoked` | After each LLM response | Store conversation messages as Memory nodes |
| `__aexit__` | Provider exits context | Close Neo4j connection |

## Key Design Principles

1. **No Entity Extraction** - Full message text is passed to the search index, letting Neo4j handle relevance ranking. This matches how Azure AI Search and Redis providers work in the Microsoft Agent Framework.

2. **Index-Driven Configuration** - Works with any Neo4j index; configure `index_name` and `index_type`. The provider doesn't assume a specific schema.

3. **Configurable Graph Enrichment** - Custom Cypher queries traverse relationships after initial search. Users define their own `retrieval_query` to control what context is returned.

4. **Multi-Tenant Memory Scoping** - Memory storage and retrieval uses scoping filters (user_id, agent_id, thread_id, application_id) following Mem0Provider and RedisProvider patterns from Microsoft Agent Framework.

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
| `MemoryManager` | `_memory.py` | Handles memory storage and retrieval operations |
| `ScopeFilter` | `_memory.py` | Dataclass for memory scoping parameters |
| `Neo4jSettings` | `_settings.py` | Environment-based settings with Pydantic |
| `AzureAISettings` | `_settings.py` | Azure AI embeddings configuration |
| `AzureAIEmbedder` | `_embedder.py` | neo4j-graphrag compatible embedder for Azure AI |
| `FulltextRetriever` | `_fulltext.py` | Custom fulltext search retriever |

**Memory-related methods in `Neo4jContextProvider`:**

| Method | Purpose |
|--------|---------|
| `invoked()` | Store conversation messages via `MemoryManager` |
| `_search_memories()` | Query Memory nodes via `MemoryManager` |
| `_get_scope_filter()` | Build `ScopeFilter` from provider state |
| `_effective_thread_id` | Resolve active thread ID (property) |
| `_validate_per_operation_thread_id()` | Prevent cross-thread conflicts |

**Methods in `MemoryManager`:**

| Method | Purpose |
|--------|---------|
| `ensure_indexes()` | Create memory indexes (lazy initialization) |
| `store()` | Create Memory nodes with metadata and embeddings |
| `search()` | Query Memory nodes with scoping filters |

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

## Agent Memory

The provider supports storing and retrieving conversation memories, enabling agents to recall information from past interactions.

### Memory Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           Memory Lifecycle                                    │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                        BEFORE Model Invocation                          │ │
│  │                                                                         │ │
│  │  invoking(messages) ─────────────────────────────────────────────────►  │ │
│  │       │                                                                 │ │
│  │       ├──► Search Knowledge Graph (existing retriever)                  │ │
│  │       │         ↓                                                       │ │
│  │       │    Return document/chunk context                                │ │
│  │       │                                                                 │ │
│  │       └──► Search Memory Nodes (if memory_enabled)                      │ │
│  │                 ↓                                                       │ │
│  │            Filter by scoping parameters                                 │ │
│  │                 ↓                                                       │ │
│  │            Return relevant past conversations                           │ │
│  │                                                                         │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                        AFTER Model Invocation                           │ │
│  │                                                                         │ │
│  │  invoked(request_messages, response_messages) ───────────────────────►  │ │
│  │       │                                                                 │ │
│  │       ├──► Filter to configured roles (user, assistant, system)         │ │
│  │       │                                                                 │ │
│  │       ├──► Generate embeddings (if embedder configured)                 │ │
│  │       │                                                                 │ │
│  │       └──► Store as Memory nodes with:                                  │ │
│  │                • id (UUID)                                              │ │
│  │                • text (message content)                                 │ │
│  │                • role (user/assistant/system)                           │ │
│  │                • timestamp (ISO format UTC)                             │ │
│  │                • embedding (optional, for vector search)                │ │
│  │                • Scoping: application_id, agent_id, user_id, thread_id  │ │
│  │                                                                         │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Memory Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `memory_enabled` | bool | `False` | Enable memory storage and retrieval |
| `memory_label` | str | `"Memory"` | Node label for stored memories |
| `memory_roles` | tuple | `("user", "assistant")` | Which message roles to store |

### Scoping Parameters

Following the patterns established by Mem0Provider and RedisProvider in Microsoft Agent Framework:

| Parameter | Description |
|-----------|-------------|
| `application_id` | Scope memories to a specific application |
| `agent_id` | Scope memories to a specific agent |
| `user_id` | Scope memories to a specific user |
| `thread_id` | Scope memories to a specific conversation thread |
| `scope_to_per_operation_thread_id` | Use per-operation thread ID instead of configured thread_id |

**Validation:** When `memory_enabled=True`, at least one scope filter must be provided to prevent unbounded memory operations.

### Memory Node Schema

```cypher
(:Memory {
    id: "uuid-string",
    text: "message content",
    role: "user" | "assistant" | "system",
    timestamp: "2024-01-15T10:30:00Z",
    embedding: [float array],  // Optional, for vector search
    application_id: "app-id",
    agent_id: "agent-id",
    user_id: "user-id",
    thread_id: "thread-id",
    message_id: "original-message-id",  // Optional
    author_name: "author"  // Optional
})
```

### Memory Retrieval

When `memory_enabled=True`, the `invoking()` method performs two searches:

1. **Knowledge Graph Search** - Uses the configured retriever (vector/fulltext/hybrid) to search document chunks
2. **Memory Search** - Queries Memory nodes filtered by scoping parameters

Memory search uses:
- **Vector similarity** if an embedder is configured (cosine similarity on embeddings)
- **Recency** if no embedder (ordered by timestamp DESC)

### Thread ID Handling

The provider supports two threading modes (following Mem0/Redis patterns):

**Static Thread ID:**
```python
provider = Neo4jContextProvider(
    thread_id="conversation-123",  # Fixed thread ID
    ...
)
```

**Per-Operation Thread ID:**
```python
provider = Neo4jContextProvider(
    scope_to_per_operation_thread_id=True,  # Use agent-provided thread ID
    ...
)
# Thread ID captured from thread_created() callback
```

When `scope_to_per_operation_thread_id=True`:
- The provider captures the thread ID from the first `thread_created()` call
- Subsequent calls with different thread IDs raise `ValueError`
- This prevents cross-thread data leakage

### Best Practices Implemented

The memory implementation follows patterns from Microsoft Agent Framework's reference providers:

1. **From Mem0Provider** (`agent_framework_mem0/_provider.py`):
   - Scoping with user_id, agent_id, application_id, thread_id
   - Per-operation thread ID scoping option
   - Filter validation before operations
   - Combining request and response messages in `invoked()`

2. **From RedisProvider** (`agent_framework_redis/_provider.py`):
   - `_effective_thread_id` property for thread resolution
   - `_validate_per_operation_thread_id()` for conflict detection
   - Batch storage with metadata fields
   - Hybrid search support (text + vector)

3. **Additional Neo4j-specific patterns**:
   - UNWIND for efficient batch node creation
   - Parameterized Cypher to prevent injection
   - Graph-native storage enabling future relationship traversal

### Reference Implementation Files

For understanding memory patterns in Microsoft Agent Framework:

| File | Purpose |
|------|---------|
| `agent_framework/_memory.py` | `Context` and `ContextProvider` base classes |
| `agent_framework/_threads.py` | `ChatMessageStoreProtocol` for persistence |
| `agent_framework/_agents.py` | How context providers integrate with agents |
| `agent_framework_mem0/_provider.py` | Mem0 memory implementation |
| `agent_framework_redis/_provider.py` | Redis memory with hybrid search |

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

### Hierarchical Memory 

The current memory implementation  provides basic conversation memory. Phase 2 will add hierarchical memory organization:

**Memory Hierarchy:**
1. **Message Level** (Base Layer) - Individual messages (implemented in Phase 1)
2. **Conversation Level** - Summaries of conversation segments
3. **Topic Level** - Extracted facts and entities with relationships
4. **User Profile Level** - Long-term preferences and patterns

**Planned Features:**
- `ConversationSummary` nodes linked to underlying messages
- `Fact` and `Preference` nodes extracted from conversations
- `UserProfile` nodes with aggregated user information
- Graph relationships: `PART_OF`, `SUMMARIZES`, `EXTRACTED_FROM`, `HAS_PREFERENCE`
- Hierarchy traversal in retrieval queries
- Memory consolidation (merge old messages into summaries)


### Additional Retrievers

The neo4j-graphrag library supports additional retrievers:
- `Text2CypherRetriever` - Natural language to Cypher generation
- Custom retrievers for specific use cases

### Memory Index Management

Future enhancements for memory storage:
- Automatic vector index creation for Memory nodes
- Fulltext index for keyword-based memory search
- Time-based memory cleanup and archival
