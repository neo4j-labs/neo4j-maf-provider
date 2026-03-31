using Microsoft.Extensions.AI;
using Moq;

namespace Neo4j.AgentFramework.GraphRAG.Tests;

public class Neo4jContextProviderOptionsTests
{
    private static IEmbeddingGenerator<string, Embedding<float>> MockEmbedder()
        => new Mock<IEmbeddingGenerator<string, Embedding<float>>>().Object;

    [Fact]
    public void Validate_WithValidVectorConfig_DoesNotThrow()
    {
        var options = new Neo4jContextProviderOptions
        {
            IndexName = "myIndex",
            IndexType = IndexType.Vector,
            EmbeddingGenerator = MockEmbedder()
        };

        options.Validate(); // should not throw
    }

    [Fact]
    public void Validate_WithValidFulltextConfig_DoesNotThrow()
    {
        var options = new Neo4jContextProviderOptions
        {
            IndexName = "myFulltextIndex",
            IndexType = IndexType.Fulltext
        };

        options.Validate(); // should not throw
    }

    [Fact]
    public void Validate_WithValidHybridConfig_DoesNotThrow()
    {
        var options = new Neo4jContextProviderOptions
        {
            IndexName = "vectorIdx",
            IndexType = IndexType.Hybrid,
            FulltextIndexName = "fulltextIdx",
            EmbeddingGenerator = MockEmbedder()
        };

        options.Validate(); // should not throw
    }

    [Fact]
    public void Validate_MissingIndexName_Throws()
    {
        var options = new Neo4jContextProviderOptions
        {
            IndexName = "",
            IndexType = IndexType.Fulltext
        };

        Assert.Throws<ArgumentException>(() => options.Validate());
    }

    [Fact]
    public void Validate_VectorWithoutEmbedder_Throws()
    {
        var options = new Neo4jContextProviderOptions
        {
            IndexName = "myIndex",
            IndexType = IndexType.Vector,
            EmbeddingGenerator = null
        };

        Assert.Throws<ArgumentException>(() => options.Validate());
    }

    [Fact]
    public void Validate_HybridWithoutFulltextIndex_Throws()
    {
        var options = new Neo4jContextProviderOptions
        {
            IndexName = "vectorIdx",
            IndexType = IndexType.Hybrid,
            EmbeddingGenerator = MockEmbedder()
        };

        Assert.Throws<ArgumentException>(() => options.Validate());
    }

    [Fact]
    public void Validate_HybridWithoutEmbedder_Throws()
    {
        var options = new Neo4jContextProviderOptions
        {
            IndexName = "vectorIdx",
            IndexType = IndexType.Hybrid,
            FulltextIndexName = "fulltextIdx"
        };

        Assert.Throws<ArgumentException>(() => options.Validate());
    }

    [Fact]
    public void Validate_TopKZero_Throws()
    {
        var options = new Neo4jContextProviderOptions
        {
            IndexName = "idx",
            IndexType = IndexType.Fulltext,
            TopK = 0
        };

        Assert.Throws<ArgumentOutOfRangeException>(() => options.Validate());
    }

    [Fact]
    public void Validate_MessageHistoryCountZero_Throws()
    {
        var options = new Neo4jContextProviderOptions
        {
            IndexName = "idx",
            IndexType = IndexType.Fulltext,
            MessageHistoryCount = 0
        };

        Assert.Throws<ArgumentOutOfRangeException>(() => options.Validate());
    }

    [Fact]
    public void DefaultValues_AreCorrect()
    {
        var options = new Neo4jContextProviderOptions { IndexName = "idx" };

        Assert.Equal(IndexType.Vector, options.IndexType);
        Assert.Equal(5, options.TopK);
        Assert.Equal(10, options.MessageHistoryCount);
        Assert.Null(options.FulltextIndexName);
        Assert.Null(options.RetrievalQuery);
        Assert.Null(options.FilterStopWords);
        Assert.Null(options.EmbeddingGenerator);
    }

    [Fact]
    public void EffectiveFilterStopWords_DefaultsTrueForFulltext()
    {
        var options = new Neo4jContextProviderOptions
        {
            IndexName = "idx",
            IndexType = IndexType.Fulltext
        };

        Assert.True(options.EffectiveFilterStopWords);
    }

    [Fact]
    public void EffectiveFilterStopWords_DefaultsFalseForVector()
    {
        var options = new Neo4jContextProviderOptions
        {
            IndexName = "idx",
            IndexType = IndexType.Vector,
            EmbeddingGenerator = MockEmbedder()
        };

        Assert.False(options.EffectiveFilterStopWords);
    }

    [Fact]
    public void EffectiveFilterStopWords_RespectsExplicitValue()
    {
        var options = new Neo4jContextProviderOptions
        {
            IndexName = "idx",
            IndexType = IndexType.Fulltext,
            FilterStopWords = false
        };

        Assert.False(options.EffectiveFilterStopWords);
    }
}
