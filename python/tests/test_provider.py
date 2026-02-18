"""
Tests for Neo4j Context Provider.

Tests the provider initialization and configuration validation.
"""

from unittest.mock import AsyncMock, PropertyMock, patch

import pytest
from agent_framework import AgentSession, Message, SessionContext
from neo4j_graphrag.types import RetrieverResult, RetrieverResultItem

from agent_framework_neo4j import Neo4jContextProvider, Neo4jSettings


class TestSettings:
    """Test Neo4jSettings."""

    def test_settings_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Settings should load from environment variables."""
        # Clear any existing env vars first
        monkeypatch.delenv("NEO4J_URI", raising=False)
        monkeypatch.delenv("NEO4J_USERNAME", raising=False)
        monkeypatch.delenv("NEO4J_PASSWORD", raising=False)

        monkeypatch.setenv("NEO4J_URI", "bolt://test:7687")
        monkeypatch.setenv("NEO4J_USERNAME", "testuser")
        monkeypatch.setenv("NEO4J_VECTOR_INDEX_NAME", "testindex")

        settings = Neo4jSettings()
        assert settings.uri == "bolt://test:7687"
        assert settings.username == "testuser"
        assert settings.vector_index_name == "testindex"

    def test_settings_has_defaults(self) -> None:
        """Settings should have default index names."""
        # Don't test uri/username/password as they may come from env
        settings = Neo4jSettings()
        assert settings.vector_index_name == "chunkEmbeddings"
        assert settings.fulltext_index_name == "chunkFulltext"


class TestProviderInit:
    """Test Neo4jContextProvider initialization."""

    def test_requires_index_name(self) -> None:
        """Provider should require index_name."""
        with pytest.raises(ValueError, match="index_name"):
            Neo4jContextProvider(
                index_type="fulltext",
            )

    def test_requires_embedder_for_vector_type(self) -> None:
        """Provider should require embedder when index_type is vector."""
        with pytest.raises(ValueError, match="embedder is required"):
            Neo4jContextProvider(
                index_name="test_index",
                index_type="vector",
            )

    def test_valid_fulltext_config(self) -> None:
        """Provider should accept valid fulltext configuration."""
        provider = Neo4jContextProvider(
            index_name="test_index",
            index_type="fulltext",
        )
        assert provider._index_name == "test_index"
        assert provider._index_type == "fulltext"
        assert provider._retrieval_query is None

    def test_valid_retrieval_query_config(self) -> None:
        """Provider should accept retrieval_query for graph enrichment."""
        provider = Neo4jContextProvider(
            index_name="test_index",
            index_type="fulltext",
            retrieval_query="RETURN node.text AS text, score",
        )
        assert provider._retrieval_query is not None
        assert "RETURN" in provider._retrieval_query

    def test_default_values(self) -> None:
        """Provider should have sensible defaults."""
        provider = Neo4jContextProvider(
            index_name="test_index",
            index_type="fulltext",
        )
        assert provider._top_k == 5
        assert provider._message_history_count == 10
        assert "Knowledge Graph Context" in provider._context_prompt

    def test_not_connected_initially(self) -> None:
        """Provider should not be connected before __aenter__."""
        provider = Neo4jContextProvider(
            index_name="test_index",
            index_type="fulltext",
        )
        assert not provider.is_connected

    def test_custom_context_prompt(self) -> None:
        """Provider should accept custom context prompt."""
        custom_prompt = "Custom prompt for testing"
        provider = Neo4jContextProvider(
            index_name="test_index",
            index_type="fulltext",
            context_prompt=custom_prompt,
        )
        assert provider._context_prompt == custom_prompt

    def test_message_history_count(self) -> None:
        """Provider should accept message_history_count."""
        provider = Neo4jContextProvider(
            index_name="test_index",
            index_type="fulltext",
            message_history_count=5,
        )
        assert provider._message_history_count == 5

    def test_top_k_validation(self) -> None:
        """Provider should validate top_k is positive."""
        with pytest.raises(ValueError, match="top_k must be at least 1"):
            Neo4jContextProvider(
                index_name="test_index",
                index_type="fulltext",
                top_k=0,
            )


class TestGraphEnrichment:
    """Test graph enrichment via retrieval_query."""

    def test_uses_custom_retrieval_query(self) -> None:
        """Provider should store custom retrieval query."""
        custom_query = """
        MATCH (node)-[:FROM_DOCUMENT]-(doc:Document)
        RETURN node.text AS text, score, doc.path AS source
        """
        provider = Neo4jContextProvider(
            index_name="test_index",
            index_type="fulltext",
            retrieval_query=custom_query,
        )
        assert "FROM_DOCUMENT" in provider._retrieval_query
        assert "doc.path AS source" in provider._retrieval_query

    def test_retrieval_query_patterns_from_workshop(self) -> None:
        """Test retrieval query patterns from the workshop examples."""
        company_risk_query = """
        MATCH (node)-[:FROM_DOCUMENT]-(doc:Document)-[:FILED]-(company:Company)
        OPTIONAL MATCH (company)-[:FACES_RISK]->(risk:RiskFactor)
        WITH node, score, company, collect(DISTINCT risk.name) as risks
        WHERE score IS NOT NULL
        RETURN node.text AS text, score, company.name AS company, risks
        ORDER BY score DESC
        """
        provider = Neo4jContextProvider(
            index_name="chunkEmbeddings",
            index_type="fulltext",
            retrieval_query=company_risk_query,
        )
        assert provider._retrieval_query is not None
        assert "FACES_RISK" in provider._retrieval_query
        assert "collect(DISTINCT risk.name)" in provider._retrieval_query


class TestBeforeRun:
    """Test the before_run method."""

    @pytest.mark.asyncio
    async def test_before_run_no_op_when_not_connected(self) -> None:
        """before_run should not add context when not connected."""
        provider = Neo4jContextProvider(
            index_name="test_index",
            index_type="fulltext",
        )
        # Test with single message
        session = AgentSession()
        context = SessionContext(input_messages=[Message(role="user", text="test query")])
        await provider.before_run(agent=None, session=session, context=context, state={})
        assert context.context_messages == {}

        # Test with message list
        context = SessionContext(input_messages=[
            Message(role="user", text="first query"),
            Message(role="assistant", text="first response"),
        ])
        await provider.before_run(agent=None, session=session, context=context, state={})
        assert context.context_messages == {}

    @pytest.mark.asyncio
    async def test_before_run_returns_context_when_connected(self) -> None:
        """before_run should add context messages when connected and results found."""
        provider = Neo4jContextProvider(
            index_name="test_index",
            index_type="fulltext",
        )
        mock_result = RetrieverResult(
            items=[
                RetrieverResultItem(content="Result about Acme Corp", metadata={"score": 0.95}),
                RetrieverResultItem(content="Result about products", metadata={"score": 0.80}),
            ]
        )
        with (
            patch.object(type(provider), "is_connected", new_callable=PropertyMock, return_value=True),
            patch.object(provider, "_execute_search", new_callable=AsyncMock, return_value=mock_result),
        ):
            session = AgentSession()
            context = SessionContext(input_messages=[Message(role="user", text="Tell me about Acme")])
            await provider.before_run(agent=None, session=session, context=context, state={})

            assert "neo4j-context" in context.context_messages
            messages = context.context_messages["neo4j-context"]
            # First message is the context prompt, followed by results
            assert len(messages) >= 3
            assert "Knowledge Graph Context" in messages[0].text
            assert "Acme Corp" in messages[1].text

    @pytest.mark.asyncio
    async def test_before_run_filters_non_user_assistant_messages(self) -> None:
        """before_run should only use user and assistant messages for search."""
        provider = Neo4jContextProvider(
            index_name="test_index",
            index_type="fulltext",
        )
        mock_result = RetrieverResult(
            items=[RetrieverResultItem(content="Some result", metadata={"score": 0.9})]
        )
        with (
            patch.object(type(provider), "is_connected", new_callable=PropertyMock, return_value=True),
            patch.object(provider, "_execute_search", new_callable=AsyncMock, return_value=mock_result) as mock_search,
        ):
            session = AgentSession()
            context = SessionContext(input_messages=[
                Message(role="system", text="You are a helpful assistant"),
                Message(role="user", text="What about Acme?"),
                Message(role="assistant", text="Acme is a company."),
            ])
            await provider.before_run(agent=None, session=session, context=context, state={})

            # Search should be called with only user+assistant text, not system
            call_args = mock_search.call_args
            query_text = call_args.kwargs.get("query_text") or call_args.args[0]
            assert "What about Acme?" in query_text
            assert "Acme is a company." in query_text
            assert "You are a helpful assistant" not in query_text

    @pytest.mark.asyncio
    async def test_before_run_skips_empty_messages(self) -> None:
        """before_run should not search when all messages are empty."""
        provider = Neo4jContextProvider(
            index_name="test_index",
            index_type="fulltext",
        )
        with (
            patch.object(type(provider), "is_connected", new_callable=PropertyMock, return_value=True),
            patch.object(provider, "_execute_search", new_callable=AsyncMock) as mock_search,
        ):
            session = AgentSession()
            context = SessionContext(input_messages=[
                Message(role="user", text=""),
                Message(role="user", text="   "),
            ])
            await provider.before_run(agent=None, session=session, context=context, state={})

            mock_search.assert_not_called()
            assert context.context_messages == {}

    @pytest.mark.asyncio
    async def test_before_run_respects_message_history_count(self) -> None:
        """before_run should only use the last N messages based on message_history_count."""
        provider = Neo4jContextProvider(
            index_name="test_index",
            index_type="fulltext",
            message_history_count=2,
        )
        mock_result = RetrieverResult(
            items=[RetrieverResultItem(content="Result", metadata={"score": 0.9})]
        )
        with (
            patch.object(type(provider), "is_connected", new_callable=PropertyMock, return_value=True),
            patch.object(provider, "_execute_search", new_callable=AsyncMock, return_value=mock_result) as mock_search,
        ):
            session = AgentSession()
            context = SessionContext(input_messages=[
                Message(role="user", text="first message"),
                Message(role="user", text="second message"),
                Message(role="user", text="third message"),
                Message(role="user", text="fourth message"),
                Message(role="user", text="fifth message"),
            ])
            await provider.before_run(agent=None, session=session, context=context, state={})

            call_args = mock_search.call_args
            query_text = call_args.kwargs.get("query_text") or call_args.args[0]
            # Only last 2 messages should be included
            assert "first message" not in query_text
            assert "second message" not in query_text
            assert "third message" not in query_text
            assert "fourth message" in query_text
            assert "fifth message" in query_text

    @pytest.mark.asyncio
    async def test_before_run_no_context_when_no_results(self) -> None:
        """before_run should not add context when search returns no results."""
        provider = Neo4jContextProvider(
            index_name="test_index",
            index_type="fulltext",
        )
        mock_result = RetrieverResult(items=[])
        with (
            patch.object(type(provider), "is_connected", new_callable=PropertyMock, return_value=True),
            patch.object(provider, "_execute_search", new_callable=AsyncMock, return_value=mock_result),
        ):
            session = AgentSession()
            context = SessionContext(input_messages=[Message(role="user", text="test query")])
            await provider.before_run(agent=None, session=session, context=context, state={})

            assert context.context_messages == {}


class TestHybridMode:
    """Test hybrid search mode."""

    def test_requires_fulltext_index_name(self) -> None:
        """Hybrid mode should require fulltext_index_name."""
        with pytest.raises(ValueError, match="fulltext_index_name is required"):
            Neo4jContextProvider(
                index_name="test_vector_index",
                index_type="hybrid",
            )
