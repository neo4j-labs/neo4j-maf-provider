using Microsoft.Extensions.AI;

namespace Neo4j.AgentFramework.GraphRAG;

/// <summary>
/// Configuration options for <see cref="Neo4jContextProvider"/>.
/// </summary>
public sealed class Neo4jContextProviderOptions
{
    private const string DefaultContextPrompt =
        "## Knowledge Graph Context\n" +
        "Use the following information from the knowledge graph to answer the question:";

    /// <summary>
    /// Name of the Neo4j index to query. Required.
    /// For vector/hybrid: the vector index name.
    /// For fulltext: the fulltext index name.
    /// </summary>
    public required string IndexName { get; init; }

    /// <summary>
    /// Type of search to perform. Defaults to <see cref="IndexType.Vector"/>.
    /// </summary>
    public IndexType IndexType { get; init; } = IndexType.Vector;

    /// <summary>
    /// Fulltext index name for hybrid search.
    /// Required when <see cref="IndexType"/> is <see cref="IndexType.Hybrid"/>.
    /// </summary>
    public string? FulltextIndexName { get; init; }

    /// <summary>
    /// Optional Cypher query for graph enrichment after index search.
    /// Must use <c>node</c> and <c>score</c> variables from the index search.
    /// Must return at least <c>text</c> and <c>score</c> columns.
    /// </summary>
    public string? RetrievalQuery { get; init; }

    /// <summary>
    /// Number of results to retrieve. Defaults to 5. Must be at least 1.
    /// </summary>
    public int TopK { get; init; } = 5;

    /// <summary>
    /// Prompt prepended to context messages. Defaults to a knowledge graph context prompt.
    /// </summary>
    public string ContextPrompt { get; init; } = DefaultContextPrompt;

    /// <summary>
    /// Number of recent messages to use for the search query. Defaults to 10. Must be at least 1.
    /// </summary>
    public int MessageHistoryCount { get; init; } = 10;

    /// <summary>
    /// Whether to filter stop words from fulltext queries.
    /// Defaults to <c>true</c> for fulltext indexes, <c>false</c> otherwise.
    /// </summary>
    public bool? FilterStopWords { get; init; }

    /// <summary>
    /// Embedding generator for vector and hybrid search.
    /// Required when <see cref="IndexType"/> is <see cref="IndexType.Vector"/> or <see cref="IndexType.Hybrid"/>.
    /// </summary>
    public IEmbeddingGenerator<string, Embedding<float>>? EmbeddingGenerator { get; init; }

    /// <summary>
    /// Validates the configuration and throws if invalid.
    /// </summary>
    internal void Validate()
    {
        if (string.IsNullOrWhiteSpace(IndexName))
            throw new ArgumentException("IndexName is required.", nameof(IndexName));

        if (TopK < 1)
            throw new ArgumentOutOfRangeException(nameof(TopK), "TopK must be at least 1.");

        if (MessageHistoryCount < 1)
            throw new ArgumentOutOfRangeException(nameof(MessageHistoryCount), "MessageHistoryCount must be at least 1.");

        if (IndexType == IndexType.Hybrid && string.IsNullOrWhiteSpace(FulltextIndexName))
            throw new ArgumentException("FulltextIndexName is required when IndexType is Hybrid.", nameof(FulltextIndexName));

        if (IndexType is IndexType.Vector or IndexType.Hybrid && EmbeddingGenerator is null)
            throw new ArgumentException($"EmbeddingGenerator is required when IndexType is {IndexType}.", nameof(EmbeddingGenerator));
    }

    /// <summary>
    /// Returns the effective FilterStopWords value (defaults based on index type).
    /// </summary>
    internal bool EffectiveFilterStopWords => FilterStopWords ?? (IndexType == IndexType.Fulltext);
}
