# Neo4j Context Provider for Microsoft Agent Framework (.NET)

A .NET library that provides Neo4j knowledge graph context to AI agents built with the [Microsoft Agent Framework](https://github.com/microsoft/agent-framework). The provider automatically retrieves relevant information from Neo4j using vector, fulltext, or hybrid search and injects it into the agent's conversation context.

## Features

| Feature | Description |
|---------|-------------|
| **Vector Search** | Semantic similarity search using embeddings |
| **Fulltext Search** | Keyword matching using BM25 scoring |
| **Hybrid Search** | Combined vector + fulltext for best results |
| **Graph Enrichment** | Custom Cypher queries traverse relationships after initial search |

## Installation

```bash
dotnet add package Neo4j.AgentFramework.GraphRAG
```

## Quick Start

```csharp
using Azure.AI.OpenAI;
using Azure.Identity;
using Microsoft.Agents.AI;
using Microsoft.Extensions.AI;
using Neo4j.AgentFramework.GraphRAG;
using Neo4j.Driver;

// Create embedding generator (any IEmbeddingGenerator implementation works)
var credential = new DefaultAzureCredential();
IEmbeddingGenerator<string, Embedding<float>> embedder = new AzureOpenAIClient(
        new Uri(azureEndpoint), credential)
    .GetEmbeddingClient("text-embedding-3-small")
    .AsIEmbeddingGenerator();

// Create the Neo4j context provider
await using var provider = new Neo4jContextProvider(driver, new Neo4jContextProviderOptions
{
    IndexName = "chunkEmbeddings",
    IndexType = IndexType.Vector,
    EmbeddingGenerator = embedder,
    TopK = 5,
});

// Create an agent with the provider
AIAgent agent = new AzureOpenAIClient(new Uri(azureEndpoint), credential)
    .GetChatClient("gpt-4o")
    .AsIChatClient()
    .AsBuilder()
    .UseAIContextProviders(provider)
    .BuildAIAgent(new ChatClientAgentOptions
    {
        ChatOptions = new ChatOptions
        {
            Instructions = "You are a helpful assistant.",
        },
    });

var session = await agent.CreateSessionAsync();
Console.WriteLine(await agent.RunAsync("What products does Acme offer?", session));
```

## Search Modes

### Fulltext Search

Keyword-based search using Neo4j fulltext indexes. No embedding generator needed.

```csharp
var provider = new Neo4jContextProvider(driver, new Neo4jContextProviderOptions
{
    IndexName = "search_chunks",
    IndexType = IndexType.Fulltext,
    TopK = 3,
});
```

### Vector Search

Semantic similarity search using embeddings.

```csharp
var provider = new Neo4jContextProvider(driver, new Neo4jContextProviderOptions
{
    IndexName = "chunkEmbeddings",
    IndexType = IndexType.Vector,
    EmbeddingGenerator = embedder,
    TopK = 5,
});
```

### Hybrid Search

Combines vector and fulltext search, taking the best score per result.

```csharp
var provider = new Neo4jContextProvider(driver, new Neo4jContextProviderOptions
{
    IndexName = "chunkEmbeddings",
    IndexType = IndexType.Hybrid,
    FulltextIndexName = "search_chunks",
    EmbeddingGenerator = embedder,
    TopK = 5,
});
```

### Graph-Enriched Search

Add a `RetrievalQuery` to traverse the graph after the initial search. The query receives `node` and `score` variables from the index search and must return `text` and `score` columns.

```csharp
var provider = new Neo4jContextProvider(driver, new Neo4jContextProviderOptions
{
    IndexName = "chunkEmbeddings",
    IndexType = IndexType.Vector,
    EmbeddingGenerator = embedder,
    RetrievalQuery = """
        MATCH (node)-[:FROM_DOCUMENT]->(doc:Document)<-[:FILED]-(company:Company)
        RETURN node.text AS text, score, company.name AS company
        ORDER BY score DESC
        """,
    TopK = 5,
});
```

## Configuration

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `IndexName` | `string` | *required* | Neo4j index name |
| `IndexType` | `IndexType` | `Vector` | Search type: `Vector`, `Fulltext`, or `Hybrid` |
| `EmbeddingGenerator` | `IEmbeddingGenerator<string, Embedding<float>>?` | `null` | Required for Vector/Hybrid |
| `FulltextIndexName` | `string?` | `null` | Required for Hybrid |
| `RetrievalQuery` | `string?` | `null` | Custom Cypher for graph enrichment |
| `TopK` | `int` | `5` | Max results to return |
| `MessageHistoryCount` | `int` | `10` | Recent messages to use as search query |
| `FilterStopWords` | `bool?` | `null` | Filter stop words (defaults to `true` for Fulltext) |
| `ContextPrompt` | `string` | *(built-in)* | System prompt prepended to results |

## Environment Variables

The `Neo4jSettings` helper reads connection details from environment variables:

```
NEO4J_URI=neo4j+s://xxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=<password>
NEO4J_VECTOR_INDEX_NAME=chunkEmbeddings
NEO4J_FULLTEXT_INDEX_NAME=search_chunks
```

```csharp
var settings = new Neo4jSettings();
if (settings.IsConfigured)
{
    var driver = GraphDatabase.Driver(settings.Uri, AuthTokens.Basic(settings.Username, settings.Password!));
}
```

## Running the Sample

1. Set up Azure AI Foundry and Neo4j — see [examples/SETUP.md](../examples/SETUP.md) for full instructions
2. Copy `.env.sample` to `.env` at the repo root and fill in your credentials
3. Load demo data: `python examples/scripts/seed_data.py` (or restore the full backup)
4. Run the sample:

```bash
cd dotnet
dotnet run --project samples/Neo4j.Samples
```

## Project Structure

```
dotnet/
├── src/Neo4j.AgentFramework.GraphRAG/         # Library
│   ├── Neo4jContextProvider.cs        # AIContextProvider implementation
│   ├── Neo4jContextProviderOptions.cs # Configuration
│   ├── Neo4jSettings.cs               # Environment variable loader
│   ├── IndexType.cs                   # Vector, Fulltext, Hybrid enum
│   ├── StopWords.cs                   # Stop word filtering
│   └── Retrieval/                     # Search implementations
│       ├── IRetriever.cs
│       ├── RetrieverResult.cs
│       ├── VectorRetriever.cs
│       ├── FulltextRetriever.cs
│       └── HybridRetriever.cs
├── samples/Neo4j.Samples/            # Demo console app
├── tests/Neo4j.AgentFramework.GraphRAG.Tests/  # Unit tests
└── neo4j-provider.sln
```

## Dependencies

| Package | Purpose |
|---------|---------|
| `Microsoft.Agents.AI.Abstractions` | Agent Framework context provider base class |
| `Neo4j.Driver` | Neo4j database access |

The library uses `IEmbeddingGenerator<string, Embedding<float>>` from `Microsoft.Extensions.AI.Abstractions` (transitive dependency) as the standard .NET embedding abstraction. Any AI provider (Azure OpenAI, OpenAI, Ollama) can supply an implementation.

## Development

```bash
cd dotnet
dotnet build                    # Build all projects
dotnet test                     # Run unit tests
dotnet pack src/Neo4j.AgentFramework.GraphRAG  # Create NuGet package
```
