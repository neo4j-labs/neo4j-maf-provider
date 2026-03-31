"""
Tests for Neo4jContextProvider async lifecycle.

Tests __aenter__ / __aexit__ with mocked Neo4j driver.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent_framework_neo4j import Neo4jContextProvider


class TestAsyncContextManager:
    """Test provider __aenter__ and __aexit__."""

    @pytest.mark.asyncio
    async def test_aenter_connects_and_creates_retriever(self) -> None:
        """__aenter__ should create driver, verify connectivity, and create retriever."""
        provider = Neo4jContextProvider(
            index_name="test_index",
            index_type="fulltext",
            uri="bolt://localhost:7687",
            username="neo4j",
            password="password",
        )

        mock_driver = MagicMock()
        mock_driver.verify_connectivity = MagicMock()
        mock_driver.close = MagicMock()

        with (
            patch("agent_framework_neo4j._provider.neo4j.GraphDatabase.driver", return_value=mock_driver),
            patch.object(provider, "_create_retriever", return_value=MagicMock()),
        ):
            result = await provider.__aenter__()

            assert result is provider
            assert provider.is_connected
            assert provider._driver is mock_driver

    @pytest.mark.asyncio
    async def test_aexit_closes_driver(self) -> None:
        """__aexit__ should close the driver and clear state."""
        provider = Neo4jContextProvider(
            index_name="test_index",
            index_type="fulltext",
            uri="bolt://localhost:7687",
            username="neo4j",
            password="password",
        )

        mock_driver = MagicMock()
        mock_driver.verify_connectivity = MagicMock()
        mock_driver.close = MagicMock()

        with (
            patch("agent_framework_neo4j._provider.neo4j.GraphDatabase.driver", return_value=mock_driver),
            patch.object(provider, "_create_retriever", return_value=MagicMock()),
        ):
            await provider.__aenter__()
            assert provider.is_connected

            await provider.__aexit__(None, None, None)

            assert not provider.is_connected
            assert provider._driver is None
            assert provider._retriever is None
            mock_driver.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_aexit_handles_no_driver(self) -> None:
        """__aexit__ should be safe to call when not connected."""
        provider = Neo4jContextProvider(
            index_name="test_index",
            index_type="fulltext",
        )
        # Should not raise
        await provider.__aexit__(None, None, None)
        assert not provider.is_connected

    @pytest.mark.asyncio
    async def test_context_manager_protocol(self) -> None:
        """Provider should work as an async context manager."""
        provider = Neo4jContextProvider(
            index_name="test_index",
            index_type="fulltext",
            uri="bolt://localhost:7687",
            username="neo4j",
            password="password",
        )

        mock_driver = MagicMock()
        mock_driver.verify_connectivity = MagicMock()
        mock_driver.close = MagicMock()

        with (
            patch("agent_framework_neo4j._provider.neo4j.GraphDatabase.driver", return_value=mock_driver),
            patch.object(provider, "_create_retriever", return_value=MagicMock()),
        ):
            async with provider as p:
                assert p is provider
                assert p.is_connected

            assert not provider.is_connected
            mock_driver.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_aenter_raises_on_connectivity_failure(self) -> None:
        """__aenter__ should propagate connectivity errors."""
        provider = Neo4jContextProvider(
            index_name="test_index",
            index_type="fulltext",
            uri="bolt://localhost:7687",
            username="neo4j",
            password="password",
        )

        mock_driver = MagicMock()
        mock_driver.verify_connectivity = MagicMock(side_effect=Exception("Connection refused"))

        with patch("agent_framework_neo4j._provider.neo4j.GraphDatabase.driver", return_value=mock_driver):
            with pytest.raises(Exception, match="Connection refused"):
                await provider.__aenter__()

    @pytest.mark.asyncio
    async def test_aenter_requires_connection_config(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """__aenter__ should raise if connection config is missing."""
        monkeypatch.delenv("NEO4J_URI", raising=False)
        monkeypatch.delenv("NEO4J_USERNAME", raising=False)
        monkeypatch.delenv("NEO4J_PASSWORD", raising=False)
        provider = Neo4jContextProvider(
            index_name="test_index",
            index_type="fulltext",
            # No uri/username/password
        )

        with pytest.raises(ValueError, match="Neo4j connection requires"):
            await provider.__aenter__()


class TestCreateRetriever:
    """Test _create_retriever with various configurations."""

    def test_raises_without_driver(self) -> None:
        """_create_retriever should raise if driver is not set."""
        provider = Neo4jContextProvider(
            index_name="test_index",
            index_type="fulltext",
        )
        with pytest.raises(ValueError, match="Driver not initialized"):
            provider._create_retriever()
