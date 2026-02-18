# Proposal: Align Neo4j Context Provider with Agent Framework BaseContextProvider API

## Implementation Status

| Step | Description | Status |
|------|-------------|--------|
| 1 | Update `_provider.py` — core provider class | DONE |
| 2 | Update `__init__.py` — public exports | DONE (no changes needed) |
| 3 | Update `test_provider.py` — tests | DONE |
| 4 | Update sample docstrings/print | DONE |
| 5 | Update documentation (architecture, README, CLAUDE.md) | DONE |
| 6 | Update `pyproject.toml` dependency pin | DONE |
| 7 | Verify (pytest, mypy, ruff) | DONE — all pass |

### Verification Results

```
pytest:  15 passed in 0.50s
mypy:    Success: no issues found in 7 source files
ruff:    All checks passed!
```

### Files Changed

| File | What Changed |
|------|-------------|
| `python/packages/.../agent_framework_neo4j/_provider.py` | `ContextProvider` → `BaseContextProvider`, `invoking()` → `before_run()`, `ChatMessage` → `Message`, added `source_id` param, removed `Context`/`Role`/`MutableSequence`/`override` imports |
| `python/packages/.../pyproject.toml` | `agent-framework-core>=1.0.0b` → `>=1.0.0b260212` |
| `python/tests/test_provider.py` | `ChatMessage`/`Role` → `Message`/`AgentSession`/`SessionContext`, `TestInvoking` → `TestBeforeRun` |
| `python/samples/src/samples/basic_fulltext/main.py` | `ChatAgent` → `Agent` (3 occurrences) |
| `python/samples/src/samples/vector_search/main.py` | `ChatAgent` → `Agent` (2 occurrences) |
| `python/samples/src/samples/shared/agent.py` | `ChatAgent` → `Agent` (1 occurrence) |
| `python/docs/reference/NEO4J_PROVIDER_ARCHITECTURE.md` | Sequence diagram, lifecycle table, architecture diagram, prose updated |
| `python/samples/README.md` | `ChatAgent` → `Agent` (2 occurrences) |
| `CLAUDE.md` | Search flow updated: `invoking()` → `before_run()`, `Context(messages=...)` → `context.extend_messages(...)` |

---

## Key Goal

**No backward compatibility. Upgrade everything to the latest Agent Framework API.**

The old `ContextProvider`, `ChatMessage`, `ChatAgent`, and `invoking()` pattern are removed entirely — no deprecated wrappers, no aliases, no shims. All library code, tests, samples, and documentation will target the current framework version (`1.0.0b260212`) exclusively.

## Background

The Microsoft Agent Framework has undergone a significant API redesign for context providers. The old `ContextProvider` base class (with its `invoking()` hook returning a `Context` object) has been **removed entirely** and replaced with `BaseContextProvider` using a `before_run()`/`after_run()` hooks pattern. The `ChatMessage` class has also been renamed to `Message`.

Our `Neo4jContextProvider` currently extends the old `ContextProvider` and uses `invoking()` — this class no longer exists in the framework. This means our library is broken against the latest framework version and must be updated.

## What Changed in the Agent Framework

### Old API (what we use today)

```python
from agent_framework import ChatMessage, Context, ContextProvider, Role

class Neo4jContextProvider(ContextProvider):
    async def invoking(self, messages: ChatMessage | MutableSequence[ChatMessage], **kwargs) -> Context:
        # ... search Neo4j ...
        return Context(messages=[ChatMessage(role=Role.USER, text="...")])
```

### New API (current framework)

```python
from agent_framework import BaseContextProvider, Message, SessionContext, AgentSession, SupportsAgentRun

class Neo4jContextProvider(BaseContextProvider):
    def __init__(self, *, source_id: str = "neo4j-context", ...):
        super().__init__(source_id)

    async def before_run(self, *, agent: SupportsAgentRun, session: AgentSession, context: SessionContext, state: dict) -> None:
        # ... search Neo4j ...
        context.extend_messages(self.source_id, [Message(role="user", text="...")])
```

