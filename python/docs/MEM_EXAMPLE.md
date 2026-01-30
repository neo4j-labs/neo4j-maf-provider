# Proposal: Neo4j Agent Memory Example

This proposal outlines adding a new example demonstrating how to use the Neo4j Context Provider for agent memory within the Microsoft Agent Framework.

## Implementation Status

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1A | **Complete** | Provider changes to support memory storage and retrieval |
| Phase 1B | **Complete** | Provider index management and sample application |
| Phase 2 | Pending | Hierarchical memory with graph relationships |

## Background

The Microsoft Agent Framework provides a `ContextProvider` interface with two key lifecycle methods:
- **invoking()**: Called before each model invocation to retrieve and inject relevant context
- **invoked()**: Called after each model invocation to store or extract information from the conversation

Existing memory implementations (Mem0Provider, RedisProvider) demonstrate patterns for storing conversation history and retrieving relevant memories using search. The Neo4j Context Provider already supports vector and fulltext search with optional graph enrichment, making it well-suited for memory use cases—especially those requiring relationship-aware retrieval.

## Microsoft Agent Framework References

The following files in the Microsoft Agent Framework provide essential background for understanding and implementing memory functionality:

### Core Memory Interface
- `/Users/ryanknight/projects/azure/agent-framework/python/packages/core/agent_framework/_memory.py` - Defines the `Context` class and `ContextProvider` abstract base class with `invoking()` and `invoked()` methods
- `/Users/ryanknight/projects/azure/agent-framework/python/packages/core/agent_framework/_threads.py` - Defines `ChatMessageStoreProtocol` for persistent conversation storage

### Agent Integration
- `/Users/ryanknight/projects/azure/agent-framework/python/packages/core/agent_framework/_agents.py` - Shows how context providers are called during agent execution (see `_prepare_thread_and_messages` method around line 1237)

### Memory Provider Implementations
- `/Users/ryanknight/projects/azure/agent-framework/python/packages/mem0/agent_framework_mem0/_provider.py` - Mem0 memory provider implementation showing `invoking()` for search and `invoked()` for storage
- `/Users/ryanknight/projects/azure/agent-framework/python/packages/redis/agent_framework_redis/_provider.py` - Redis memory provider with hybrid text and vector search
- `/Users/ryanknight/projects/azure/agent-framework/python/packages/redis/agent_framework_redis/_chat_message_store.py` - Redis-based conversation history storage

### Sample Implementations
- `/Users/ryanknight/projects/azure/agent-framework/python/samples/getting_started/context_providers/simple_context_provider.py` - Simple example showing user info extraction using LLM
- `/Users/ryanknight/projects/azure/agent-framework/python/samples/getting_started/context_providers/aggregate_context_provider.py` - Combining multiple providers
- `/Users/ryanknight/projects/azure/agent-framework/python/samples/getting_started/context_providers/mem0/mem0_basic.py` - Mem0 usage example
- `/Users/ryanknight/projects/azure/agent-framework/python/samples/getting_started/context_providers/redis/redis_basics.py` - Redis memory usage example
- `/Users/ryanknight/projects/azure/agent-framework/python/samples/getting_started/agents/azure_ai/azure_ai_with_memory_search.py` - Azure AI built-in memory search

## Best Practices Implemented

The memory implementation follows patterns from the Microsoft Agent Framework reference providers:

### From Mem0Provider
- **Scoping parameters**: user_id, agent_id, application_id, thread_id for multi-tenancy
- **Per-operation thread ID**: Option to use agent-provided thread ID via `scope_to_per_operation_thread_id`
- **Filter validation**: Require at least one scope filter when memory is enabled to prevent unbounded operations
- **Message combination**: Combine request and response messages in `invoked()` before storage
- **Role filtering**: Only store messages with valid roles (user, assistant, system)

### From RedisProvider
- **`_effective_thread_id` property**: Resolve which thread ID to use based on scoping mode
- **`_validate_per_operation_thread_id()` method**: Prevent cross-thread data leakage when scoped
- **Batch storage**: Store multiple messages efficiently in a single operation
- **Metadata fields**: Include message_id, author_name, and other metadata when available
- **Hybrid search support**: Use vector similarity when embedder available, fall back to recency

