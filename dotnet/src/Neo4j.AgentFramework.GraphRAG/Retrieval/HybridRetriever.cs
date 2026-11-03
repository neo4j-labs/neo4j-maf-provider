using Microsoft.Extensions.AI;
using Neo4j.Driver;

namespace Neo4j.AgentFramework.GraphRAG.Retrieval;

/// <summary>
/// Retriever combining vector and fulltext search.
/// Runs both queries concurrently, scales each one's scores by its own maximum, and merges results
/// by content, taking the max scaled score for duplicate text chunks.
/// </summary>
/// <remarks>
/// Vector index scores lie between 0 and 1, while fulltext (Lucene) scores are unbounded, so raw scores
/// from the two indexes aren't comparable. Dividing each result list by its maximum, as neo4j-graphrag's
/// hybrid query does, keeps a strong match from either index from being pushed out by the other's scale.
/// </remarks>
internal sealed class HybridRetriever : IRetriever
{
    private readonly VectorRetriever _vectorRetriever;
    private readonly FulltextRetriever _fulltextRetriever;

    public HybridRetriever(
        IDriver driver,
        string vectorIndexName,
        string fulltextIndexName,
        IEmbeddingGenerator<string, Embedding<float>> embeddingGenerator,
        string? retrievalQuery = null,
        bool filterStopWords = false)
    {
        _vectorRetriever = new VectorRetriever(driver, vectorIndexName, embeddingGenerator, retrievalQuery);
        _fulltextRetriever = new FulltextRetriever(driver, fulltextIndexName, retrievalQuery, filterStopWords);
    }

    public async Task<RetrieverResult> SearchAsync(string queryText, int topK, CancellationToken cancellationToken = default)
    {
        // Run vector and fulltext searches concurrently
        var vectorTask = _vectorRetriever.SearchAsync(queryText, topK, cancellationToken);
        var fulltextTask = _fulltextRetriever.SearchAsync(queryText, topK, cancellationToken);

        await Task.WhenAll(vectorTask, fulltextTask).ConfigureAwait(false);

        var vectorResults = await vectorTask.ConfigureAwait(false);
        var fulltextResults = await fulltextTask.ConfigureAwait(false);

        // Merge results: scale each search to [0, 1], combine by content, take max score
        var merged = new Dictionary<string, RetrieverResultItem>();

        foreach (var item in ScaleToMaximum(vectorResults.Items).Concat(ScaleToMaximum(fulltextResults.Items)))
        {
            var key = item.Content;
            if (merged.TryGetValue(key, out var existing))
            {
                var existingScore = GetScore(existing);
                var newScore = GetScore(item);
                if (newScore > existingScore)
                    merged[key] = item;
            }
            else
            {
                merged[key] = item;
            }
        }

        var items = merged.Values
            .OrderByDescending(GetScore)
            .Take(topK)
            .ToList();

        return new RetrieverResult(items);
    }

    /// <summary>
    /// Divides every score in <paramref name="items"/> by the list's highest score, so the best result scores 1.
    /// A list without a positive score is returned unchanged.
    /// </summary>
    private static IEnumerable<RetrieverResultItem> ScaleToMaximum(IReadOnlyList<RetrieverResultItem> items)
    {
        var max = items.Count == 0 ? 0 : items.Max(GetScore);
        if (max <= 0)
            return items;

        return items.Select(item =>
        {
            if (item.Metadata is null || item.Metadata.GetValueOrDefault("score") is not double score)
                return item;

            var metadata = new Dictionary<string, object?>(item.Metadata) { ["score"] = score / max };
            return item with { Metadata = metadata };
        });
    }

    private static double GetScore(RetrieverResultItem item)
    {
        if (item.Metadata?.TryGetValue("score", out var score) == true && score is double d)
            return d;
        return 0;
    }
}
