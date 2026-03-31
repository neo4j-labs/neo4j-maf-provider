namespace Neo4j.AgentFramework.GraphRAG;

/// <summary>
/// Loads Neo4j connection settings from environment variables.
/// </summary>
public sealed class Neo4jSettings
{
    /// <summary>Neo4j connection URI.</summary>
    public string? Uri { get; } = Environment.GetEnvironmentVariable("NEO4J_URI");

    /// <summary>Neo4j username.</summary>
    public string? Username { get; } = Environment.GetEnvironmentVariable("NEO4J_USERNAME");

    /// <summary>Neo4j password.</summary>
    public string? Password { get; } = Environment.GetEnvironmentVariable("NEO4J_PASSWORD");

    /// <summary>Vector index name. Defaults to "chunkEmbeddings".</summary>
    public string VectorIndexName { get; } =
        Environment.GetEnvironmentVariable("NEO4J_VECTOR_INDEX_NAME") ?? "chunkEmbeddings";

    /// <summary>Fulltext index name. Defaults to "search_chunks".</summary>
    public string FulltextIndexName { get; } =
        Environment.GetEnvironmentVariable("NEO4J_FULLTEXT_INDEX_NAME") ?? "search_chunks";

    /// <summary>Whether all required connection fields are set.</summary>
    public bool IsConfigured =>
        !string.IsNullOrWhiteSpace(Uri) &&
        !string.IsNullOrWhiteSpace(Username) &&
        !string.IsNullOrWhiteSpace(Password);
}
