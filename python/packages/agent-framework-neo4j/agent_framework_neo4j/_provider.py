"""
Neo4j Context Provider for Microsoft Agent Framework.

Provides RAG context from Neo4j using vector, fulltext, or hybrid search
via neo4j-graphrag retrievers, with optional graph enrichment.
"""

from __future__ import annotations

import asyncio
import sys
from typing import TYPE_CHECKING, Any

import neo4j
from agent_framework import (
    AgentSession,
    BaseContextProvider,
    Message,
    SessionContext,
)

if TYPE_CHECKING:
    from agent_framework import SupportsAgentRun
from neo4j_graphrag.embeddings import Embedder
from neo4j_graphrag.retrievers import (
    HybridCypherRetriever,
    HybridRetriever,
    VectorCypherRetriever,
    VectorRetriever,
)
from neo4j_graphrag.types import RetrieverResult, RetrieverResultItem

from ._config import DEFAULT_CONTEXT_PROMPT, IndexType, ProviderConfig
from ._fulltext import FulltextRetriever
from ._settings import Neo4jSettings

if sys.version_info >= (3, 12):
    from typing import Self
else:
    from typing_extensions import Self


# Type alias for all supported retrievers
RetrieverType = VectorRetriever | VectorCypherRetriever | HybridRetriever | HybridCypherRetriever | FulltextRetriever


def _format_cypher_result(record: neo4j.Record) -> RetrieverResultItem:
    """
    Format a neo4j Record from a Cypher retrieval query into a RetrieverResultItem.

    Extracts 'text' as content and all other fields as metadata.
    This provides proper parsing of custom retrieval query results.
    """
    data = dict(record)
    # Extract text content (use 'text' field or first string field)
    content = data.pop("text", None)
    if content is None:
        # Fallback: use first string value found
        for _key, value in data.items():
            if isinstance(value, str):
                content = value
                break
    if content is None:
        content = str(record)

    # All remaining fields go to metadata
    return RetrieverResultItem(content=str(content), metadata=data if data else None)


