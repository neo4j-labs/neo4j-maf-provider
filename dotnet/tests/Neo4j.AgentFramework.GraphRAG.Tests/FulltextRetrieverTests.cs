using Moq;
using Neo4j.AgentFramework.GraphRAG.Retrieval;
using Neo4j.Driver;

namespace Neo4j.AgentFramework.GraphRAG.Tests;

public class FulltextRetrieverTests
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

    [Fact]
    public async Task SearchAsync_ReturnsFormattedResults()
    {
        var record = CreateNodeRecord("test content", 0.95);
        var driver = CreateMockDriver([record.Object]);

        var retriever = new FulltextRetriever(driver.Object, "myIndex");

        var result = await retriever.SearchAsync("test query", 5);

        Assert.Single(result.Items);
        Assert.Equal("test content", result.Items[0].Content);
        Assert.Equal(0.95, result.Items[0].Metadata!["score"]);
    }

    [Fact]
    public async Task SearchAsync_WithStopWordFiltering_FiltersQuery()
    {
        var record = CreateNodeRecord("engine doc", 0.9);
        var driver = CreateMockDriver([record.Object]);

        var retriever = new FulltextRetriever(driver.Object, "myIndex", filterStopWords: true);

        var result = await retriever.SearchAsync("what is the engine", 5);

        Assert.Single(result.Items);
        driver.Verify(d => d.ExecutableQuery(It.IsAny<string>()), Times.Once);
    }

    [Fact]
    public async Task SearchAsync_AllStopWords_ReturnsEmpty()
    {
        var driver = CreateMockDriver([]);

        var retriever = new FulltextRetriever(driver.Object, "myIndex", filterStopWords: true);

        var result = await retriever.SearchAsync("what is the a", 5);

        Assert.Empty(result.Items);
        driver.Verify(d => d.ExecutableQuery(It.IsAny<string>()), Times.Never);
    }

    [Fact]
    public async Task SearchAsync_WithoutStopWordFiltering_PassesFullQuery()
    {
        var record = CreateNodeRecord("result", 0.8);
        var driver = CreateMockDriver([record.Object]);

        var retriever = new FulltextRetriever(driver.Object, "myIndex", filterStopWords: false);

        var result = await retriever.SearchAsync("what is the engine", 5);

        Assert.Single(result.Items);
        driver.Verify(d => d.ExecutableQuery(It.IsAny<string>()), Times.Once);
    }

    [Fact]
    public async Task SearchAsync_WithRetrievalQuery_UsesCypherResult()
    {
        var mockRecord = new Mock<IRecord>();
        mockRecord.Setup(r => r.Keys).Returns(new List<string> { "text", "score", "title" });
        mockRecord.Setup(r => r["text"]).Returns("enriched content");
        mockRecord.Setup(r => r["score"]).Returns(0.92);
        mockRecord.Setup(r => r["title"]).Returns("My Document");

        var driver = CreateMockDriver([mockRecord.Object]);

        var retriever = new FulltextRetriever(
            driver.Object,
            "myIndex",
            retrievalQuery: "MATCH (node)-[:FROM]->(doc) RETURN node.text AS text, score, doc.title AS title");

        var result = await retriever.SearchAsync("search query", 5);

        Assert.Single(result.Items);
        Assert.Equal("enriched content", result.Items[0].Content);
        Assert.Equal("My Document", result.Items[0].Metadata!["title"]);
    }

    [Fact]
    public void FormatCypherResult_ExtractsTextAndMetadata()
    {
        var mockRecord = new Mock<IRecord>();
        mockRecord.Setup(r => r.Keys).Returns(new List<string> { "text", "score", "category" });
        mockRecord.Setup(r => r["text"]).Returns("document text");
        mockRecord.Setup(r => r["score"]).Returns(0.88);
        mockRecord.Setup(r => r["category"]).Returns("financial");

        var item = FulltextRetriever.FormatCypherResult(mockRecord.Object);

        Assert.Equal("document text", item.Content);
        Assert.Equal(0.88, item.Metadata!["score"]);
        Assert.Equal("financial", item.Metadata["category"]);
        Assert.False(item.Metadata.ContainsKey("text"));
    }

    [Fact]
    public void FormatCypherResult_NoTextColumn_FallsBackToFirstString()
    {
        var mockRecord = new Mock<IRecord>();
        mockRecord.Setup(r => r.Keys).Returns(new List<string> { "score", "description" });
        mockRecord.Setup(r => r["score"]).Returns(0.75);
        mockRecord.Setup(r => r["description"]).Returns("fallback content");
        mockRecord.Setup(r => r.Values).Returns(
            new Dictionary<string, object> { ["score"] = 0.75, ["description"] = "fallback content" });

        var item = FulltextRetriever.FormatCypherResult(mockRecord.Object);

        Assert.Equal("fallback content", item.Content);
    }

    [Fact]
    public async Task SearchAsync_EmptyQuery_ReturnsEmpty()
    {
        var driver = CreateMockDriver([]);
        var retriever = new FulltextRetriever(driver.Object, "myIndex", filterStopWords: false);

        var result = await retriever.SearchAsync("", 5);

        Assert.Empty(result.Items);
        driver.Verify(d => d.ExecutableQuery(It.IsAny<string>()), Times.Never);
    }
}
