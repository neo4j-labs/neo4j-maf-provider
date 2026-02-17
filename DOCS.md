# Documentation Proposal: Neo4j Context Provider for Microsoft Agent Framework

This proposal outlines how to document the `agent-framework-neo4j` context provider for inclusion in Microsoft's official documentation.

---

## Documentation Locations (Published to learn.microsoft.com)

| Page | URL | Content |
|------|-----|---------|
| **Integrations Overview** | [learn.microsoft.com/en-us/agent-framework/integrations/overview](https://learn.microsoft.com/en-us/agent-framework/integrations/overview) | Tables listing all available providers |
| **Agent RAG** | [learn.microsoft.com/en-us/agent-framework/user-guide/agents/agent-rag](https://learn.microsoft.com/en-us/agent-framework/user-guide/agents/agent-rag) | RAG context provider documentation |

**Source Repository:** `semantic-kernel-docs` (MicrosoftDocs/semantic-kernel-docs)

---

## Current Provider Documentation Pattern

Based on the live Microsoft Learn site:

### Integrations Overview Page Structure

**RAG AI Context Providers (Python):**
| Provider | Release Status |
|----------|----------------|
| Azure AI Search Provider | Preview |

---

## Proposed Changes

### 1. Integrations Overview Page

**File in semantic-kernel-docs:** `agent-framework/integrations/overview.md` (or similar)

**Add to RAG AI Context Providers (Python) table:**
| Provider | Release Status |
|----------|----------------|
| Neo4j Context Provider | Preview |

### 2. Agent RAG Page

**File in semantic-kernel-docs:** `agent-framework/user-guide/agents/agent-rag.md`

**Location:** After "Supported VectorStore Connectors" section (within Python zone pivot)

**Content to add:**

```markdown
### Using Neo4j for Graph-Enhanced RAG

For knowledge graph scenarios where relationships between entities matter, the Neo4j Context Provider offers graph-enhanced RAG:

```python
from agent_framework_neo4j import Neo4jContextProvider, Neo4jSettings, AzureAIEmbedder

settings = Neo4jSettings()

neo4j_provider = Neo4jContextProvider(
    uri=settings.uri,
    username=settings.username,
    password=settings.get_password(),
    index_name="documentChunks",
    index_type="vector",
    embedder=AzureAIEmbedder(...),
    top_k=5,
    retrieval_query="""
        MATCH (node)-[:FROM_DOCUMENT]->(doc:Document)
        OPTIONAL MATCH (doc)<-[:FILED]-(company:Company)
        RETURN node.text AS text, score, doc.title AS title, company.name AS company
        ORDER BY score DESC
    """,
)

async with neo4j_provider:
    agent = ChatAgent(
        chat_client=chat_client,
        instructions="You are a financial analyst assistant.",
        context_providers=neo4j_provider
    )
    response = await agent.run("What risks does Acme Corp face?")
```

Key features:
- **Index-driven**: Works with any Neo4j vector or fulltext index
- **Graph traversal**: Custom Cypher queries enrich search results with related entities

> [!TIP]
> Install with `pip install agent-framework-neo4j`. See the [Neo4j Context Provider repository](https://github.com/<org>/neo4j-maf-provider) for complete documentation.
```

---

## Implementation Plan

### Step 1: Prepare This Repository

1. Publish package to PyPI as `agent-framework-neo4j`
2. Make repository public
3. Update `<org>` placeholders with actual GitHub organization

### Step 2: Submit PR to semantic-kernel-docs

```bash
git clone https://github.com/MicrosoftDocs/semantic-kernel-docs.git
cd semantic-kernel-docs
git checkout -b docs/add-neo4j-context-provider
```

**Files to edit:**
1. `agent-framework/integrations/overview.md` - Add Neo4j to provider tables
2. `agent-framework/user-guide/agents/agent-rag.md` - Add Neo4j graph-enhanced RAG section

**PR Description:**
```markdown
## Summary
Adds documentation for the Neo4j Context Provider (`agent-framework-neo4j`), a community-contributed provider for knowledge graph RAG.

## Changes
- Added Neo4j to integrations overview tables
- Added Neo4j graph-enhanced RAG section to agent-rag.md

## Links
- Repository: https://github.com/<org>/neo4j-maf-provider
- PyPI: https://pypi.org/project/agent-framework-neo4j/
```

### Step 3 (Optional): Submit PR to agent-framework GitHub

Edit `/python/samples/getting_started/context_providers/README.md` to add Neo4j section for developers browsing the GitHub repo directly.

---

## Documentation Format Reference

### Microsoft Learn Conventions

| Element | Syntax |
|---------|--------|
| Zone pivots | `:::zone pivot="programming-language-python"` ... `:::zone-end` |
| Tips | `> [!TIP]` |
| Important | `> [!IMPORTANT]` |
| Notes | `> [!NOTE]` |
| Code blocks | Triple backticks with language |
| Internal links | `[text](/path/to/doc)` |
| External links | `[text](https://...)` |

### Current Mem0 Documentation Style

The Mem0 example on the live site is minimal:
- One code example (~10 lines)
- Brief description
- Link to tutorial for more details

Neo4j documentation should follow this same brief pattern, with links to the external repository for full documentation.

---

## Questions to Resolve

1. **Repository URL**: What GitHub org/user will host this repo?
2. **Package name**: Confirm `agent-framework-neo4j` as PyPI package name
3. **Provider category**: Neo4j is a RAG provider (knowledge graph retrieval)
4. **Microsoft contribution process**: Does MicrosoftDocs/semantic-kernel-docs accept external community provider PRs?

---

## Summary

**One PR to semantic-kernel-docs** modifying two files:

| File | Change |
|------|--------|
| `integrations/overview.md` | Add Neo4j to RAG provider table |
| `user-guide/agents/agent-rag.md` | Add Neo4j graph-enhanced RAG example |

All documentation links to the external repository rather than incorporating source code.

---

## Sources

- [Agent Framework Integrations Overview](https://learn.microsoft.com/en-us/agent-framework/integrations/overview)
- [Agent Retrieval Augmented Generation (RAG)](https://learn.microsoft.com/en-us/agent-framework/user-guide/agents/agent-rag)