### Neo4j-Specific Additions
- **UNWIND for batch creation**: Efficient Cypher pattern for creating multiple nodes
- **Parameterized queries**: All user data passed as parameters to prevent injection
- **Graph-native storage**: Memory nodes can be extended with relationships in Phase 2

## Proposed Example Structure

The example is organized in two phases, with Phase 1 split into provider changes and sample application:

---

## Phase 1A: Provider Changes (COMPLETE)

**Goal**: Add memory storage and retrieval capabilities to the Neo4j Context Provider.

**What Was Implemented**:

The provider now supports storing conversation messages as Memory nodes in Neo4j and retrieving relevant past messages during context generation. This mirrors how Mem0Provider and RedisProvider work but uses Neo4j as the storage backend.

**How It Works**:
1. When `memory_enabled=True`, the provider activates memory functionality
2. After each model invocation (`invoked()` method), messages are filtered by role and stored as Memory nodes
3. Each Memory node includes: id, text, role, timestamp, and scoping metadata
4. If an embedder is configured, embeddings are generated and stored for vector search
5. Before each model invocation (`invoking()` method), the provider searches for relevant memories
6. Memory search uses vector similarity (if embeddings available) or recency (timestamp order)
7. Retrieved memories are formatted and included in the context alongside knowledge graph results

**New Configuration Parameters**:
- `memory_enabled` (bool, default False): Enable memory storage and retrieval
- `memory_label` (str, default "Memory"): Node label for stored memories
- `memory_roles` (tuple, default ("user", "assistant")): Which message roles to store
- `application_id` (str): Scope memories to a specific application
- `agent_id` (str): Scope memories to a specific agent
- `user_id` (str): Scope memories to a specific user
- `thread_id` (str): Scope memories to a specific conversation thread
- `scope_to_per_operation_thread_id` (bool): Use per-operation thread ID for scoping

**New Methods Added**:
- `invoked()`: Stores conversation messages as Memory nodes after each model invocation
- `_store_memories()`: Creates Memory nodes with metadata and optional embeddings
- `_search_memories()`: Queries Memory nodes filtered by scoping parameters
- `_build_scope_filter_cypher()`: Generates WHERE clause for scoping filters
- `_effective_thread_id` (property): Resolves active thread ID based on scoping mode
- `_validate_per_operation_thread_id()`: Validates thread ID conflicts when scoped

### Phase 1A Checklist

#### Provider Changes
- [x] Implement `invoked()` method in `Neo4jContextProvider`
- [x] Add message storage logic to write `Memory` nodes after each invocation
- [x] Add scoping parameters (user_id, thread_id, agent_id, application_id) to provider configuration
- [x] Add configuration for which message roles to store (user, assistant, or both)
- [x] Add optional embedding generation for stored messages (for vector indexing)
- [x] Add timestamp field to stored memories
- [x] Update `invoking()` to search and include memories in context
- [x] Add scoping filters to memory retrieval
- [x] Add `_effective_thread_id` property following RedisProvider pattern
- [x] Add `_validate_per_operation_thread_id()` following Mem0/Redis pattern
- [x] Add validation requiring at least one scope filter when memory enabled

#### Testing
- [x] Test memory configuration options
- [x] Test scoping parameter validation
- [x] Test thread ID handling and conflicts
- [x] Test invoked() does nothing when memory disabled
- [x] Test invoked() does nothing when not connected
- [x] Test scope filter Cypher generation

#### Documentation
- [x] Update docs/architecture.md with memory implementation details
- [x] Document best practices from reference implementations
- [x] Add memory lifecycle diagram

---

## Phase 1B: Provider Index Management and Sample Application (PENDING)

**Goal**: Add lazy index initialization to the provider (following RedisProvider pattern) and create a working sample that demonstrates basic memory in action.

**What This Phase Covers**:

This phase adds automatic index creation to the provider so users don't need to run separate setup scripts. Following the pattern established by RedisProvider and other Microsoft Agent Framework context providers, the provider will create necessary indexes on first use. This phase also creates a runnable demo showing memories being stored and retrieved across conversations.

### How Database Setup Works (Lazy Initialization Pattern)

