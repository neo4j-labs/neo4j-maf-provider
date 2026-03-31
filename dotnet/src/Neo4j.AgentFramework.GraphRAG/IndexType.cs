namespace Neo4j.AgentFramework.GraphRAG;

/// <summary>
/// The type of search to perform against Neo4j indexes.
/// </summary>
public enum IndexType
{
    /// <summary>Semantic similarity search using embeddings.</summary>
    Vector,

    /// <summary>Keyword matching using BM25 scoring.</summary>
    Fulltext,

    /// <summary>Combined vector and fulltext search.</summary>
    Hybrid
}
