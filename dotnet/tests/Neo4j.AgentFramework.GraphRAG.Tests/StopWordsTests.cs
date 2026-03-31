namespace Neo4j.AgentFramework.GraphRAG.Tests;

public class StopWordsTests
{
    [Fact]
    public void ExtractKeywords_RemovesStopWords()
    {
        var result = StopWords.ExtractKeywords("What maintenance issues involve engine vibration?");
        Assert.Equal("maintenance issues engine vibration", result);
    }

    [Fact]
    public void ExtractKeywords_IsCaseInsensitive()
    {
        var result = StopWords.ExtractKeywords("TELL me ABOUT the ENGINE");
        Assert.Equal("engine", result);
    }

    [Fact]
    public void ExtractKeywords_RemovesSingleCharWords()
    {
        var result = StopWords.ExtractKeywords("a b c engine d");
        Assert.Equal("engine", result);
    }

    [Fact]
    public void ExtractKeywords_AllStopWords_ReturnsEmpty()
    {
        var result = StopWords.ExtractKeywords("what is the a");
        Assert.Equal("", result);
    }

    [Fact]
    public void ExtractKeywords_EmptyInput_ReturnsEmpty()
    {
        var result = StopWords.ExtractKeywords("");
        Assert.Equal("", result);
    }

    [Fact]
    public void ExtractKeywords_PreservesMultipleKeywords()
    {
        var result = StopWords.ExtractKeywords("company products financial risks");
        Assert.Equal("company products financial risks", result);
    }
}