Following the best practice from Microsoft Agent Framework providers (RedisProvider, Mem0Provider, AzureAISearchContextProvider), the Neo4j provider handles index creation automatically. Users do not need to run setup scripts or manually create indexes.

**The Pattern**:

When the user first stores a memory, the provider automatically creates the necessary indexes if they don't exist. This is called "lazy initialization" because setup happens on-demand rather than requiring an explicit setup step.

**How It Works**:

1. User creates a provider with `memory_enabled=True`
2. On the first call to `invoked()` (when storing memories), the provider calls `_ensure_memory_indexes()`
3. This method checks if each required index exists
4. If an index doesn't exist, it creates it using `CREATE ... IF NOT EXISTS` Cypher
5. A flag (`_memory_indexes_initialized`) tracks whether this check has been done
6. Subsequent calls skip the index check for efficiency

**Why This Pattern**:

- **Simple for users**: No setup scripts to run, no manual SQL/Cypher commands
- **Idempotent**: Safe to run multiple times (IF NOT EXISTS prevents errors)
- **Matches framework conventions**: Same pattern used by RedisProvider
- **Graceful handling**: Clear error messages if index creation fails

**Memory Node Schema**:

When the provider stores a memory, it creates a node with this structure:
- `id`: A unique identifier (UUID) for each memory
- `text`: The actual message content
- `role`: Who sent the message (user, assistant, or system)
- `timestamp`: When the memory was stored (ISO format UTC)
- `embedding`: Vector representation of the text (optional, for semantic search)
- `application_id`, `agent_id`, `user_id`, `thread_id`: Scoping fields for multi-tenancy

**Indexes Created Automatically**:

The provider creates these indexes on first memory operation:

1. **Vector Index** (if embedder configured): For semantic search on the embedding property. Requires Neo4j 5.11 or later. Allows finding memories that are conceptually similar even without exact word matches.

2. **Fulltext Index**: For keyword-based search on the text property. Used as fallback when no embedder is configured, or for hybrid search.

3. **Scoping Indexes**: Standard indexes on user_id, thread_id, agent_id, and application_id. These make filtering by scope fast, which is critical for multi-tenant deployments.

**New Provider Parameters**:

- `overwrite_memory_index` (bool, default False): If True, recreate indexes even if they exist. Useful for development or schema changes.
- `memory_vector_index_name` (str, default "memory_embeddings"): Name of the vector index to create/use.
- `memory_fulltext_index_name` (str, default "memory_fulltext"): Name of the fulltext index to create/use.

**Error Handling**:

If index creation fails (e.g., wrong Neo4j version for vector indexes), the provider raises a clear error explaining the issue and potential solutions.

### Phase 1B Checklist

#### Provider Enhancements (Lazy Index Initialization) - COMPLETE
- [x] Add `_ensure_memory_indexes()` method to provider
- [x] Add `_memory_indexes_initialized` flag to track state
- [x] Add `overwrite_memory_index` parameter (default False)
- [x] Add `memory_vector_index_name` parameter (default "memory_embeddings")
- [x] Add `memory_fulltext_index_name` parameter (default "memory_fulltext")
- [x] Implement vector index creation with `CREATE VECTOR INDEX IF NOT EXISTS`
- [x] Implement fulltext index creation with `CREATE FULLTEXT INDEX IF NOT EXISTS`
- [x] Implement scoping indexes creation (user_id, thread_id, agent_id, application_id)
- [x] Use `IF NOT EXISTS` for idempotent index creation
- [x] Call `_ensure_memory_indexes()` from first memory operation in `invoked()`
- [x] Add clear error messages for index creation failures (Neo4j version check)
- [x] Document Neo4j version requirement (5.11+ for vector indexes) in error message

#### Sample Application
- [x] Create `samples/memory_basic/` directory
- [x] Create `demo.py` showing basic memory in action
- [x] Demonstrate memory storage across multiple conversation turns
- [x] Demonstrate memory retrieval providing context from past conversations
- [x] Show scoping in action (user A memories separate from user B)
- [x] Create `README.md` with usage instructions
- [x] Add sample to the start-samples menu in `pyproject.toml`

#### Demo Script Structure

