# API Alignment: Migrate to Microsoft Agent Framework Preferred Patterns

The Microsoft Agent Framework has renamed core classes and changed the preferred agent construction pattern. Both Neo4j projects and the documentation PRs need to be updated to align.

## Summary of API Changes

| Old (current in both projects) | New (preferred) |
|-------------------------------|-----------------|
| `from agent_framework import ChatAgent` | `from agent_framework import Agent` |
| `from agent_framework import ChatMessage` | `from agent_framework import Message` |
| `ChatAgent(chat_client=..., ...)` | `client.as_agent(...)` or `Agent(client=..., ...)` |
| `context_providers=provider` | `context_providers=[provider]` (must be a list) |

Source: `agent-framework/python/samples/AGENTS.md`

---

## Project 1: neo4j-maf-provider (`agent-framework-neo4j`)

**Repo:** `/Users/ryanknight/projects/azure/neo4j-maf-provider`

### Library code (`python/packages/agent-framework-neo4j/`)

#### `agent_framework_neo4j/_provider.py`

- **Line 16:** `from agent_framework import ChatMessage, Context, ContextProvider, Role`
  - Change to: `from agent_framework import Message, Context, ContextProvider, Role`
- **All references to `ChatMessage`** in the file (type hints, instantiation in `invoking()`)
  - Change to: `Message`
- Verify `ContextProvider` base class name hasn't changed (it may now be `BaseContextProvider` — check `agent_framework` exports)

### Samples (`python/samples/`)

#### All sample files (`basic_fulltext/main.py`, `vector_search/main.py`, `graph_enriched/main.py`, etc.)

- References to `ChatAgent` in docstrings and print statements → `Agent`
- `samples/shared/agent.py` line 86: docstring mentions `ChatAgent` → `Agent`
- `samples/README.md` lines 136, 158: mentions `ChatAgent` → `Agent`

### Tests (`python/tests/`)

#### `test_provider.py`

- **Line 8:** `from agent_framework import ChatMessage, Role`
  - Change to: `from agent_framework import Message, Role`
- All `ChatMessage(...)` instantiations → `Message(...)`

### Documentation (`python/docs/`)

#### `docs/reference/NEO4J_PROVIDER_ARCHITECTURE.md`

- Line 39: sequence diagram participant `ChatAgent` → `Agent`

---

## Project 2: agent-memory (`neo4j-agent-memory`)

**Repo:** `/Users/ryanknight/projects/neo4j-labs/agent-memory`

### Integration module (`src/neo4j_agent_memory/integrations/microsoft_agent/`)

#### `__init__.py`

- **Line 21:** `from agent_framework import ChatAgent` → `from agent_framework import Agent`
- **Lines 37-42:** Example code uses `ChatAgent(chat_client=...)` → `Agent(client=...)` or `client.as_agent(...)`
- **Line 52:** `MICROSOFT_AGENT_FRAMEWORK_VERSION` — update to current version

#### `context_provider.py`

- **Line 29:** `from agent_framework import Context, ContextProvider` — verify `ContextProvider` is still the correct base class name
- **Lines 47-65:** Docstring example uses `ChatAgent(chat_client=...)` → update to new pattern
- **Line 334 (invoking method):** Uses `ChatMessage` for type hints → `Message`
- All `ChatMessage(...)` instantiations → `Message(...)`

#### `memory.py`

- **Line 24:** `from agent_framework import ChatMessage` → `from agent_framework import Message`
- **Lines 45-59:** Docstring example uses `ChatAgent(chat_client=...)` → update
- **Line 180:** Property docstring says "for use with ChatAgent" → "for use with Agent"
- **Line 258:** Return type `list[ChatMessage]` → `list[Message]`

#### `chat_store.py`

- **Line 24:** `from agent_framework import ChatMessage` → `from agent_framework import Message`
- **Lines 42-57:** Docstring example uses `ChatAgent` → `Agent`
- All `ChatMessage(...)` instantiations → `Message(...)`

#### `tools.py`

- **Lines 51-55:** Docstring example uses `ChatAgent(chat_client=...)` → update
- **Line 52:** Comment `# Use with ChatAgent` → `# Use with Agent`

#### `tracing.py`

- **Line 21:** `from agent_framework import ChatMessage` → `from agent_framework import Message`

### Examples (`examples/microsoft_agent_retail_assistant/`)

#### `backend/agent.py`

- **Line 15:** `from agent_framework import ChatAgent, ChatMessage` → `from agent_framework import Agent, Message`
- **Line 411:** `agent = ChatAgent(...)` → use `client.as_agent(...)` or `Agent(client=...)`
- **Line 445-446:** `ChatMessage(role="user", text=message)` → `Message(role="user", text=message)`

---

## Project 3: Documentation PRs

### agent-framework PR #4010 (`neo4j_rag/README.md`, `neo4j_memory/README.md`)

Both READMEs need code snippet updates:

#### `neo4j_rag/README.md` — Code Example section

