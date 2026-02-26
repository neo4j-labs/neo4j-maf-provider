"""
Fulltext Retriever for neo4j-graphrag integration.

Provides fulltext-only search capability that neo4j-graphrag doesn't support
(it only supports fulltext as part of hybrid search).
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from typing import Any

import neo4j
from neo4j_graphrag.exceptions import RetrieverInitializationError
from neo4j_graphrag.retrievers.base import Retriever
from neo4j_graphrag.types import (
    Neo4jDriverModel,
    RawSearchResult,
    RetrieverResultItem,
)
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from ._stop_words import FULLTEXT_STOP_WORDS

logger = logging.getLogger(__name__)


class FulltextRetrieverModel(BaseModel):
    """Pydantic model for FulltextRetriever configuration validation."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    driver_model: Neo4jDriverModel
    index_name: str
    retrieval_query: str | None = None
    filter_stop_words: bool = True
    result_formatter: Callable[[neo4j.Record], RetrieverResultItem] | None = None
    neo4j_database: str | None = None

    @field_validator("index_name")
    @classmethod
    def index_name_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("index_name cannot be empty")
        return v


class FulltextSearchModel(BaseModel):
    """Pydantic model for fulltext search parameters validation."""

    query_text: str
    top_k: int = 5
    query_params: dict[str, Any] | None = None

    @field_validator("query_text")
    @classmethod
    def query_text_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("query_text cannot be empty")
        return v

    @field_validator("top_k")
    @classmethod
    def top_k_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("top_k must be at least 1")
        return v


class FulltextRetriever(Retriever):
    """
    Retriever using fulltext search over Neo4j fulltext indexes.

    This retriever fills a gap in neo4j-graphrag, which only supports fulltext
    as part of hybrid search. It provides standalone fulltext search with
    optional stop word filtering to improve query results.

    Example:
        import neo4j
        from agent_framework_neo4j import FulltextRetriever

        driver = neo4j.GraphDatabase.driver(URI, auth=AUTH)

        retriever = FulltextRetriever(
            driver,
            index_name="maintenance_search",
            filter_stop_words=True,
        )
        retriever.search(query_text="engine vibration fault", top_k=5)

    Args:
        driver: The Neo4j Python driver.
        index_name: Fulltext index name.
        retrieval_query: Optional Cypher query appended after fulltext search.
            Use `node` and `score` variables from the search.
        filter_stop_words: Remove common stop words from queries to improve
            Lucene matching. Defaults to True.
        result_formatter: Custom function to transform neo4j.Record to RetrieverResultItem.
        neo4j_database: Neo4j database name. Defaults to server's default.
    """

    VERIFY_NEO4J_VERSION = False  # Fulltext doesn't require vector index support

    def __init__(
        self,
        driver: neo4j.Driver,
        index_name: str,
        retrieval_query: str | None = None,
        filter_stop_words: bool = True,
        result_formatter: Callable[[neo4j.Record], RetrieverResultItem] | None = None,
        neo4j_database: str | None = None,
    ) -> None:
        try:
            driver_model = Neo4jDriverModel(driver=driver)
            validated_data = FulltextRetrieverModel(
                driver_model=driver_model,
                index_name=index_name,
                retrieval_query=retrieval_query,
                filter_stop_words=filter_stop_words,
                result_formatter=result_formatter,
                neo4j_database=neo4j_database,
            )
        except ValidationError as e:
            raise RetrieverInitializationError(e.errors()) from e

        super().__init__(validated_data.driver_model.driver, validated_data.neo4j_database)
        self.index_name = validated_data.index_name
        self.retrieval_query = validated_data.retrieval_query
        self.filter_stop_words = validated_data.filter_stop_words
        self.result_formatter = validated_data.result_formatter

    def _extract_keywords(self, text: str) -> str:
        """
        Extract keywords from text by removing stop words.

        Used for fulltext search to improve query results when users
        ask natural language questions like "What maintenance issues
        involve engine vibration?" - extracting just "maintenance engine vibration".

        Args:
            text: The input text (typically a user question).

        Returns:
            Space-separated keywords with stop words removed.
        """
        words = re.findall(r"\b\w+\b", text.lower())
        keywords = [w for w in words if w not in FULLTEXT_STOP_WORDS and len(w) > 1]
        return " ".join(keywords)

    def default_record_formatter(self, record: neo4j.Record) -> RetrieverResultItem:
        """
        Format a fulltext search result record.

        Follows neo4j-graphrag pattern of extracting content and metadata
        from the record.
        """
        metadata = {
            "score": record.get("score"),
        }
        # Try to get text from common field names
        content = record.get("text") or record.get("content") or str(record.get("node", record))
        return RetrieverResultItem(
            content=str(content),
            metadata=metadata,
        )

    def get_search_results(
        self,
        query_text: str,
        top_k: int = 5,
        query_params: dict[str, Any] | None = None,
    ) -> RawSearchResult:
        """
        Get fulltext search results from Neo4j.

        Args:
            query_text: The text to search for.
            top_k: Number of results to return. Defaults to 5.
            query_params: Additional parameters for the retrieval query.

        Returns:
            RawSearchResult: Search results as neo4j.Records with metadata.
        """
        # Apply stop word filtering if enabled
        if self.filter_stop_words:
            search_text = self._extract_keywords(query_text)
            if not search_text.strip():
                # No keywords found after filtering - return empty results
                return RawSearchResult(records=[], metadata={"query_text": query_text})
        else:
            search_text = query_text

        # Build the Cypher query
        # For retrieval_query: Apply LIMIT twice - once to limit nodes from fulltext search,
        # and once at the end to limit final rows (retrieval_query MATCH may fan out)
        if self.retrieval_query:
            cypher = f"""
            CALL db.index.fulltext.queryNodes($index_name, $query)
            YIELD node, score
            WITH node, score
            ORDER BY score DESC
            LIMIT $top_k
            {self.retrieval_query}
            LIMIT $top_k
            """
        else:
            cypher = """
            CALL db.index.fulltext.queryNodes($index_name, $query)
            YIELD node, score
            WITH node, score
            ORDER BY score DESC
            LIMIT $top_k
            RETURN node, score
            """

        parameters: dict[str, Any] = {
            "index_name": self.index_name,
            "query": search_text,
            "top_k": top_k,
        }

        # Add custom query params if provided
        if query_params:
            for key, value in query_params.items():
                if key not in parameters:
                    parameters[key] = value

        logger.debug("FulltextRetriever Cypher query: %s", cypher)
        logger.debug("FulltextRetriever parameters: %s", parameters)

        records, _, _ = self.driver.execute_query(
            cypher,
            parameters,
            database_=self.neo4j_database,
            routing_=neo4j.RoutingControl.READ,
        )

        return RawSearchResult(
            records=records,
            metadata={"query_text": query_text, "search_text": search_text},
        )
