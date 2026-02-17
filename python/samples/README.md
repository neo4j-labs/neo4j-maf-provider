# Neo4j Context Provider Samples

Sample applications demonstrating the `agent-framework-neo4j` library with Microsoft Agent Framework.

## How It Works

These samples use **Azure AI Foundry serverless models** to power the AI agents. The infrastructure is minimal:

- **AI Project** - A Microsoft Foundry project for managing model endpoints
- **Serverless Models** - Pay-as-you-go model deployments (GPT-4o, text-embedding-ada-002)

When you run a sample, the agent:
1. Receives your question
2. The Neo4j Context Provider searches the knowledge graph for relevant information
3. Retrieved context is injected into the conversation
4. The model generates a response grounded in the knowledge graph data

## Prerequisites

- Azure subscription with access to Azure AI services
- Azure CLI and Azure Developer CLI (`azd`) installed
- Neo4j database with your data (samples use two demo databases)
- Python 3.10+ and `uv` package manager

## Quick Start

```bash
# 1. Install dependencies (from repo root)
uv sync --prerelease=allow

# 2. Configure Azure region (from samples directory)
cd samples
./scripts/setup_azure.sh

# 3. Deploy Azure infrastructure (includes model deployments)
azd up

# 4. Sync Azure environment variables
uv run setup_env.py

# 5. Add Neo4j credentials to .env

# 6. Run samples
uv run start-samples
```

## 1. Deploy Azure Infrastructure

First, configure your Azure region:

```bash
cd samples
./scripts/setup_azure.sh
```

Then deploy the infrastructure:

```bash
azd up
```

This provisions:
- Azure AI Services account
- Azure AI Project
- Model deployments (GPT-4o, text-embedding-ada-002)
- Required IAM role assignments

After provisioning, sync the Azure endpoints to your `.env` file:

```bash
uv run setup_env.py
```

This populates your `.env` with:
```
AZURE_AI_PROJECT_ENDPOINT=https://...
AZURE_AI_MODEL_NAME=gpt-4o
AZURE_AI_EMBEDDING_NAME=text-embedding-ada-002
```

## 2. Configure Neo4j

Add your Neo4j database credentials to `.env`:

### Financial Documents Database (samples 1-4)

See [SETUP.md](SETUP.md) for instructions on setting up the Neo4j database with financial data.

### Aircraft Database (samples 5-7)

For aircraft database access, please contact the author.

## 3. Run Samples

### Interactive Menu

```bash
uv run start-samples
```

### Run Specific Sample

```bash
uv run start-samples 1   # Semantic Search
uv run start-samples 2   # Context Provider (Fulltext)
uv run start-samples 3   # Context Provider (Vector)
uv run start-samples 4   # Context Provider (Graph-Enriched)
uv run start-samples 5   # Aircraft Maintenance Search
uv run start-samples 6   # Flight Delay Analysis
uv run start-samples 7   # Component Health Analysis
uv run start-samples a   # Run all demos
```

## Available Samples

### Sample 1: Semantic Search (`vector_search/semantic_search.py`)

Direct semantic search demonstration without an agent. Shows the raw search capabilities of the `Neo4jContextProvider` with vector embeddings and graph enrichment.

**What it shows:**
- Vector similarity search using Azure AI embeddings
- Graph traversal to enrich results with company and risk factor data
- Raw search result output (scores, metadata, text previews)

**Graph pattern:**
```
Chunk -[:FROM_DOCUMENT]-> Document <-[:FILED]- Company -[:FACES_RISK]-> RiskFactor
```

**Use case:** Understanding how the provider retrieves and enriches data before passing it to an agent.

---

### Sample 2: Context Provider - Fulltext (`basic_fulltext/main.py`)

Basic fulltext search context provider integrated with an Agent. Uses Neo4j's fulltext index to find relevant document chunks based on keyword matching.

**What it shows:**
- Creating a `Neo4jContextProvider` with `index_type="fulltext"`
- Automatic context injection into agent conversations
- No embeddings required—uses native fulltext search

**Configuration:**
```python
provider = Neo4jContextProvider(
    index_name="search_chunks",
    index_type="fulltext",
    top_k=3,
)
```

**Best for:** Fast keyword-based retrieval when exact term matching is sufficient.

---

### Sample 3: Context Provider - Vector (`vector_search/main.py`)

Vector similarity search context provider with an Agent. Uses Azure AI embeddings to find semantically similar content even when exact keywords don't match.

**What it shows:**
- Creating a `Neo4jContextProvider` with `index_type="vector"`
- Integrating the `AzureAIEmbedder` for query embedding
- Semantic matching (e.g., "challenges" finds content about "risk factors")

**Configuration:**
```python
provider = Neo4jContextProvider(
    index_name="chunkEmbeddings",
    index_type="vector",
    embedder=embedder,
    top_k=5,
)
```

**Best for:** Finding conceptually related content where phrasing varies.

---