**Current:**
```python
from agent_framework import ChatAgent
from agent_framework_neo4j import Neo4jContextProvider, Neo4jSettings, AzureAIEmbedder, AzureAISettings

# ... provider setup ...

async with provider:
    agent = ChatAgent(
        chat_client=chat_client,
        instructions="You are a financial analyst assistant.",
        context_providers=provider,
    )
    response = await agent.run("What risks does Acme Corp face?")
```

**Updated:**
```python
import os
from azure.identity import AzureCliCredential
from agent_framework.azure import AzureOpenAIResponsesClient
from agent_framework_neo4j import Neo4jContextProvider, Neo4jSettings, AzureAIEmbedder, AzureAISettings

neo4j_settings = Neo4jSettings()
azure_settings = AzureAISettings()

embedder = AzureAIEmbedder(
    endpoint=azure_settings.inference_endpoint,
    credential=AzureCliCredential(),
    model=azure_settings.embedding_name,
)

provider = Neo4jContextProvider(
    uri=neo4j_settings.uri,
    username=neo4j_settings.username,
    password=neo4j_settings.get_password(),
    index_name="chunkEmbeddings",
    index_type="vector",
    embedder=embedder,
    top_k=5,
    retrieval_query="""
        MATCH (node)-[:FROM_DOCUMENT]->(doc:Document)<-[:FILED]-(company:Company)
        RETURN node.text AS text, score, company.name AS company, doc.title AS title
        ORDER BY score DESC
    """,
)

client = AzureOpenAIResponsesClient(
    project_endpoint=os.environ["AZURE_AI_PROJECT_ENDPOINT"],
    deployment_name=os.environ["AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME"],
    credential=AzureCliCredential(),
)

async with provider:
    agent = client.as_agent(
        instructions="You are a financial analyst assistant.",
        context_providers=[provider],
    )
    response = await agent.run("What risks does Acme Corp face?")
    print(response)
```

#### `neo4j_memory/README.md` — Code Example section

**Current:**
```python
from agent_framework import ChatAgent
from neo4j_agent_memory import MemoryClient, MemorySettings
from neo4j_agent_memory.integrations.microsoft_agent import (
    Neo4jMicrosoftMemory,
    create_memory_tools,
)

settings = MemorySettings(...)
client = MemoryClient(settings)

async with client:
    memory = Neo4jMicrosoftMemory.from_memory_client(
        memory_client=client,
        session_id="user-123",
    )
    tools = create_memory_tools(memory)

    agent = ChatAgent(
        chat_client=chat_client,
        instructions="You are a helpful assistant with persistent memory.",
        tools=tools,
        context_providers=[memory.context_provider],
    )
    response = await agent.run("Remember that I prefer window seats on flights.")
```

**Updated:**
```python
import os
from azure.identity import AzureCliCredential
from agent_framework.azure import AzureOpenAIResponsesClient
from neo4j_agent_memory import MemoryClient, MemorySettings
from neo4j_agent_memory.integrations.microsoft_agent import (
    Neo4jMicrosoftMemory,
    create_memory_tools,
)

settings = MemorySettings(...)
memory_client = MemoryClient(settings)

chat_client = AzureOpenAIResponsesClient(
    project_endpoint=os.environ["AZURE_AI_PROJECT_ENDPOINT"],
    deployment_name=os.environ["AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME"],
    credential=AzureCliCredential(),
)

async with memory_client:
    memory = Neo4jMicrosoftMemory.from_memory_client(
        memory_client=memory_client,
        session_id="user-123",
    )
    tools = create_memory_tools(memory)

    agent = chat_client.as_agent(
        instructions="You are a helpful assistant with persistent memory.",
        tools=tools,
        context_providers=[memory.context_provider],
    )
    response = await agent.run("Remember that I prefer window seats on flights.")
    print(response)
```

### semantic-kernel-docs PR (`agent-rag.md`, `agent-memory.md`)

Same pattern changes apply to the Neo4j sections added to these files. Update `ChatAgent` → `Agent` and show `client.as_agent(...)` pattern with proper client setup.

---

## Execution Order

1. **Update source projects first** (neo4j-maf-provider and agent-memory) so the library code and internal docstrings are aligned
2. **Verify tests pass** after renames — `ChatMessage` → `Message` may require framework version bump in dependencies
3. **Update documentation PRs** (agent-framework #4010 and semantic-kernel-docs) to use the new API in code snippets
4. **Check framework version compatibility** — both projects pin `agent-framework >= 1.0.0b251223`. The `Agent`/`Message` renames may require a newer minimum version. Check which version introduced the renames.

---

## Open Questions

1. **Is `ContextProvider` still the correct base class?** The framework exports `BaseContextProvider` — need to verify if `ContextProvider` is an alias or deprecated.
2. **Is `ChatMessage` still importable as an alias?** If the framework kept backwards-compatible aliases, the rename may not be urgent for library code — but docstrings/examples should still use the new names.
3. **Framework minimum version:** What is the minimum `agent-framework` version that supports `Agent` and `Message`? Both projects' `pyproject.toml` need their dependency pins updated.