### Summary of Breaking Changes

| Aspect | Old (our code) | New (framework) | Source |
|--------|---------------|-----------------|--------|
| Base class | `ContextProvider` | `BaseContextProvider` | `_sessions.py:272` |
| Hook method | `invoking()` returns `Context` | `before_run()` mutates `SessionContext` | `_sessions.py:296-314` |
| Post-processing | _(none)_ | `after_run()` | `_sessions.py:316-334` |
| Message class | `ChatMessage` | `Message` | `_types.py:1403` |
| Role values | `Role.USER` enum | `"user"` string literal | `_types.py:1348` |
| Constructor | No `source_id` required | `source_id: str` required | `_sessions.py:288` |
| Input messages | Passed as `invoking(messages)` arg | Read from `context.input_messages` | `_sessions.py:144` |
| Output | Return `Context(messages=[...])` | Call `context.extend_messages(source_id, [...])` | `_sessions.py:178-209` |
| Lifecycle | `__aenter__`/`__aexit__` | Same (unchanged) | Azure AI Search provider uses this |
| Agent construction | `ChatAgent(chat_client=...)` | `client.as_agent(...)` or `Agent(client=...)` | Framework samples |
| Thread/session | `AgentThread` | `AgentSession` | `_sessions.py:452` |

### Reference Implementation

The `AzureAISearchContextProvider` in the framework is the canonical reference for this pattern:

**File:** `agent-framework/python/packages/azure-ai-search/agent_framework_azure_ai_search/_context_provider.py`

Key patterns from that implementation (lines 134-349):
- Extends `BaseContextProvider` with `source_id` in constructor (line 134, 195)
- Reads messages from `context.input_messages` (line 324)
- Filters to user/assistant messages with text (lines 329-333)
- Writes results via `context.extend_messages(self.source_id, messages)` (line 349)
- Creates `Message(role="user", text=...)` directly (lines 347-348)
- Uses `agent: SupportsAgentRun` type hint (line 318)
- Retains `__aenter__`/`__aexit__` for client lifecycle (lines 298-311)

## Decisions

### 1. `source_id` — optional with default `"neo4j-context"`

The Azure AI Search provider requires `source_id` as a mandatory parameter. For simpler usage, our provider will accept it as optional with a default of `"neo4j-context"`. Users who run multiple Neo4j providers can override it.

### 2. `SupportsAgentRun` type hint — use the protocol

All official framework provider packages (Azure AI Search, Mem0, Redis) use `agent: SupportsAgentRun` in their `before_run()` signatures. This is the Python best practice — it's a `Protocol` class (structural subtyping), so it provides type safety without coupling to a concrete class. Only the framework's internal test helpers use `Any` for brevity.

Source references:
- Azure AI Search: `agent_framework_azure_ai_search/_context_provider.py:318`
- Mem0: `agent_framework_mem0/_context_provider.py:98`
- Redis: `agent_framework_redis/_context_provider.py:120`
- Base class definition: `agent_framework/_sessions.py:299`
- Protocol definition: `agent_framework/_agents.py:169`

### 3. No backward compatibility

Clean break. Remove `invoking()` entirely. No deprecated wrappers. Users must use the latest framework version.

### 4. Pin to latest framework version

Pin dependency to `agent-framework-core>=1.0.0b260212` in `pyproject.toml`. The current pin is `>=1.0.0b` which is too loose.

## Files Requiring Changes

### 1. Library Code

| File | Changes |
|------|---------|
| `python/packages/.../agent_framework_neo4j/_provider.py` | Base class, imports, `invoking()` → `before_run()`, `ChatMessage` → `Message`, `Context` → `SessionContext` |
| `python/packages/.../agent_framework_neo4j/__init__.py` | Update public API exports if any types change |
| `python/packages/.../pyproject.toml` | Update `agent-framework-core` dependency pin |