### Sample 4: Context Provider - Graph-Enriched (`graph_enriched/main.py`)

Vector search combined with graph traversal for rich context. After finding relevant chunks, a custom Cypher query traverses relationships to gather company names, tickers, products, and risk factors.

**What it shows:**
- Using `retrieval_query` for post-search graph enrichment
- Returning structured metadata alongside text content
- Agent responses that cite specific companies, products, and risks

**Graph pattern:**
```
Chunk -[:FROM_DOCUMENT]-> Document <-[:FILED]- Company
Company -[:FACES_RISK]-> RiskFactor
Company -[:MENTIONS]-> Product
```

**Retrieval query returns:** `text`, `score`, `company`, `ticker`, `risks[]`, `products[]`

**Best for:** Applications requiring rich, structured context from interconnected graph data.

---

### Sample 5: Aircraft Maintenance Search (`aircraft_domain/maintenance_search.py`)

Fulltext search on aircraft maintenance events with graph enrichment. Searches fault descriptions and corrective actions, then traverses the graph to provide aircraft, system, and component context.

**What it shows:**
- Domain-specific fulltext search configuration
- Graph traversal through the aircraft hierarchy
- Structured maintenance records for agent analysis

**Graph pattern:**
```
MaintenanceEvent <-[:HAS_EVENT]- Component <-[:HAS_COMPONENT]- System <-[:HAS_SYSTEM]- Aircraft
```

**Retrieval query returns:** `fault`, `corrective_action`, `severity`, `aircraft`, `model`, `system`, `component`

**Example queries:** "What maintenance issues involve vibration?", "Tell me about electrical faults"

---

### Sample 6: Flight Delay Analysis (`aircraft_domain/flight_delays.py`)

Fulltext search on flight delays with route and aircraft context. Searches delay causes and enriches results with flight numbers, aircraft tail numbers, and origin/destination routes.

**What it shows:**
- Searching delay records by cause keywords
- Combining delay data with flight and route information
- Minimal context configuration (`top_k=2`, `message_history_count=1`) to avoid token overflow

**Graph pattern:**
```
Delay <-[:HAS_DELAY]- Flight -[:OPERATES_FLIGHT]-> Aircraft
Flight -[:DEPARTS_FROM]-> Origin Airport
Flight -[:ARRIVES_AT]-> Destination Airport
```

**Retrieval query returns:** `cause`, `minutes`, `flight`, `aircraft`, `route` (e.g., "LAX -> JFK")

**Example queries:** "What flights were delayed due to weather?", "Tell me about security-related delays"

---

### Sample 7: Component Health Analysis (`aircraft_domain/component_health.py`)

Fulltext search on aircraft components with maintenance history. Searches component names and types, then aggregates maintenance event counts and severity levels.

**What it shows:**
- Searching the component hierarchy
- Aggregating related maintenance events (`count(event)`, `last_severity`)
- Component-centric view of aircraft health

**Graph pattern:**
```
Component <-[:HAS_COMPONENT]- System <-[:HAS_SYSTEM]- Aircraft
Component -[:HAS_EVENT]-> MaintenanceEvent
```

**Retrieval query returns:** `component`, `type`, `aircraft`, `system`, `maintenance_events`, `severity`

**Example queries:** "What turbine components have maintenance issues?", "Tell me about fuel pump components"

## Directory Structure

```
samples/
├── azure.yaml              # Azure Developer CLI configuration
├── setup_env.py            # Sync Azure env vars to .env
├── infra/                  # Azure Bicep templates
│   └── main.bicep          # AI Services, Project, and model deployments
├── scripts/                # Setup helper scripts
├── src/samples/
│   ├── basic_fulltext/     # Fulltext search samples
│   ├── vector_search/      # Vector similarity samples
│   ├── graph_enriched/     # Graph traversal samples
│   ├── aircraft_domain/    # Aircraft maintenance samples
│   └── shared/             # Shared utilities (agent config, CLI, logging)
```

## Troubleshooting

### "Model deployment not found"

Run `azd up` to deploy the infrastructure including model deployments, then run `uv run setup_env.py` to sync the model names to your `.env` file.

### "Neo4j not configured"

Add the required Neo4j environment variables to `.env`. The samples check for:
- `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` (financial database)
- `AIRCRAFT_NEO4J_URI`, `AIRCRAFT_NEO4J_USERNAME`, `AIRCRAFT_NEO4J_PASSWORD` (aircraft database)

### "Azure not configured"

Run `azd up` followed by `uv run setup_env.py` to populate Azure variables.

### "Index not found"

Create the required indexes in your Neo4j database. See `SETUP.md` for details.

## Cost Estimate

With serverless models, you only pay for what you use:

- **Chat model (GPT-4o)**: ~$0.01-0.03 per 1K tokens
- **Embedding model**: ~$0.0001 per 1K tokens
- **Running all 8 demos**: approximately $0.10-0.30 total

No idle costs - the AI Services account itself has no ongoing charges when not in use.
