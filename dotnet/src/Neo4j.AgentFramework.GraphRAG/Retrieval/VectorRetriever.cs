using Microsoft.Extensions.AI;
using Neo4j.Driver;

namespace Neo4j.AgentFramework.GraphRAG.Retrieval;

/// <summary>
/// Retriever using vector search over Neo4j vector indexes.
/// Embeds the query text and executes db.index.vector.queryNodes via Cypher.
/// </summary>
internal sealed class VectorRetriever : IRetriever
{
    private readonly IDriver _driver;
    private readonly string _indexName;
    private readonly string? _retrievalQuery;
    private readonly IEmbeddingGenerator<string, Embedding<float>> _embeddingGenerator;

    public VectorRetriever(
        IDriver driver,
        string indexName,
        IEmbeddingGenerator<string, Embedding<float>> embeddingGenerator,
        string? retrievalQuery = null)
    {
        _driver = driver;
        _indexName = indexName;
        _embeddingGenerator = embeddingGenerator;
        _retrievalQuery = retrievalQuery;
    }

    public async Task<RetrieverResult> SearchAsync(string queryText, int topK, CancellationToken cancellationToken = default)
    {
        var embedding = await _embeddingGenerator.GenerateVectorAsync(queryText, cancellationToken: cancellationToken)
            .ConfigureAwait(false);

        string cypher;
        if (_retrievalQuery is not null)
        {
            cypher = $"""
                CALL db.index.vector.queryNodes($index, $k, $embedding)
                YIELD node, score
                WITH node, score
                ORDER BY score DESC
                LIMIT $k
                {_retrievalQuery}
                LIMIT $k
                """;
        }
        else
        {
            cypher = """
                CALL db.index.vector.queryNodes($index, $k, $embedding)
                YIELD node, score
                WITH node, score
                ORDER BY score DESC
                LIMIT $k
                RETURN node, score
                """;
        }

        var parameters = new Dictionary<string, object?>
        {
            ["index"] = _indexName,
            ["k"] = topK,
            ["embedding"] = embedding.ToArray()
        };

        var (records, _, _) = await _driver.ExecutableQuery(cypher)
            .WithParameters(parameters)
            .WithConfig(new QueryConfig(routing: RoutingControl.Readers))
            .ExecuteAsync(cancellationToken)
            .ConfigureAwait(false);

        var items = records.Select(r =>
            _retrievalQuery is not null
                ? FulltextRetriever.FormatCypherResult(r)
                : FormatStandardResult(r)
        ).ToList();

        return new RetrieverResult(items);
    }

    private static RetrieverResultItem FormatStandardResult(IRecord record)
    {
        var node = record["node"].As<INode>();
        var score = record["score"].As<double>();
        var content = node.Properties.TryGetValue("text", out var text)
            ? text?.ToString() ?? ""
            : node.Properties.TryGetValue("content", out var c)
                ? c?.ToString() ?? ""
                : node.ToString()!;

        return new RetrieverResultItem(content, new Dictionary<string, object?> { ["score"] = score });
    }
}