### 2. Tests

| File | Changes |
|------|---------|
| `python/tests/test_provider.py` | `ChatMessage` → `Message`, update `invoking()` calls to match new `before_run()` signature |

### 3. Samples

| File | Changes |
|------|---------|
| `python/samples/src/samples/basic_fulltext/main.py` | `ChatAgent` → `Agent` in docstrings/print |
| `python/samples/src/samples/vector_search/main.py` | `ChatAgent` → `Agent` in docstrings/print |
| `python/samples/src/samples/shared/agent.py` | `ChatAgent` → `Agent` in docstring |

### 4. Documentation

| File | Changes |
|------|---------|
| `python/docs/reference/NEO4J_PROVIDER_ARCHITECTURE.md` | `ChatAgent` → `Agent`, `ChatMessage` → `Message` in diagrams |
| `python/samples/README.md` | `ChatAgent` → `Agent` in descriptions |
| `CLAUDE.md` | Update code patterns section |

## Detailed Implementation Plan

### Step 1: Update `_provider.py` — Core Provider Class

This is the critical change. Transform the provider from the old `ContextProvider`/`invoking()` pattern to the new `BaseContextProvider`/`before_run()` hooks pattern.

**1a. Update imports (line 16)**

```python
# Before
from agent_framework import ChatMessage, Context, ContextProvider, Role

# After
from agent_framework import (
    AgentSession,
    BaseContextProvider,
    Message,
    SessionContext,
    SupportsAgentRun,
)
```

`Context` and `ContextProvider` are removed entirely. `Role` is no longer needed since the new `Message` accepts string role literals like `"user"`.

**1b. Change base class (line 63)**

```python
# Before
class Neo4jContextProvider(ContextProvider):

# After
class Neo4jContextProvider(BaseContextProvider):
```

**1c. Add `source_id` to constructor and call `super().__init__()` (line 79)**

```python
def __init__(
    self,
    *,
    source_id: str = "neo4j-context",
    # ... existing params unchanged ...
) -> None:
    super().__init__(source_id)
    # ... rest of __init__ unchanged ...
```

**1d. Replace `invoking()` with `before_run()` (lines 331-386)**

This is the main behavioral change. The method signature changes, input messages come from `context.input_messages` instead of a parameter, and output is written via `context.extend_messages()` instead of returning a `Context` object.

```python
# Before
@override
async def invoking(
    self,
    messages: ChatMessage | MutableSequence[ChatMessage],
    **_kwargs: Any,
) -> Context:
    if not self.is_connected:
        return Context()
    if isinstance(messages, ChatMessage):
        messages_list = [messages]
    else:
        messages_list = list(messages)
    filtered_messages = [
        msg for msg in messages_list
        if msg.text and msg.text.strip() and msg.role in [Role.USER, Role.ASSISTANT]
    ]
    if not filtered_messages:
        return Context()
    recent_messages = filtered_messages[-self._message_history_count :]
    query_text = "\n".join(msg.text for msg in recent_messages if msg.text)
    if not query_text.strip():
        return Context()
    context_messages: list[ChatMessage] = []
    result = await self._execute_search(query_text)
    if result.items:
        context_messages.append(ChatMessage(role=Role.USER, text=self._context_prompt))
        formatted_results = self._format_retriever_result(result)
        for text in formatted_results:
            if text:
                context_messages.append(ChatMessage(role=Role.USER, text=text))
    if not context_messages:
        return Context()
    return Context(messages=context_messages)

# After
async def before_run(
    self,
    *,
    agent: SupportsAgentRun,
    session: AgentSession,
    context: SessionContext,
    state: dict[str, Any],
) -> None:
    if not self.is_connected:
        return
    messages_list = list(context.input_messages)
    filtered_messages = [
        msg for msg in messages_list
        if msg.text and msg.text.strip() and msg.role in ("user", "assistant")
    ]
    if not filtered_messages:
        return
    recent_messages = filtered_messages[-self._message_history_count :]
    query_text = "\n".join(msg.text for msg in recent_messages if msg.text)
    if not query_text.strip():
        return
    result = await self._execute_search(query_text)
    if not result.items:
        return
    context_messages: list[Message] = [Message(role="user", text=self._context_prompt)]
    formatted_results = self._format_retriever_result(result)
    for text in formatted_results:
        if text:
            context_messages.append(Message(role="user", text=text))
    if context_messages:
        context.extend_messages(self.source_id, context_messages)
```