The demo script would:
1. Create a provider with memory enabled and a user_id scope (indexes created automatically on first use)
2. Start an agent with the provider
3. Have a multi-turn conversation where the user shares information
4. Start a new conversation (new thread) with the same user
5. Show that the agent recalls information from the previous conversation
6. Optionally show a different user_id to demonstrate scoping isolation

#### Testing
- [x] Test default memory index names
- [x] Test custom memory index names configuration
- [x] Test `overwrite_memory_index` defaults to False
- [x] Test `overwrite_memory_index` can be enabled
- [x] Test memory indexes not initialized initially
- [x] Test `_ensure_memory_indexes()` raises when not connected
- [x] Test `_ensure_memory_indexes()` skips when already initialized
- [x] Verify memories are stored after each invocation (requires Neo4j connection)
- [x] Verify memories are retrieved based on conversation relevance
- [x] Verify scoping filters work correctly (user A cannot see user B memories)
- [ ] Test with both vector and fulltext search modes

#### Documentation
- [x] Write README for memory_basic sample
- [x] Document that indexes are created automatically
- [x] Document Neo4j version requirements (5.11+ for vector)
- [x] Document optional index configuration parameters
- [x] Add troubleshooting section for common issues

---

## Phase 2: Hierarchical Memory (Long-Term)

**Goal**: Demonstrate multi-level memory organization using Neo4j's graph capabilities for richer, more structured recall.

**Concept**: Build a memory hierarchy where raw messages are organized into higher-level abstractions (conversation summaries, topic clusters, user profiles). Graph relationships connect these layers, enabling traversal-based retrieval that provides both specific details and broader context.

**Memory Hierarchy**:

1. **Message Level** (Base Layer)
   - Individual user and assistant messages
   - Stored as `Memory` nodes with full text and metadata
   - Linked to their parent conversation via relationships

2. **Conversation Level** (Summary Layer)
   - Periodic summaries of conversation segments
   - Created when a conversation reaches a certain length or on explicit triggers
   - Stored as `ConversationSummary` nodes linked to the underlying messages
   - Captures key topics, decisions, and outcomes

3. **Topic Level** (Knowledge Layer)
   - Facts and entities extracted from conversations
   - Stored as domain-specific nodes (e.g., `Fact`, `Preference`, `Entity`)
   - Connected to conversations and other topics via typed relationships
   - Enables cross-conversation knowledge retrieval

4. **User Profile Level** (Aggregate Layer)
   - Long-term user preferences, patterns, and summary information
   - Periodically updated based on accumulated interactions
   - Stored as `UserProfile` nodes with structured attributes
   - Connected to topics and key facts

**Graph Relationships**:
- `(Memory)-[:PART_OF]->(Conversation)`
- `(ConversationSummary)-[:SUMMARIZES]->(Conversation)`
- `(Fact)-[:EXTRACTED_FROM]->(Memory)`
- `(UserProfile)-[:HAS_PREFERENCE]->(Preference)`
- `(Topic)-[:RELATED_TO]->(Topic)`

**How Retrieval Works**:
1. Initial search finds relevant memories at any level using vector or fulltext
2. Graph traversal expands context by following relationships
3. Retrieval query walks up the hierarchy (message → summary → topic) for broader context
4. Retrieval query walks down the hierarchy (topic → messages) for specific examples
5. Results combine immediate relevance with structural context

**What This Enables**:
- Agent accesses both specific memories and general knowledge about the user
- Agent understands how topics relate to each other
- Agent provides consistent responses based on established preferences
- Memory naturally organizes around meaningful structures rather than flat lists
- Old messages can be archived while preserving their summarized knowledge

### Phase 2 Checklist

#### Provider Changes
- [ ] Add summary generation hook to `invoked()` method
- [ ] Add configuration for summary trigger (message count, token count, or explicit)
- [ ] Add fact extraction hook (optional, LLM-based or pattern matching)
- [ ] Add user profile update logic
- [ ] Add hierarchy traversal queries to `invoking()` method
- [ ] Add configurable hierarchy depth setting
- [ ] Add memory consolidation method (merge old messages into summaries)
- [ ] Add memory cleanup/archival method

