using Microsoft.Extensions.AI;
using Moq;
using Neo4j.AgentFramework.GraphRAG.Retrieval;
using Neo4j.Driver;

namespace Neo4j.AgentFramework.GraphRAG.Tests;

public class VectorRetrieverTests
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

    private static Mock<IEmbeddingGenerator<string, Embedding<float>>> CreateMockEmbedder(float[] vector)
    {
        var mockEmbedder = new Mock<IEmbeddingGenerator<string, Embedding<float>>>();
        var embedding = new GeneratedEmbeddings<Embedding<float>>([new Embedding<float>(vector)]);

        mockEmbedder
            .Setup(e => e.GenerateAsync(
                It.IsAny<IEnumerable<string>>(),
                It.IsAny<EmbeddingGenerationOptions?>(),
                It.IsAny<CancellationToken>()))
            .ReturnsAsync(embedding);

        return mockEmbedder;
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

    [Fact]
    public async Task SearchAsync_EmbedsQueryAndReturnsResults()
    {
        var record = CreateNodeRecord("vector result", 0.97);
        var driver = CreateMockDriver([record.Object]);
        var embedder = CreateMockEmbedder([0.1f, 0.2f, 0.3f]);

        var retriever = new VectorRetriever(driver.Object, "vectorIndex", embedder.Object);

        var result = await retriever.SearchAsync("search query", 5);

        Assert.Single(result.Items);
        Assert.Equal("vector result", result.Items[0].Content);
        Assert.Equal(0.97, result.Items[0].Metadata!["score"]);

        embedder.Verify(e => e.GenerateAsync(
            It.IsAny<IEnumerable<string>>(),
            It.IsAny<EmbeddingGenerationOptions?>(),
            It.IsAny<CancellationToken>()), Times.Once);
    }

    [Fact]
    public async Task SearchAsync_WithRetrievalQuery_UsesCypherResult()
    {
        var mockRecord = new Mock<IRecord>();
        mockRecord.Setup(r => r.Keys).Returns(new List<string> { "text", "score", "source" });
        mockRecord.Setup(r => r["text"]).Returns("graph enriched");
        mockRecord.Setup(r => r["score"]).Returns(0.91);
        mockRecord.Setup(r => r["source"]).Returns("document.pdf");

        var driver = CreateMockDriver([mockRecord.Object]);
        var embedder = CreateMockEmbedder([0.1f, 0.2f]);

        var retriever = new VectorRetriever(
            driver.Object,
            "vectorIndex",
            embedder.Object,
            retrievalQuery: "MATCH (node)-[:FROM]->(doc) RETURN node.text AS text, score, doc.name AS source");

        var result = await retriever.SearchAsync("query", 5);

        Assert.Single(result.Items);
        Assert.Equal("graph enriched", result.Items[0].Content);
        Assert.Equal("document.pdf", result.Items[0].Metadata!["source"]);
    }

    [Fact]
    public async Task SearchAsync_MultipleResults_AllReturned()
    {
        var record1 = CreateNodeRecord("first", 0.95);
        var record2 = CreateNodeRecord("second", 0.85);
        var driver = CreateMockDriver([record1.Object, record2.Object]);
        var embedder = CreateMockEmbedder([0.1f]);

        var retriever = new VectorRetriever(driver.Object, "idx", embedder.Object);

        var result = await retriever.SearchAsync("query", 5);

        Assert.Equal(2, result.Items.Count);
        Assert.Equal("first", result.Items[0].Content);
        Assert.Equal("second", result.Items[1].Content);
    }

    [Fact]
    public async Task SearchAsync_NodeWithContentProperty_UsesContent()
    {
        var mockNode = new Mock<INode>();
        var props = new Dictionary<string, object> { ["content"] = "from content prop" };
        mockNode.Setup(n => n.Properties).Returns(props);

        var mockRecord = new Mock<IRecord>();
        mockRecord.Setup(r => r["node"]).Returns(mockNode.Object);
        mockRecord.Setup(r => r["score"]).Returns(0.8);
        mockRecord.Setup(r => r.Keys).Returns(new List<string> { "node", "score" });

        var driver = CreateMockDriver([mockRecord.Object]);
        var embedder = CreateMockEmbedder([0.1f]);

        var retriever = new VectorRetriever(driver.Object, "idx", embedder.Object);

        var result = await retriever.SearchAsync("query", 5);

        Assert.Equal("from content prop", result.Items[0].Content);
    }
}
