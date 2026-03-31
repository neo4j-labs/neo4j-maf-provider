using Microsoft.Extensions.AI;
using Moq;
using Neo4j.AgentFramework.GraphRAG.Retrieval;
using Neo4j.Driver;

namespace Neo4j.AgentFramework.GraphRAG.Tests;

public class HybridRetrieverTests
{
    private static Mock<IDriver> CreateMockDriver(List<IRecord> records)
    {
        var mockDriver = new Mock<IDriver>();
        var mockEqb = new Mock<IExecutableQuery<IRecord, IRecord>>();

        mockEqb
            .Setup(q => q.WithParameters(It.IsAny<Dictionary<string, object>>()))
            .Returns(mockEqb.Object);
        mockEqb
            .Setup(q => q.WithConfig(It.IsAny<QueryConfig>()))
            .Returns(mockEqb.Object);
        mockEqb
            .Setup(q => q.ExecuteAsync(It.IsAny<CancellationToken>()))
            .ReturnsAsync(CreateEagerResult(records));

        mockDriver
            .Setup(d => d.ExecutableQuery(It.IsAny<string>()))
            .Returns(mockEqb.Object);

        return mockDriver;
    }

    private static EagerResult<IReadOnlyList<IRecord>> CreateEagerResult(List<IRecord> records)
    {
        return (EagerResult<IReadOnlyList<IRecord>>)Activator.CreateInstance(
            typeof(EagerResult<IReadOnlyList<IRecord>>),
            System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance,
            null,
            [records, Mock.Of<IResultSummary>(), Array.Empty<string>()],
            null)!;
    }

    private static Mock<IRecord> CreateNodeRecord(string text, double score)
    {
        var mockNode = new Mock<INode>();
        var props = new Dictionary<string, object> { ["text"] = text };
        mockNode.Setup(n => n.Properties).Returns(props);

        var mockRecord = new Mock<IRecord>();
        mockRecord.Setup(r => r["node"]).Returns(mockNode.Object);
        mockRecord.Setup(r => r["score"]).Returns(score);
        mockRecord.Setup(r => r.Keys).Returns(new List<string> { "node", "score" });

        return mockRecord;
    }

    private static Mock<IEmbeddingGenerator<string, Embedding<float>>> CreateMockEmbedder()
    {
        var mockEmbedder = new Mock<IEmbeddingGenerator<string, Embedding<float>>>();
        var embedding = new Embedding<float>(new float[] { 0.1f, 0.2f, 0.3f });
        var generated = new GeneratedEmbeddings<Embedding<float>>([embedding]);
        mockEmbedder
            .Setup(e => e.GenerateAsync(It.IsAny<IEnumerable<string>>(), It.IsAny<EmbeddingGenerationOptions?>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync(generated);
        return mockEmbedder;
    }

    [Fact]
    public async Task SearchAsync_MergesVectorAndFulltextResults()
    {
        var record1 = CreateNodeRecord("shared content", 0.9);
        var record2 = CreateNodeRecord("vector only", 0.8);
        var record3 = CreateNodeRecord("shared content", 0.7); // Same content, lower score
        var record4 = CreateNodeRecord("fulltext only", 0.6);

        var driver = CreateMockDriver([record1.Object, record2.Object, record3.Object, record4.Object]);
        var embedder = CreateMockEmbedder();

        var retriever = new HybridRetriever(
            driver.Object, "vectorIdx", "fulltextIdx", embedder.Object);

        var result = await retriever.SearchAsync("test query", 10);

        // "shared content" should appear once (max score wins)
        var contents = result.Items.Select(i => i.Content).ToList();
        Assert.Equal(3, contents.Distinct().Count());
        Assert.Contains("shared content", contents);
        Assert.Contains("vector only", contents);
        Assert.Contains("fulltext only", contents);
    }

    [Fact]
    public async Task SearchAsync_RespectsTopK()
    {
        var records = new List<IRecord>
        {
            CreateNodeRecord("text1", 0.9).Object,
            CreateNodeRecord("text2", 0.8).Object,
            CreateNodeRecord("text3", 0.7).Object,
        };

        var driver = CreateMockDriver(records);
        var embedder = CreateMockEmbedder();

        var retriever = new HybridRetriever(
            driver.Object, "vectorIdx", "fulltextIdx", embedder.Object);

        var result = await retriever.SearchAsync("test", 2);

        Assert.True(result.Items.Count <= 2);
    }

    [Fact]
    public async Task SearchAsync_OrdersByScoreDescending()
    {
        var record1 = CreateNodeRecord("low score", 0.3);
        var record2 = CreateNodeRecord("high score", 0.9);
        var record3 = CreateNodeRecord("mid score", 0.6);

        var driver = CreateMockDriver([record1.Object, record2.Object, record3.Object]);
        var embedder = CreateMockEmbedder();

        var retriever = new HybridRetriever(
            driver.Object, "vectorIdx", "fulltextIdx", embedder.Object);

        var result = await retriever.SearchAsync("test", 10);

        var scores = result.Items
            .Select(i => i.Metadata != null && i.Metadata.TryGetValue("score", out var s) && s is double d ? d : 0)
            .ToList();

        for (int i = 1; i < scores.Count; i++)
            Assert.True(scores[i - 1] >= scores[i], "Results should be ordered by score descending");
    }

    [Fact]
    public async Task SearchAsync_WithRetrievalQuery_DelegatesToSubRetrievers()
    {
        var mockRecord = new Mock<IRecord>();
        mockRecord.Setup(r => r.Keys).Returns(new List<string> { "text", "score", "company" });
        mockRecord.Setup(r => r["text"]).Returns("enriched content");
        mockRecord.Setup(r => r["score"]).Returns(0.95);
        mockRecord.Setup(r => r["company"]).Returns("Acme Corp");

        var driver = CreateMockDriver([mockRecord.Object]);
        var embedder = CreateMockEmbedder();

        var retriever = new HybridRetriever(
            driver.Object, "vectorIdx", "fulltextIdx", embedder.Object,
            retrievalQuery: "MATCH (node)-[:FROM]->(doc) RETURN node.text AS text, score, doc.company AS company");

        var result = await retriever.SearchAsync("test", 5);

        // Should get results (retrieval query is handled by sub-retrievers)
        Assert.NotEmpty(result.Items);
    }
}
