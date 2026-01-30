"""
Tests for Neo4j Context Provider.

Tests the provider initialization and configuration validation.
"""

import pytest
from agent_framework import ChatMessage, Role

from agent_framework_neo4j import Neo4jContextProvider, Neo4jSettings
from agent_framework_neo4j._memory import MemoryManager, ScopeFilter


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


class TestInvoking:
    """Test the invoking method."""

    @pytest.mark.asyncio
    async def test_invoking_returns_empty_when_not_connected(self) -> None:
        """Invoking should return empty context when not connected."""
        provider = Neo4jContextProvider(
            index_name="test_index",
            index_type="fulltext",
        )
        # Test with single message
        message = ChatMessage(role=Role.USER, text="test query")
        context = await provider.invoking(message)
        assert context.messages == []

        # Test with message list
        messages = [
            ChatMessage(role=Role.USER, text="first query"),
            ChatMessage(role=Role.ASSISTANT, text="first response"),
        ]
        context = await provider.invoking(messages)
        assert context.messages == []


class TestHybridMode:
    """Test hybrid search mode."""

    def test_requires_fulltext_index_name(self) -> None:
        """Hybrid mode should require fulltext_index_name."""
        with pytest.raises(ValueError, match="fulltext_index_name is required"):
            Neo4jContextProvider(
                index_name="test_vector_index",
                index_type="hybrid",
            )


class TestMemoryConfiguration:
    """Test memory configuration options."""

    def test_memory_disabled_by_default(self) -> None:
        """Memory should be disabled by default."""
        provider = Neo4jContextProvider(
            index_name="test_index",
            index_type="fulltext",
        )
        assert provider._memory_enabled is False

    def test_memory_requires_scope_filter(self) -> None:
        """Memory should require at least one scope filter when enabled."""
        with pytest.raises(ValueError, match="Memory requires at least one scope filter"):
            Neo4jContextProvider(
                index_name="test_index",
                index_type="fulltext",
                memory_enabled=True,
            )

    @pytest.mark.parametrize(
        "scope_field,scope_value",
        [
            ("user_id", "test_user"),
            ("agent_id", "test_agent"),
            ("application_id", "test_app"),
            ("thread_id", "test_thread"),
        ],
    )
    def test_memory_enabled_with_single_scope(
        self, scope_field: str, scope_value: str
    ) -> None:
        """Memory should work with any single scope field."""
        provider = Neo4jContextProvider(
            index_name="test_index",
            index_type="fulltext",
            memory_enabled=True,
            **{scope_field: scope_value},
        )
        assert provider._memory_enabled is True
        assert getattr(provider, scope_field) == scope_value

    def test_custom_memory_label(self) -> None:
        """Memory should accept custom node label."""
        provider = Neo4jContextProvider(
            index_name="test_index",
            index_type="fulltext",
            memory_enabled=True,
            user_id="test_user",
            memory_label="ConversationMemory",
        )
        assert provider._memory_label == "ConversationMemory"

    def test_default_memory_label(self) -> None:
        """Memory should have default label 'Memory'."""
        provider = Neo4jContextProvider(
            index_name="test_index",
            index_type="fulltext",
            memory_enabled=True,
            user_id="test_user",
        )
        assert provider._memory_label == "Memory"

    def test_custom_memory_roles(self) -> None:
        """Memory should accept custom roles to store."""
        provider = Neo4jContextProvider(
            index_name="test_index",
            index_type="fulltext",
            memory_enabled=True,
            user_id="test_user",
            memory_roles=("user", "assistant", "system"),
        )
        assert provider._memory_roles == {"user", "assistant", "system"}

    def test_default_memory_roles(self) -> None:
        """Memory should default to storing user and assistant roles."""
        provider = Neo4jContextProvider(
            index_name="test_index",
            index_type="fulltext",
            memory_enabled=True,
            user_id="test_user",
        )
        assert provider._memory_roles == {"user", "assistant"}


