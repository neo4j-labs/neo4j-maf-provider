using Neo4j.Driver;

namespace Neo4j.AgentFramework.GraphRAG.Retrieval;

/// <summary>
/// Retriever using fulltext search over Neo4j fulltext indexes.
/// Executes Cypher queries directly against the Neo4j driver.
/// </summary>
internal sealed class FulltextRetriever : IRetriever
{
    private readonly IDriver _driver;
    private readonly string _indexName;
    private readonly string? _retrievalQuery;
    private readonly bool _filterStopWords;

    public FulltextRetriever(
        IDriver driver,
        string indexName,
        string? retrievalQuery = null,
        bool filterStopWords = true)
    {
        _driver = driver;
        _indexName = indexName;
        _retrievalQuery = retrievalQuery;
        _filterStopWords = filterStopWords;
    }

    public async Task<RetrieverResult> SearchAsync(string queryText, int topK, CancellationToken cancellationToken = default)
    {
        var searchText = _filterStopWords
            ? StopWords.ExtractKeywords(queryText)
            : queryText;

        if (string.IsNullOrWhiteSpace(searchText))
            return new RetrieverResult([]);

        string cypher;
        if (_retrievalQuery is not null)
        {
            // Double LIMIT: once after fulltext search, once after graph enrichment
            cypher = $"""
                CALL db.index.fulltext.queryNodes($index_name, $query)
                YIELD node, score
                WITH node, score
                ORDER BY score DESC
                LIMIT $top_k
                {_retrievalQuery}
                LIMIT $top_k
                """;
        }
        else
        {
            cypher = """
                CALL db.index.fulltext.queryNodes($index_name, $query)
                YIELD node, score
                WITH node, score
                ORDER BY score DESC
                LIMIT $top_k
                RETURN node, score
                """;
        }

        var parameters = new Dictionary<string, object?>
        {
            ["index_name"] = _indexName,
            ["query"] = searchText,
            ["top_k"] = topK
        };

        var (records, _, _) = await _driver.ExecutableQuery(cypher)
            .WithParameters(parameters)
            .WithConfig(new QueryConfig(routing: RoutingControl.Readers))
            .ExecuteAsync(cancellationToken)
            .ConfigureAwait(false);

        var items = records.Select(FormatRecord).ToList();
        return new RetrieverResult(items);
    }

    private static RetrieverResultItem FormatRecord(IRecord record)
    {
        if (record.Keys.Contains("text"))
        {
            // Graph-enriched result: retrieval_query returns named columns
            return FormatCypherResult(record);
        }

        // Standard result: node + score
        var node = record["node"].As<INode>();
        var score = record["score"].As<double>();
        var content = node.Properties.TryGetValue("text", out var text)
            ? text?.ToString() ?? ""
            : node.Properties.TryGetValue("content", out var c)
                ? c?.ToString() ?? ""
                : node.ToString()!;

        return new RetrieverResultItem(content, new Dictionary<string, object?> { ["score"] = score });
    }

    internal static RetrieverResultItem FormatCypherResult(IRecord record)
    {
        var data = record.Keys.ToDictionary<string, string, object?>(k => k, k => record[k]);

        // Extract text content
        string content;
        if (data.Remove("text", out var textVal) && textVal is not null)
        {
            content = textVal.ToString()!;
        }
        else
        {
            // Fallback: prefer first string value, then any non-null value
            content = (data.Values.FirstOrDefault(v => v is string) ??
                       data.Values.FirstOrDefault(v => v is not null))?.ToString() ?? "";
        }

        return new RetrieverResultItem(content, data.Count > 0 ? data! : null);
    }
}
