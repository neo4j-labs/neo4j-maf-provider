using System.Collections;
using System.Globalization;
using Microsoft.Agents.AI;
using Microsoft.Extensions.AI;
using Neo4j.AgentFramework.GraphRAG.Retrieval;
using Neo4j.Driver;

namespace Neo4j.AgentFramework.GraphRAG;

/// <summary>
/// Context provider that retrieves knowledge graph context from Neo4j.
///
/// Key design principles:
/// - NO entity extraction — passes full message text to search
/// - Index-driven configuration — works with any Neo4j index
/// - Configurable enrichment — users define their own retrieval_query
/// </summary>
public sealed class Neo4jContextProvider : AIContextProvider, IAsyncDisposable
{
    private readonly IDriver _driver;
    private readonly bool _ownsDriver;
    private readonly Neo4jContextProviderOptions _options;
    private readonly IRetriever _retriever;

    /// <summary>
    /// Creates a new Neo4j context provider with an existing driver.
    /// </summary>
    /// <param name="driver">The Neo4j driver instance.</param>
    /// <param name="options">Provider configuration options.</param>
    public Neo4jContextProvider(IDriver driver, Neo4jContextProviderOptions options)
        : base(null, null)
    {
        ArgumentNullException.ThrowIfNull(driver);
        ArgumentNullException.ThrowIfNull(options);
        options.Validate();

        _driver = driver;
        _ownsDriver = false;
        _options = options;
        _retriever = CreateRetriever();
    }

    /// <summary>
    /// Creates a new Neo4j context provider that manages its own driver connection.
    /// </summary>
    public static Neo4jContextProvider Create(
        string uri,
        string username,
        string password,
        Neo4jContextProviderOptions options)
    {
        var driver = GraphDatabase.Driver(uri, AuthTokens.Basic(username, password));
        var provider = new Neo4jContextProvider(driver, options, ownsDriver: true);
        return provider;
    }

    private Neo4jContextProvider(IDriver driver, Neo4jContextProviderOptions options, bool ownsDriver)
        : base(null, null)
    {
        options.Validate();
        _driver = driver;
        _ownsDriver = ownsDriver;
        _options = options;
        _retriever = CreateRetriever();
    }

    /// <inheritdoc/>
    protected override async ValueTask<AIContext> ProvideAIContextAsync(
        InvokingContext context,
        CancellationToken cancellationToken = default)
    {
        var messages = context.AIContext.Messages;
        if (messages is null)
            return new AIContext();

        // Filter to user/assistant messages with text content, take recent N
        var filteredMessages = messages
            .Where(m => m.Role == ChatRole.User || m.Role == ChatRole.Assistant)
            .Where(m => !string.IsNullOrWhiteSpace(m.Text))
            .TakeLast(_options.MessageHistoryCount)
            .ToList();

        if (filteredMessages.Count == 0)
            return new AIContext();

        // CRITICAL: Concatenate full message text — NO ENTITY EXTRACTION
        var queryText = string.Join("\n", filteredMessages.Select(m => m.Text));
        if (string.IsNullOrWhiteSpace(queryText))
            return new AIContext();

        // Search knowledge graph
        var result = await _retriever.SearchAsync(queryText, _options.TopK, cancellationToken)
            .ConfigureAwait(false);

        if (result.Items.Count == 0)
            return new AIContext();

        // Format results as context messages
        var contextMessages = new List<ChatMessage>
        {
            new(ChatRole.User, _options.ContextPrompt)
        };

        foreach (var item in result.Items)
        {
            var formatted = FormatResultItem(item);
            if (!string.IsNullOrEmpty(formatted))
                contextMessages.Add(new ChatMessage(ChatRole.User, formatted));
        }

        return new AIContext { Messages = contextMessages };
    }

    private IRetriever CreateRetriever()
    {
        return _options.IndexType switch
        {
            IndexType.Vector => new VectorRetriever(
                _driver,
                _options.IndexName,
                _options.EmbeddingGenerator!,
                _options.RetrievalQuery),

            IndexType.Fulltext => new FulltextRetriever(
                _driver,
                _options.IndexName,
                _options.RetrievalQuery,
                _options.EffectiveFilterStopWords),

            IndexType.Hybrid => new HybridRetriever(
                _driver,
                _options.IndexName,
                _options.FulltextIndexName!,
                _options.EmbeddingGenerator!,
                _options.RetrievalQuery,
                _options.EffectiveFilterStopWords),

            _ => throw new ArgumentOutOfRangeException(nameof(_options.IndexType))
        };
    }

    private static string FormatResultItem(RetrieverResultItem item)
    {
        var parts = new List<string>();

        if (item.Metadata is not null)
        {
            // Score first
            if (item.Metadata.TryGetValue("score", out var score) && score is not null)
                parts.Add(string.Format(CultureInfo.InvariantCulture, "[Score: {0:F3}]", score));

            // Other metadata
            foreach (var (key, value) in item.Metadata)
            {
                if (key == "score" || value is null)
                    continue;
                parts.Add(FormatField(key, value));
            }
        }

        if (!string.IsNullOrEmpty(item.Content))
            parts.Add(item.Content);

        return string.Join(" ", parts.Where(p => !string.IsNullOrEmpty(p)));
    }

    private static string FormatField(string key, object value)
    {
        if (value is string s)
            return $"[{key}: {s}]";

        if (value is IEnumerable enumerable and not string)
        {
            var items = enumerable.Cast<object>().ToList();
            return items.Count > 0
                ? $"[{key}: {string.Join(", ", items)}]"
                : string.Empty;
        }

        return $"[{key}: {value}]";
    }

    /// <inheritdoc/>
    public async ValueTask DisposeAsync()
    {
        if (_ownsDriver)
        {
            await _driver.DisposeAsync().ConfigureAwait(false);
        }
    }
}