class TestThreadIdHandling:
    """Test thread ID handling for memory scoping."""

    def test_effective_thread_id_uses_configured_thread_id(self) -> None:
        """Effective thread ID should use configured thread_id by default."""
        provider = Neo4jContextProvider(
            index_name="test_index",
            index_type="fulltext",
            memory_enabled=True,
            thread_id="configured_thread",
        )
        assert provider._effective_thread_id == "configured_thread"

    def test_effective_thread_id_uses_per_operation_when_scoped(self) -> None:
        """Effective thread ID should use per-operation thread when scoped."""
        provider = Neo4jContextProvider(
            index_name="test_index",
            index_type="fulltext",
            memory_enabled=True,
            user_id="test_user",
            scope_to_per_operation_thread_id=True,
        )
        provider._per_operation_thread_id = "per_op_thread"
        assert provider._effective_thread_id == "per_op_thread"

    @pytest.mark.asyncio
    async def test_thread_created_captures_thread_id(self) -> None:
        """thread_created should capture the thread ID."""
        provider = Neo4jContextProvider(
            index_name="test_index",
            index_type="fulltext",
            memory_enabled=True,
            user_id="test_user",
        )
        await provider.thread_created("new_thread_123")
        assert provider._per_operation_thread_id == "new_thread_123"

    @pytest.mark.asyncio
    async def test_thread_created_does_not_overwrite_existing(self) -> None:
        """thread_created should not overwrite existing thread ID."""
        provider = Neo4jContextProvider(
            index_name="test_index",
            index_type="fulltext",
            memory_enabled=True,
            user_id="test_user",
        )
        await provider.thread_created("first_thread")
        await provider.thread_created("second_thread")
        assert provider._per_operation_thread_id == "first_thread"

    @pytest.mark.asyncio
    async def test_thread_created_raises_on_conflict_when_scoped(self) -> None:
        """thread_created should raise when conflicting thread IDs and scoped."""
        provider = Neo4jContextProvider(
            index_name="test_index",
            index_type="fulltext",
            memory_enabled=True,
            user_id="test_user",
            scope_to_per_operation_thread_id=True,
        )
        await provider.thread_created("first_thread")
        with pytest.raises(ValueError, match="can only be used with one thread"):
            await provider.thread_created("different_thread")


class TestInvoked:
    """Test the invoked method for memory storage."""

    @pytest.mark.asyncio
    async def test_invoked_does_nothing_when_memory_disabled(self) -> None:
        """Invoked should do nothing when memory is disabled."""
        provider = Neo4jContextProvider(
            index_name="test_index",
            index_type="fulltext",
        )
        message = ChatMessage(role=Role.USER, text="test message")
        # Should not raise any errors
        await provider.invoked(message)

    @pytest.mark.asyncio
    async def test_invoked_does_nothing_when_not_connected(self) -> None:
        """Invoked should do nothing when not connected to Neo4j."""
        provider = Neo4jContextProvider(
            index_name="test_index",
            index_type="fulltext",
            memory_enabled=True,
            user_id="test_user",
        )
        message = ChatMessage(role=Role.USER, text="test message")
        # Should not raise any errors (not connected, so no storage attempt)
        await provider.invoked(message)


class TestMemoryIndexConfiguration:
    """Test memory index configuration (Phase 1B lazy initialization)."""

    def test_default_memory_index_names(self) -> None:
        """Should have default index names."""
        provider = Neo4jContextProvider(
            index_name="test_index",
            index_type="fulltext",
            memory_enabled=True,
            user_id="test_user",
        )
        assert provider._memory_vector_index_name == "memory_embeddings"
        assert provider._memory_fulltext_index_name == "memory_fulltext"

    def test_custom_memory_index_names(self) -> None:
        """Should accept custom index names."""
        provider = Neo4jContextProvider(
            index_name="test_index",
            index_type="fulltext",
            memory_enabled=True,
            user_id="test_user",
            memory_vector_index_name="custom_vector_idx",
            memory_fulltext_index_name="custom_fulltext_idx",
        )
        assert provider._memory_vector_index_name == "custom_vector_idx"
        assert provider._memory_fulltext_index_name == "custom_fulltext_idx"

    def test_overwrite_memory_index_default_false(self) -> None:
        """Overwrite memory index should default to False."""
        provider = Neo4jContextProvider(
            index_name="test_index",
            index_type="fulltext",
            memory_enabled=True,
            user_id="test_user",
        )
        assert provider._overwrite_memory_index is False

    def test_overwrite_memory_index_can_be_enabled(self) -> None:
        """Overwrite memory index can be set to True."""
        provider = Neo4jContextProvider(
            index_name="test_index",
            index_type="fulltext",
            memory_enabled=True,
            user_id="test_user",
            overwrite_memory_index=True,
        )
        assert provider._overwrite_memory_index is True

    def test_memory_indexes_not_initialized_initially(self) -> None:
        """Memory indexes should not be initialized at startup."""
        provider = Neo4jContextProvider(
            index_name="test_index",
            index_type="fulltext",
            memory_enabled=True,
            user_id="test_user",
        )
        assert provider._memory_indexes_initialized is False

    @pytest.mark.asyncio
    async def test_ensure_memory_indexes_raises_when_not_connected(self) -> None:
        """_ensure_memory_indexes should raise when driver not initialized."""
        provider = Neo4jContextProvider(
            index_name="test_index",
            index_type="fulltext",
            memory_enabled=True,
            user_id="test_user",
        )
        with pytest.raises(ValueError, match="Driver not initialized"):
            await provider._ensure_memory_indexes()


