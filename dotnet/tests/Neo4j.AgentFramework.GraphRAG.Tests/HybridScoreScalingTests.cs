using Microsoft.Extensions.AI;
using Moq;
using Neo4j.AgentFramework.GraphRAG.Retrieval;
using Neo4j.Driver;

namespace Neo4j.AgentFramework.GraphRAG.Tests;

/// <summary>
/// Vector index scores lie between 0 and 1, while full-text (Lucene) scores are unbounded, so the two can't be
/// compared raw. These tests pin that hybrid search scales each search's scores by its own maximum before merging,
/// as neo4j-graphrag's hybrid query does.
/// </summary>
public class HybridScoreScalingTests
{
    private static Mock<IDriver> CreateDriver(List<IRecord> vectorRecords, List<IRecord> fulltextRecords)
    {
        var driver = new Mock<IDriver>();
        driver
            .Setup(d => d.ExecutableQuery(It.IsAny<string>()))
            .Returns((string cypher) => CreateQuery(
                cypher.Contains("db.index.vector.queryNodes") ? vectorRecords : fulltextRecords).Object);
        return driver;
    }

    private static Mock<IExecutableQuery<IRecord, IRecord>> CreateQuery(List<IRecord> records)
    {
        var query = new Mock<IExecutableQuery<IRecord, IRecord>>();
        query.Setup(q => q.WithParameters(It.IsAny<Dictionary<string, object>>())).Returns(query.Object);
        query.Setup(q => q.WithConfig(It.IsAny<QueryConfig>())).Returns(query.Object);
        query.Setup(q => q.ExecuteAsync(It.IsAny<CancellationToken>())).ReturnsAsync(CreateEagerResult(records));
        return query;
    }

    private static EagerResult<IReadOnlyList<IRecord>> CreateEagerResult(List<IRecord> records) =>
        (EagerResult<IReadOnlyList<IRecord>>)Activator.CreateInstance(
            typeof(EagerResult<IReadOnlyList<IRecord>>),
            System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance,
            null,
            [records, Mock.Of<IResultSummary>(), Array.Empty<string>()],
            null)!;

    private static IRecord Node(string text, double score)
    {
        var node = new Mock<INode>();
        node.Setup(n => n.Properties).Returns(new Dictionary<string, object> { ["text"] = text });
        var record = new Mock<IRecord>();
        record.Setup(r => r["node"]).Returns(node.Object);
        record.Setup(r => r["score"]).Returns(score);
        record.Setup(r => r.Keys).Returns(new List<string> { "node", "score" });
        return record.Object;
    }

    private static IEmbeddingGenerator<string, Embedding<float>> Embedder()
    {
        var embedder = new Mock<IEmbeddingGenerator<string, Embedding<float>>>();
        embedder
            .Setup(e => e.GenerateAsync(It.IsAny<IEnumerable<string>>(), It.IsAny<EmbeddingGenerationOptions?>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync(new GeneratedEmbeddings<Embedding<float>>([new Embedding<float>(new float[] { 0.1f, 0.2f, 0.3f })]));
        return embedder.Object;
    }

    private static double Score(RetrieverResultItem item) =>
        item.Metadata is not null && item.Metadata.TryGetValue("score", out var s) && s is double d ? d : double.NaN;

    [Fact]
    public async Task SearchAsync_KeepsTheBestVectorMatch_WhenFulltextScoresAreLarger()
    {
        // The best vector match scores 0.95; three keyword matches score 8, 6 and 4 on Lucene's open scale.
        var driver = CreateDriver(
            [Node("best vector match", 0.95)],
            [Node("keyword match 1", 8.0), Node("keyword match 2", 6.0), Node("keyword match 3", 4.0)]);
        var retriever = new HybridRetriever(driver.Object, "vectorIdx", "fulltextIdx", Embedder());

        var result = await retriever.SearchAsync("question", 3);

        Assert.Contains("best vector match", result.Items.Select(i => i.Content));
    }

    [Fact]
    public async Task SearchAsync_ScalesEachSearchToItsMaximum()
    {
        var driver = CreateDriver(
            [Node("vector a", 0.9), Node("vector b", 0.45)],
            [Node("keyword a", 10.0), Node("keyword b", 5.0)]);
        var retriever = new HybridRetriever(driver.Object, "vectorIdx", "fulltextIdx", Embedder());

        var result = await retriever.SearchAsync("question", 10);
        var scores = result.Items.ToDictionary(i => i.Content, Score);

        Assert.Equal(1.0, scores["vector a"], 6);
        Assert.Equal(0.5, scores["vector b"], 6);
        Assert.Equal(1.0, scores["keyword a"], 6);
        Assert.Equal(0.5, scores["keyword b"], 6);
    }

    [Fact]
    public async Task SearchAsync_TakesTheHigherScaledScore_ForAPassageBothSearchesFind()
    {
        // "shared" is the top keyword match (10 of 10, so 1.0) but only half the best vector score (0.4 of 0.8).
        var driver = CreateDriver(
            [Node("vector top", 0.8), Node("shared", 0.4)],
            [Node("shared", 10.0)]);
        var retriever = new HybridRetriever(driver.Object, "vectorIdx", "fulltextIdx", Embedder());

        var result = await retriever.SearchAsync("question", 10);

        Assert.Equal(2, result.Items.Count);
        Assert.Equal(1.0, Score(result.Items.Single(i => i.Content == "shared")), 6);
    }

    [Fact]
    public async Task SearchAsync_LeavesScoresAlone_WhenASearchHasNoPositiveScore()
    {
        var driver = CreateDriver([Node("zero", 0.0)], []);
        var retriever = new HybridRetriever(driver.Object, "vectorIdx", "fulltextIdx", Embedder());

        var result = await retriever.SearchAsync("question", 10);

        Assert.Equal(0.0, Score(Assert.Single(result.Items)), 6);
    }
}
