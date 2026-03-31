using Azure.AI.OpenAI;
using Azure.Identity;
using Microsoft.Agents.AI;
using Microsoft.Agents.AI.OpenAI;
using Microsoft.Extensions.AI;
using Neo4j.AgentFramework.GraphRAG;
using Neo4j.Driver;

// ── Load .env from repo root ─────────────────────────────────────────────────
LoadEnvFile();

// ── Load configuration from environment ──────────────────────────────────────
var neo4jUri = Env("NEO4J_URI");
var neo4jUser = Env("NEO4J_USERNAME", "neo4j");
var neo4jPassword = Env("NEO4J_PASSWORD");
var vectorIndex = Env("NEO4J_VECTOR_INDEX_NAME", "chunkEmbeddings");
var fulltextIndex = Env("NEO4J_FULLTEXT_INDEX_NAME", "search_chunks");
var azureEndpoint = Env("AZURE_AI_SERVICES_ENDPOINT");
var chatDeployment = Env("AZURE_AI_MODEL_NAME", "gpt-4o");
var embeddingDeployment = Env("AZURE_AI_EMBEDDING_NAME", "text-embedding-3-small");

// ── Create Azure OpenAI clients ──────────────────────────────────────────────
var credential = new DefaultAzureCredential();
var azureClient = new AzureOpenAIClient(new Uri(azureEndpoint), credential);

IEmbeddingGenerator<string, Embedding<float>> embeddingGenerator = azureClient
    .GetEmbeddingClient(embeddingDeployment)
    .AsIEmbeddingGenerator();

// ── Create Neo4j driver ──────────────────────────────────────────────────────
await using var driver = GraphDatabase.Driver(neo4jUri, AuthTokens.Basic(neo4jUser, neo4jPassword));
await driver.VerifyConnectivityAsync();
Console.WriteLine("Connected to Neo4j.\n");

// ── Select demo ──────────────────────────────────────────────────────────────
var demoArg = args.Length > 0 ? args[0] : null;
if (demoArg == null)
{
    Console.WriteLine("Available demos:");
    Console.WriteLine("  1  Fulltext search");
    Console.WriteLine("  2  Vector search");
    Console.WriteLine("  3  Graph-enriched vector search");
    Console.WriteLine("  a  Run all demos");
    Console.Write("\nSelect demo: ");
    demoArg = Console.ReadLine()?.Trim();
}

if (demoArg is "1" or "a")
    await RunFulltextDemo();
if (demoArg is "2" or "a")
    await RunVectorDemo();
if (demoArg is "3" or "a")
    await RunGraphEnrichedDemo();

return;

// ── Demo 1: Fulltext search ─────────────────────────────────────────────────
async Task RunFulltextDemo()
{
    Console.WriteLine("═══════════════════════════════════════════");
    Console.WriteLine(" Demo 1: Fulltext Search");
    Console.WriteLine("═══════════════════════════════════════════\n");

    await using var provider = new Neo4jContextProvider(driver, new Neo4jContextProviderOptions
    {
        IndexName = fulltextIndex,
        IndexType = IndexType.Fulltext,
        TopK = 3,
        ContextPrompt = "## Knowledge Graph Context\nUse the following information from the knowledge graph to answer the question:",
    });

    await RunAgent(provider, [
        "What products does Microsoft offer?",
        "Tell me about risk factors for technology companies",
        "What are some financial metrics mentioned in SEC filings?",
    ]);
}

// ── Demo 2: Vector search ───────────────────────────────────────────────────
async Task RunVectorDemo()
{
    Console.WriteLine("═══════════════════════════════════════════");
    Console.WriteLine(" Demo 2: Vector Search");
    Console.WriteLine("═══════════════════════════════════════════\n");

    await using var provider = new Neo4jContextProvider(driver, new Neo4jContextProviderOptions
    {
        IndexName = vectorIndex,
        IndexType = IndexType.Vector,
        EmbeddingGenerator = embeddingGenerator,
        TopK = 5,
        ContextPrompt = "## Semantic Search Results\nUse the following semantically relevant information to answer the question:",
    });

    await RunAgent(provider, [
        "What are the main business activities of tech companies?",
        "How do companies generate revenue and measure performance?",
    ]);
}