Key differences:
- No return value (mutates `context` instead)
- Messages read from `context.input_messages`
- Role comparison uses string literals `"user"`, `"assistant"` instead of `Role.USER`, `Role.ASSISTANT`
- Results written via `context.extend_messages(self.source_id, messages)`
- No `isinstance(messages, ChatMessage)` check needed — `context.input_messages` is always `list[Message]`
- Uses `SupportsAgentRun` protocol for the `agent` parameter (matches all official providers)

**1e. Clean up unused imports**

Remove `MutableSequence` from collections.abc import (no longer needed since we don't accept `MutableSequence[ChatMessage]`). Remove the `@override` decorator from `invoking` (it's gone). The `__aenter__`/`__aexit__` overrides remain unchanged.

### Step 2: Update `__init__.py` — Public Exports

No changes expected to the public API surface. `Neo4jContextProvider`, `Neo4jSettings`, `AzureAISettings`, `AzureAIEmbedder`, `FulltextRetriever` all remain.

### Step 3: Update `test_provider.py` — Tests

**3a. Update imports (line 8)**

```python
# Before
from agent_framework import ChatMessage, Role

# After
from agent_framework import Message, AgentSession, SessionContext
```

**3b. Update `TestInvoking` class (lines 161-182)**

The test currently calls `provider.invoking(message)` and checks the returned `Context`. This needs to change to call `provider.before_run()` with a `SessionContext` and check that context messages were added.

```python
# Before
message = ChatMessage(role=Role.USER, text="test query")
context = await provider.invoking(message)
assert context.messages == []

# After
input_messages = [Message(role="user", text="test query")]
session = AgentSession()
context = SessionContext(input_messages=input_messages)
await provider.before_run(agent=None, session=session, context=context, state={})
assert context.context_messages == {}  # Not connected, no messages added
```

### Step 4: Update Sample Docstrings and Print Statements

Simple text replacements across sample files:
- `ChatAgent` → `Agent` in all docstrings and print statements
- Files: `basic_fulltext/main.py`, `vector_search/main.py`, `shared/agent.py`

### Step 5: Update Documentation

**5a. `python/docs/reference/NEO4J_PROVIDER_ARCHITECTURE.md`**
- Line 39: `participant Agent as ChatAgent` → `participant Agent`
- Line 149: `Context(messages=[ChatMessage(...)])` → `context.extend_messages(source_id, [Message(...)])`

**5b. `python/samples/README.md`**
- Lines 136, 158: `ChatAgent` → `Agent`

**5c. `CLAUDE.md`**
- Update the "Key Patterns > Creating a Context Provider" code example to show `before_run()` instead of `invoking()`

### Step 6: Update `pyproject.toml` Dependency Pin

Update `python/packages/agent-framework-neo4j/pyproject.toml`:

```toml
# Before
"agent-framework-core>=1.0.0b",

# After
"agent-framework-core>=1.0.0b260212",
```

This pins to the latest framework version which includes `BaseContextProvider`, `Message`, `SessionContext`, `AgentSession`, and `SupportsAgentRun`.

### Step 7: Verify

```bash
cd python
uv sync --prerelease=allow
uv run pytest
uv run mypy packages/agent-framework-neo4j/agent_framework_neo4j
uv run ruff check packages/agent-framework-neo4j/agent_framework_neo4j
```