class Neo4jContextProvider(BaseContextProvider):
    """
    Context provider that retrieves knowledge graph context from Neo4j.

    Uses neo4j-graphrag retrievers for search:
    - VectorRetriever / VectorCypherRetriever for vector search
    - HybridRetriever / HybridCypherRetriever for hybrid (vector + fulltext)
    - FulltextRetriever for fulltext-only search

    Key design principles:
    - NO entity extraction - passes full message text to search
    - Index-driven configuration - works with any Neo4j index
    - Configurable enrichment - users define their own retrieval_query
    - Async wrapping - neo4j-graphrag retrievers are sync, wrapped with asyncio.to_thread()
    """

    def __init__(
        self,
        *,
        source_id: str = "neo4j-context",
        # Connection (falls back to environment variables)
        uri: str | None = None,
        username: str | None = None,
        password: str | None = None,
        # Index configuration (required)
        index_name: str | None = None,
        index_type: IndexType = "vector",
        # For hybrid search - optional second index
        fulltext_index_name: str | None = None,
        # Search parameters
        top_k: int = 5,
        context_prompt: str = DEFAULT_CONTEXT_PROMPT,
        # Graph enrichment - Cypher query for traversal after index search
        retrieval_query: str | None = None,
        # Embedder for vector/hybrid search (neo4j-graphrag Embedder)
        embedder: Embedder | None = None,
        # Message history (like Azure AI Search's agentic mode)
        message_history_count: int = 10,
        # Fulltext search options
        filter_stop_words: bool | None = None,
    ) -> None:
        """
        Initialize the Neo4j context provider.

        Args:
            source_id: Unique identifier for this provider instance.
            uri: Neo4j connection URI. Falls back to NEO4J_URI env var.
            username: Neo4j username. Falls back to NEO4J_USERNAME env var.
            password: Neo4j password. Falls back to NEO4J_PASSWORD env var.
            index_name: Name of the Neo4j index to query. Required.
                For vector/hybrid: the vector index name.
                For fulltext: the fulltext index name.
            index_type: Type of search - "vector", "fulltext", or "hybrid".
            fulltext_index_name: Fulltext index name for hybrid search.
                Required when index_type is "hybrid".
            top_k: Number of results to retrieve.
            context_prompt: Prompt prepended to context.
            retrieval_query: Optional Cypher query for graph enrichment.
                If provided, runs after index search to traverse the graph.
                Must use `node` and `score` variables from index search.
            embedder: neo4j-graphrag Embedder for vector/hybrid search.
                Required when index_type is "vector" or "hybrid".
            message_history_count: Number of recent messages to use for query.
            filter_stop_words: Filter common stop words from fulltext queries.
                Defaults to True for fulltext indexes, False otherwise.

        Raises:
            ValueError: If required configuration is missing or invalid.
        """
        super().__init__(source_id)

        # Load settings from environment (single source of truth)
        settings = Neo4jSettings()

        # Build effective settings by merging constructor args with env settings
        effective_uri = uri or settings.uri
        effective_username = username or settings.username
        effective_password = password or settings.get_password()
        effective_index_name = index_name or settings.index_name

        # Validate index_name is provided (before Pydantic validation)
        if not effective_index_name:
            raise ValueError(
                "index_name is required. Set via constructor or NEO4J_INDEX_NAME env var."
            )

        # Use Pydantic model for comprehensive validation
        self._config = ProviderConfig(
            uri=effective_uri,
            username=effective_username,
            password=effective_password,
            index_name=effective_index_name,
            index_type=index_type,
            fulltext_index_name=fulltext_index_name,
            retrieval_query=retrieval_query,
            top_k=top_k,
            context_prompt=context_prompt,
            message_history_count=message_history_count,
            filter_stop_words=filter_stop_words,
            embedder=embedder,
        )

        # Extract commonly accessed values to instance attributes
        # (Following Pure Pydantic Settings pattern from Azure AI Search provider)
        self._index_name = self._config.index_name
        self._index_type = self._config.index_type
        self._retrieval_query = self._config.retrieval_query
        self._top_k = self._config.top_k
        self._context_prompt = self._config.context_prompt
        self._message_history_count = self._config.message_history_count

        # Stop word filtering - default to True for fulltext, False otherwise
        if self._config.filter_stop_words is None:
            self._filter_stop_words = self._index_type == "fulltext"
        else:
            self._filter_stop_words = self._config.filter_stop_words

        # Runtime state
        self._driver: neo4j.Driver | None = None
        self._retriever: RetrieverType | None = None

    def _create_retriever(self) -> RetrieverType:
        """Create the appropriate neo4j-graphrag retriever based on configuration."""
        if self._driver is None:
            raise ValueError("Driver not initialized")

        # Determine if graph enrichment is enabled (retrieval_query provided)
        use_graph_enrichment = self._retrieval_query is not None

        if self._index_type == "vector":
            if use_graph_enrichment:
                return VectorCypherRetriever(
                    driver=self._driver,
                    index_name=self._index_name,
                    retrieval_query=self._config.get_retrieval_query(),
                    embedder=self._config.get_embedder(),
                    result_formatter=_format_cypher_result,
                )
            else:
                return VectorRetriever(
                    driver=self._driver,
                    index_name=self._index_name,
                    embedder=self._config.get_embedder(),
                )

        elif self._index_type == "hybrid":
            if use_graph_enrichment:
                return HybridCypherRetriever(
                    driver=self._driver,
                    vector_index_name=self._index_name,
                    fulltext_index_name=self._config.get_fulltext_index_name(),
                    retrieval_query=self._config.get_retrieval_query(),
                    embedder=self._config.get_embedder(),
                    result_formatter=_format_cypher_result,
                )
            else:
                return HybridRetriever(
                    driver=self._driver,
                    vector_index_name=self._index_name,
                    fulltext_index_name=self._config.get_fulltext_index_name(),
                    embedder=self._config.get_embedder(),
                )

        else:  # fulltext
            return FulltextRetriever(
                driver=self._driver,
                index_name=self._index_name,
                retrieval_query=self._retrieval_query,
                filter_stop_words=self._filter_stop_words,
                result_formatter=_format_cypher_result if use_graph_enrichment else None,
            )

    async def __aenter__(self) -> Self:
        """Connect to Neo4j and create retriever."""
        # Get validated connection config (raises if not all set)
        uri, username, password = self._config.get_connection()

        # Create driver
        self._driver = neo4j.GraphDatabase.driver(
            uri,
            auth=(username, password),
        )

        # Verify connectivity (sync call wrapped for async)
        await asyncio.to_thread(self._driver.verify_connectivity)

        # Create retriever in thread pool because neo4j-graphrag retrievers
        # call _fetch_index_infos() during __init__ which makes DB calls
        self._retriever = await asyncio.to_thread(self._create_retriever)

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Close Neo4j connection."""
        if self._driver is not None:
            self._driver.close()
            self._driver = None
            self._retriever = None

    @property
    def is_connected(self) -> bool:
        """Check if the provider is connected to Neo4j."""
        return self._driver is not None and self._retriever is not None

    def _format_retriever_result(self, result: RetrieverResult) -> list[str]:
        """Format neo4j-graphrag RetrieverResult items as text for context."""
        formatted: list[str] = []

        for item in result.items:
            parts: list[str] = []

            # Include score if present in metadata
            if item.metadata and "score" in item.metadata:
                score = item.metadata["score"]
                if score is not None:
                    parts.append(f"[Score: {score:.3f}]")

            # Include other metadata fields
            if item.metadata:
                for key, value in item.metadata.items():
                    if key == "score" or value is None:
                        continue
                    parts.append(self._format_field(key, value))

            # Include content
            if item.content:
                parts.append(str(item.content))

            if parts:
                formatted.append(" ".join(parts))

        return formatted

    def _format_field(self, key: str, value: Any) -> str:
        """Format a single field value, handling lists and scalars."""
        # Try to treat as list first (duck typing)
        try:
            # Strings are iterable but we want them as scalars
            if value == str(value):
                return f"[{key}: {value}]"
        except (TypeError, ValueError):
            pass

        # Try to iterate and join
        try:
            items = list(value)
            if items:
                return f"[{key}: {', '.join(str(v) for v in items)}]"
            return ""
        except TypeError:
            # Not iterable, treat as scalar
            return f"[{key}: {value}]"

    async def _execute_search(self, query_text: str) -> RetrieverResult:
        """Execute search using the configured retriever."""
        if self._retriever is None:
            raise ValueError("Retriever not initialized")

        # neo4j-graphrag retrievers are sync, wrap with asyncio.to_thread
        return await asyncio.to_thread(
            self._retriever.search,
            query_text=query_text,
            top_k=self._top_k,
        )

    async def before_run(
        self,
        *,
        agent: SupportsAgentRun,  # noqa: ARG002
        session: AgentSession,  # noqa: ARG002
        context: SessionContext,
        state: dict[str, Any],  # noqa: ARG002
    ) -> None:
        """
        Called before each LLM invocation to provide context.

        Key design: NO entity extraction. The full message text is passed
        to the index search, which handles relevance ranking.
        """
        if not self.is_connected:
            return

        messages_list = list(context.input_messages)

        # Filter to user and assistant messages with text
        filtered_messages = [
            msg
            for msg in messages_list
            if msg.text and msg.text.strip() and msg.role in ("user", "assistant")
        ]

        if not filtered_messages:
            return

        # Take recent messages (like Azure AI Search's agentic mode)
        recent_messages = filtered_messages[-self._message_history_count :]

        # CRITICAL: Concatenate full message text - NO ENTITY EXTRACTION
        query_text = "\n".join(msg.text for msg in recent_messages if msg.text)

        if not query_text.strip():
            return

        # Perform knowledge graph search using retriever
        result = await self._execute_search(query_text)
        if not result.items:
            return

        context_messages: list[Message] = [Message(role="user", text=self._context_prompt)]
        formatted_results = self._format_retriever_result(result)
        for text in formatted_results:
            if text:
                context_messages.append(Message(role="user", text=text))

        if context_messages:
            context.extend_messages(self.source_id, context_messages)