// ── Demo 3: Graph-enriched vector search ─────────────────────────────────────
async Task RunGraphEnrichedDemo()
{
    Console.WriteLine("═══════════════════════════════════════════");
    Console.WriteLine(" Demo 3: Graph-Enriched Vector Search");
    Console.WriteLine("═══════════════════════════════════════════\n");

    const string retrievalQuery = """
        MATCH (node)-[:FROM_DOCUMENT]->(doc:Document)<-[:FILED]-(company:Company)
        OPTIONAL MATCH (company)-[:FACES_RISK]->(risk:RiskFactor)
        WITH node, score, company, doc,
             collect(DISTINCT risk.name)[0..5] AS risks
        OPTIONAL MATCH (company)-[:MENTIONS]->(product:Product)
        WITH node, score, company, doc, risks,
             collect(DISTINCT product.name)[0..5] AS products
        WHERE score IS NOT NULL
        RETURN
            node.text AS text,
            score,
            company.name AS company,
            company.ticker AS ticker,
            risks,
            products
        ORDER BY score DESC
        """;

    await using var provider = new Neo4jContextProvider(driver, new Neo4jContextProviderOptions
    {
        IndexName = vectorIndex,
        IndexType = IndexType.Vector,
        EmbeddingGenerator = embeddingGenerator,
        RetrievalQuery = retrievalQuery,
        TopK = 5,
        ContextPrompt = "## Graph-Enriched Knowledge Context\nUse the following graph-enriched information to provide detailed answers:",
    });

    await RunAgent(provider, [
        "What are Apple's main products and what risks does the company face?",
        "Tell me about Microsoft's cloud services and business risks",
        "What products and risks are mentioned in Amazon's filings?",
    ]);
}

// ── Shared: create agent and run queries ─────────────────────────────────────
async Task RunAgent(Neo4jContextProvider provider, string[] queries)
{
    AIAgent agent = azureClient
        .GetChatClient(chatDeployment)
        .AsIChatClient()
        .AsBuilder()
        .UseAIContextProviders(provider)
        .BuildAIAgent(new ChatClientAgentOptions
        {
            ChatOptions = new ChatOptions
            {
                Instructions = "You are a helpful assistant that answers questions using knowledge graph context. "
                    + "When context is provided, use it to give informed answers. Be concise but thorough.",
            },
        });

    var session = await agent.CreateSessionAsync();

    foreach (var query in queries)
    {
        Console.WriteLine($"User: {query}\n");
        var response = await agent.RunAsync(query, session);
        Console.WriteLine($"Assistant: {response}\n");
        Console.WriteLine(new string('─', 60) + "\n");
    }
}

// ── Helpers ──────────────────────────────────────────────────────────────────
static string Env(string name, string? defaultValue = null)
{
    return Environment.GetEnvironmentVariable(name)
        ?? defaultValue
        ?? throw new InvalidOperationException($"Environment variable '{name}' is not set.");
}

static void LoadEnvFile()
{
    // Walk up from the binary directory to find .env at repo root
    var dir = new DirectoryInfo(AppContext.BaseDirectory);
    while (dir != null)
    {
        var envFile = Path.Combine(dir.FullName, ".env");
        if (File.Exists(envFile))
        {
            foreach (var line in File.ReadAllLines(envFile))
            {
                var trimmed = line.Trim();
                if (string.IsNullOrEmpty(trimmed) || trimmed.StartsWith('#'))
                    continue;
                var eqIdx = trimmed.IndexOf('=');
                if (eqIdx <= 0) continue;
                var key = trimmed[..eqIdx].Trim();
                var val = trimmed[(eqIdx + 1)..].Trim();
                if (Environment.GetEnvironmentVariable(key) == null)
                    Environment.SetEnvironmentVariable(key, val);
            }
            Console.WriteLine($"Loaded .env from {dir.FullName}");
            return;
        }
        dir = dir.Parent;
    }
}