#### Database Setup
- [ ] Define `Conversation` node schema
- [ ] Define `ConversationSummary` node schema
- [ ] Define `Fact` node schema
- [ ] Define `Preference` node schema
- [ ] Define `UserProfile` node schema
- [ ] Create relationship types (PART_OF, SUMMARIZES, EXTRACTED_FROM, HAS_PREFERENCE, RELATED_TO)
- [ ] Create indexes on new node types for search
- [ ] Write Cypher queries for hierarchy traversal

#### Sample Application
- [ ] Create `samples/memory_hierarchical/` directory
- [ ] Write demo script showing hierarchical memory in action
- [ ] Write README with setup and usage instructions
- [ ] Add sample to the start-samples menu
- [ ] Create visualization showing memory graph structure

#### Testing
- [ ] Verify conversation summaries are generated at configured thresholds
- [ ] Verify facts are extracted and linked correctly
- [ ] Verify user profile updates based on accumulated data
- [ ] Verify hierarchy traversal returns appropriate context depth
- [ ] Verify memory consolidation preserves important information
- [ ] Test graph structure in Neo4j Browser

#### Documentation
- [ ] Document hierarchical memory configuration options
- [ ] Document summary generation settings
- [ ] Document fact extraction options
- [ ] Add architecture diagram showing memory hierarchy
- [ ] Update main README with hierarchical memory example

---

## Example Organization

The examples would be added to the `samples/` directory:

```
samples/
├── memory_basic/           # Phase 1B: Basic memory sample
│   ├── demo.py             # Simple memory demonstration
│   └── README.md           # Usage instructions
└── memory_hierarchical/    # Phase 2: Hierarchical memory sample
    ├── demo.py             # Graph-based memory demonstration
    └── README.md           # Usage instructions
```

Note: No separate setup scripts are needed. The provider creates indexes automatically on first use (lazy initialization pattern).

## Database Schema

### Phase 1 Schema

**Nodes**:
- `Memory` - Individual stored messages with text, role, timestamp, embeddings, and scoping fields

**Indexes** (created automatically by provider on first use):
- Vector index on `Memory.embedding` for semantic search (requires Neo4j 5.11+)
- Fulltext index on `Memory.text` for keyword search
- Standard indexes on `Memory.user_id`, `Memory.thread_id`, `Memory.agent_id`, `Memory.application_id` for efficient filtering

The provider creates these indexes automatically via the `_ensure_memory_indexes()` method, following the lazy initialization pattern used by RedisProvider and other Microsoft Agent Framework context providers.

### Phase 2 Schema (Additions)

**Nodes**:
- `Conversation` - Groups of related messages
- `ConversationSummary` - Summaries of conversation segments
- `Fact` - Extracted factual information
- `Preference` - User preferences
- `UserProfile` - Aggregate user information

**Relationships**:
- `PART_OF` - Message belongs to conversation
- `SUMMARIZES` - Summary covers a conversation
- `EXTRACTED_FROM` - Fact came from a message
- `HAS_PREFERENCE` - User has a preference
- `RELATED_TO` - Topics or facts relate to each other

## Success Criteria

**Phase 1A** (Complete):
- Provider stores messages as Memory nodes after each invocation
- Provider retrieves relevant memories during context generation
- Memory is properly scoped by user/thread/agent/application
- Implementation follows Mem0/Redis best practices

**Phase 1B**:
- Database setup script creates necessary indexes
- Demo shows memories persisting across conversations
- Demo shows scoping isolation between users
- Example is straightforward to understand and adapt

**Phase 2**:
- Agent accesses appropriate level of detail based on query
- Graph traversal enriches context with related information
- Summaries reduce token usage while preserving key information
- Memory hierarchy is visible and understandable in Neo4j browser

## Dependencies

- Existing Neo4j Context Provider infrastructure
- Neo4j database version 5.11+ (for vector index support)
- Azure AI embeddings (for vector-based memory)
- Optional: LLM access for summary/fact extraction in Phase 2

## Open Questions

1. How should summary generation be triggered (token count, message count, explicit call)?
2. What fact extraction approach works best for general use cases?
3. How should memory retention and cleanup be handled?
4. Should the hierarchical memory support custom schema extensions for domain-specific use cases?
