using Neo4j.AgentFramework.GraphRAG.Retrieval;

namespace Neo4j.AgentFramework.GraphRAG.Tests;

public class ResultFormattingTests
{
    [Fact]
    public void FormatResultItem_WithScoreAndContent()
    {
        var item = new RetrieverResultItem(
            "Some text content",
            new Dictionary<string, object?> { ["score"] = 0.892 });

        // Use reflection to test the private static method via the provider
        var formatted = InvokeFormatResultItem(item);

        Assert.Contains("[Score: 0.892]", formatted);
        Assert.Contains("Some text content", formatted);
    }

    [Fact]
    public void FormatResultItem_WithMetadataFields()
    {
        var item = new RetrieverResultItem(
            "Content here",
            new Dictionary<string, object?>
            {
                ["score"] = 0.85,
                ["company"] = "Acme Inc",
            });

        var formatted = InvokeFormatResultItem(item);

        Assert.Contains("[Score: 0.850]", formatted);
        Assert.Contains("[company: Acme Inc]", formatted);
        Assert.Contains("Content here", formatted);
    }

    [Fact]
    public void FormatResultItem_NullMetadataValues_AreSkipped()
    {
        var item = new RetrieverResultItem(
            "Content",
            new Dictionary<string, object?>
            {
                ["score"] = 0.5,
                ["empty_field"] = null,
            });

        var formatted = InvokeFormatResultItem(item);

        Assert.DoesNotContain("empty_field", formatted);
    }

    [Fact]
    public void FormatResultItem_ContentOnly()
    {
        var item = new RetrieverResultItem("Just content");

        var formatted = InvokeFormatResultItem(item);

        Assert.Equal("Just content", formatted);
    }

    // Helper: invoke the private FormatResultItem method via reflection
    private static string InvokeFormatResultItem(RetrieverResultItem item)
    {
        var method = typeof(Neo4jContextProvider).GetMethod(
            "FormatResultItem",
            System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static);
        return (string)method!.Invoke(null, [item])!;
    }
}