class TestScopeFilter:
    """Test ScopeFilter dataclass."""

    def test_empty_scope_returns_always_true(self) -> None:
        """Empty scope filter should return '1=1' WHERE clause."""
        scope = ScopeFilter()
        where_clause, params = scope.to_cypher_where()
        assert where_clause == "1=1"
        assert params == {}

    def test_single_field_filter(self) -> None:
        """Should build correct filter for single field."""
        scope = ScopeFilter(user_id="test_user")
        where_clause, params = scope.to_cypher_where()
        assert "m.user_id = $user_id" in where_clause
        assert params["user_id"] == "test_user"

    def test_multiple_fields_filter(self) -> None:
        """Should build correct filter for multiple fields."""
        scope = ScopeFilter(
            application_id="app1",
            agent_id="agent1",
            user_id="user1",
            thread_id="thread1",
        )
        where_clause, params = scope.to_cypher_where()
        assert "m.application_id = $application_id" in where_clause
        assert "m.agent_id = $agent_id" in where_clause
        assert "m.user_id = $user_id" in where_clause
        assert "m.thread_id = $thread_id" in where_clause
        assert params["application_id"] == "app1"
        assert params["agent_id"] == "agent1"
        assert params["user_id"] == "user1"
        assert params["thread_id"] == "thread1"

    def test_custom_alias(self) -> None:
        """Should use custom alias in WHERE clause."""
        scope = ScopeFilter(user_id="test_user")
        where_clause, params = scope.to_cypher_where(alias="memory")
        assert "memory.user_id = $user_id" in where_clause

    def test_immutable(self) -> None:
        """ScopeFilter should be immutable (frozen dataclass)."""
        scope = ScopeFilter(user_id="test_user")
        with pytest.raises(AttributeError):
            scope.user_id = "other_user"  # type: ignore[misc]


class TestMemoryManager:
    """Test MemoryManager class."""

    def test_default_initialization(self) -> None:
        """Should initialize with default values."""
        manager = MemoryManager(
            memory_roles={"user", "assistant"},
        )
        assert manager._memory_label == "Memory"
        assert manager._memory_vector_index_name == "memory_embeddings"
        assert manager._memory_fulltext_index_name == "memory_fulltext"
        assert manager._overwrite_memory_index is False
        assert manager._embedder is None
        assert manager.indexes_initialized is False

    def test_custom_initialization(self) -> None:
        """Should accept custom configuration."""
        manager = MemoryManager(
            memory_label="CustomMemory",
            memory_roles={"user"},
            memory_vector_index_name="custom_vector",
            memory_fulltext_index_name="custom_fulltext",
            overwrite_memory_index=True,
        )
        assert manager._memory_label == "CustomMemory"
        assert manager._memory_roles == {"user"}
        assert manager._memory_vector_index_name == "custom_vector"
        assert manager._memory_fulltext_index_name == "custom_fulltext"
        assert manager._overwrite_memory_index is True

    def test_indexes_initialized_property(self) -> None:
        """indexes_initialized property should reflect internal state."""
        manager = MemoryManager(memory_roles={"user"})
        assert manager.indexes_initialized is False
        manager._indexes_initialized = True
        assert manager.indexes_initialized is True
