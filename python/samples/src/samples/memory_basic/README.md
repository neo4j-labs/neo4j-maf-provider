# Neo4j Memory Provider Demo

This sample demonstrates how to use the Neo4j Context Provider for persistent agent memory within the Microsoft Agent Framework.

## Overview

The Neo4j Memory Provider enables agents to:
- **Store conversation memories** after each model invocation
- **Retrieve relevant memories** before each model invocation
- **Scope memories** by user, application, agent, or thread
- **Persist memories** across conversations (new threads)

## How It Works

### Memory Storage (`invoked()` method)

After each model invocation, the provider:
1. Filters messages by configured roles (user, assistant)
2. Creates Memory nodes in Neo4j with text, role, and timestamp
3. Generates embeddings for semantic search (if embedder configured)
4. Attaches scoping metadata (user_id, thread_id, etc.)

### Memory Retrieval (`invoking()` method)

Before each model invocation, the provider:
1. Searches Memory nodes filtered by scoping parameters
2. Uses vector similarity (if embeddings) or recency (timestamp)
3. Formats relevant memories as context for the agent

### Lazy Index Initialization

Indexes are created automatically on first memory operation:
- **Vector index** on `Memory.embedding` (requires Neo4j 5.11+)
- **Fulltext index** on `Memory.text`
- **Scoping indexes** on user_id, thread_id, agent_id, application_id

No setup scripts needed - the provider handles index creation.

## Running the Demo

```bash
# From repository root
uv run start-samples 9
```

Or run directly:
```bash
uv run python -c "import asyncio; from samples.memory_basic import demo_memory_basic; asyncio.run(demo_memory_basic())"
```

## Demo Walkthrough

The demo shows three parts:

### Part 1: User A - First Conversation
Alice shares personal information (loves hiking, favorite trail).

### Part 2: User A - New Conversation
A new conversation starts with the same user. The agent should recall Alice's hiking preferences from Part 1, demonstrating cross-conversation memory persistence.

### Part 3: User B - Memory Isolation
Bob starts a conversation. The agent should NOT know about Alice's preferences, demonstrating user-scoped memory isolation.

## Configuration

### Required Environment Variables

```
NEO4J_URI=neo4j+s://xxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password
AZURE_AI_PROJECT_ENDPOINT=https://your-project.ai.azure.com/...
```

### Provider Configuration

```python
provider = Neo4jContextProvider(
    # Neo4j connection
    uri=neo4j_settings.uri,
    username=neo4j_settings.username,
    password=neo4j_settings.get_password(),

    # Memory configuration
    memory_enabled=True,
    user_id="user_alice",      # Required: at least one scope filter

    # Index configuration (fulltext for knowledge graph)
    index_name="search_chunks",
    index_type="fulltext",

    # Embedder for semantic memory search
    embedder=embedder,
    top_k=5,
)
```

### Scoping Parameters

At least one scope filter is required when memory is enabled:

| Parameter | Description |
|-----------|-------------|
| `user_id` | Isolate memories by user |
| `thread_id` | Isolate memories by conversation thread |
| `agent_id` | Isolate memories by agent instance |
| `application_id` | Isolate memories by application |

## Memory Node Schema

Each memory is stored as a Neo4j node:

```
(:Memory {
  id: "uuid",
  text: "Message content",
  role: "user|assistant|system",
  timestamp: "2024-01-15T10:30:00Z",
  embedding: [0.1, 0.2, ...],  // Optional, for vector search
  user_id: "user_alice",       // Scoping fields
  thread_id: "...",
  agent_id: "...",
  application_id: "..."
})
```

## Troubleshooting

### "Vector index creation failed"
Ensure you're using Neo4j 5.11 or later for vector index support.

### "Memory requires at least one scope filter"
Enable at least one scoping parameter (`user_id`, `thread_id`, etc.) when `memory_enabled=True`.

### Memories not appearing in new conversations
- Verify you're using the same `user_id` (or other scope filters)
- Check that the embedder is configured for semantic search
- Ensure memories were stored (check Neo4j Browser for Memory nodes)
