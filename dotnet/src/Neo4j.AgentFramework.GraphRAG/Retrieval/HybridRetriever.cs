using Microsoft.Extensions.AI;
using Neo4j.Driver;

namespace Neo4j.AgentFramework.GraphRAG.Retrieval;

/// <summary>
/// Retriever combining vector and fulltext search.
/// Runs both queries concurrently and merges results by content, taking the max score
/// for duplicate text chunks.
/// </summary>
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

        // Merge results: combine by content, take max score
        var merged = new Dictionary<string, RetrieverResultItem>();

        foreach (var item in vectorResults.Items.Concat(fulltextResults.Items))
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

    private static double GetScore(RetrieverResultItem item)
    {
        if (item.Metadata?.TryGetValue("score", out var score) == true && score is double d)
            return d;
        return 0;
    }
}
