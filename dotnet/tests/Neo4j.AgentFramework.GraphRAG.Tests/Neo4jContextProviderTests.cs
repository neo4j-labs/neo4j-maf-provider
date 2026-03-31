using Microsoft.Extensions.AI;
using Moq;
using Neo4j.AgentFramework.GraphRAG.Retrieval;
using Neo4j.Driver;

namespace Neo4j.AgentFramework.GraphRAG.Tests;

public class Neo4jContextProviderTests
{
    [Fact]
    public void Constructor_ValidatesOptions()
    {
        var mockDriver = new Mock<IDriver>();
        var options = new Neo4jContextProviderOptions
        {
            IndexName = "",
            IndexType = IndexType.Fulltext
        };

        Assert.Throws<ArgumentException>(() => new Neo4jContextProvider(mockDriver.Object, options));
    }

    [Fact]
    public void Constructor_ThrowsOnNullDriver()
    {
        var options = new Neo4jContextProviderOptions
        {
            IndexName = "idx",
            IndexType = IndexType.Fulltext
        };

        Assert.Throws<ArgumentNullException>(() => new Neo4jContextProvider(null!, options));
    }

    [Fact]
    public void Constructor_ThrowsOnNullOptions()
    {
        var mockDriver = new Mock<IDriver>();
        Assert.Throws<ArgumentNullException>(() => new Neo4jContextProvider(mockDriver.Object, null!));
    }

    [Fact]
    public void Constructor_AcceptsValidFulltextConfig()
    {
        var mockDriver = new Mock<IDriver>();
        var options = new Neo4jContextProviderOptions
        {
            IndexName = "myIndex",
            IndexType = IndexType.Fulltext
        };

        var provider = new Neo4jContextProvider(mockDriver.Object, options);
        Assert.NotNull(provider);
    }

    [Fact]
    public void Constructor_AcceptsValidVectorConfig()
    {
        var mockDriver = new Mock<IDriver>();
        var mockEmbedder = new Mock<IEmbeddingGenerator<string, Embedding<float>>>();
        var options = new Neo4jContextProviderOptions
        {
            IndexName = "myIndex",
            IndexType = IndexType.Vector,
            EmbeddingGenerator = mockEmbedder.Object
        };

        var provider = new Neo4jContextProvider(mockDriver.Object, options);
        Assert.NotNull(provider);
    }

    [Fact]
    public void Constructor_AcceptsValidHybridConfig()
    {
        var mockDriver = new Mock<IDriver>();
        var mockEmbedder = new Mock<IEmbeddingGenerator<string, Embedding<float>>>();
        var options = new Neo4jContextProviderOptions
        {
            IndexName = "vectorIdx",
            IndexType = IndexType.Hybrid,
            FulltextIndexName = "fulltextIdx",
            EmbeddingGenerator = mockEmbedder.Object
        };

        var provider = new Neo4jContextProvider(mockDriver.Object, options);
        Assert.NotNull(provider);
    }

    [Fact]
    public void Constructor_VectorRequiresEmbeddingGenerator()
    {
        var mockDriver = new Mock<IDriver>();
        var options = new Neo4jContextProviderOptions
        {
            IndexName = "myIndex",
            IndexType = IndexType.Vector,
            EmbeddingGenerator = null
        };

        Assert.Throws<ArgumentException>(() => new Neo4jContextProvider(mockDriver.Object, options));
    }

    [Fact]
    public void Constructor_HybridRequiresFulltextIndexName()
    {
        var mockDriver = new Mock<IDriver>();
        var mockEmbedder = new Mock<IEmbeddingGenerator<string, Embedding<float>>>();
        var options = new Neo4jContextProviderOptions
        {
            IndexName = "vectorIdx",
            IndexType = IndexType.Hybrid,
            EmbeddingGenerator = mockEmbedder.Object,
            FulltextIndexName = null
        };

        Assert.Throws<ArgumentException>(() => new Neo4jContextProvider(mockDriver.Object, options));
    }

    [Fact]
    public async Task DisposeAsync_DoesNotDisposeInjectedDriver()
    {
        var mockDriver = new Mock<IDriver>();

        var options = new Neo4jContextProviderOptions
        {
            IndexName = "idx",
            IndexType = IndexType.Fulltext
        };

        var provider = new Neo4jContextProvider(mockDriver.Object, options);
        await provider.DisposeAsync();

        mockDriver.Verify(d => d.DisposeAsync(), Times.Never);
    }
}
