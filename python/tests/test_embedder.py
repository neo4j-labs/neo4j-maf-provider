"""
Tests for AzureAIEmbedder.

Tests embed_query, close, and constructor with mocked Azure AI SDK.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from agent_framework_neo4j import AzureAIEmbedder


def _mock_embedding_response(vector: list[float]) -> MagicMock:
    """Create a mock Azure AI embedding response."""
    embedding_item = MagicMock()
    embedding_item.embedding = vector
    response = MagicMock()
    response.data = [embedding_item]
    return response


class TestAzureAIEmbedderInit:
    """Test AzureAIEmbedder construction."""

    @patch("azure.ai.inference.EmbeddingsClient")
    def test_creates_client_with_credential(self, mock_client_cls: MagicMock) -> None:
        """Constructor should create EmbeddingsClient with correct params."""
        credential = MagicMock()

        AzureAIEmbedder(
            endpoint="https://myhost.models.ai.azure.com",
            credential=credential,
            model="text-embedding-ada-002",
        )

        mock_client_cls.assert_called_once_with(
            endpoint="https://myhost.models.ai.azure.com",
            credential=credential,
            credential_scopes=["https://ai.azure.com/.default"],
        )

    @patch("azure.ai.inference.EmbeddingsClient")
    def test_accepts_custom_credential_scopes(self, mock_client_cls: MagicMock) -> None:
        """Constructor should allow custom credential scopes."""
        credential = MagicMock()

        AzureAIEmbedder(
            endpoint="https://myhost.models.ai.azure.com",
            credential=credential,
            model="text-embedding-ada-002",
            credential_scopes=["https://cognitiveservices.azure.com/.default"],
        )

        mock_client_cls.assert_called_once_with(
            endpoint="https://myhost.models.ai.azure.com",
            credential=credential,
            credential_scopes=["https://cognitiveservices.azure.com/.default"],
        )

    @patch("azure.ai.inference.EmbeddingsClient")
    def test_accepts_single_credential_scope_string(self, mock_client_cls: MagicMock) -> None:
        """Constructor should not split a single credential scope string into characters."""
        credential = MagicMock()

        AzureAIEmbedder(
            endpoint="https://myhost.models.ai.azure.com",
            credential=credential,
            model="text-embedding-ada-002",
            credential_scopes="https://cognitiveservices.azure.com/.default",
        )

        mock_client_cls.assert_called_once_with(
            endpoint="https://myhost.models.ai.azure.com",
            credential=credential,
            credential_scopes=["https://cognitiveservices.azure.com/.default"],
        )

    @patch("azure.ai.inference.EmbeddingsClient")
    def test_default_model(self, _mock_client_cls: MagicMock) -> None:
        """Default model should be text-embedding-ada-002."""
        embedder = AzureAIEmbedder(
            endpoint="https://myhost.models.ai.azure.com",
            credential=MagicMock(),
        )
        assert embedder._model == "text-embedding-ada-002"

    @patch("azure.ai.inference.EmbeddingsClient")
    def test_custom_model(self, _mock_client_cls: MagicMock) -> None:
        """Should accept custom model name."""
        embedder = AzureAIEmbedder(
            endpoint="https://myhost.models.ai.azure.com",
            credential=MagicMock(),
            model="text-embedding-3-large",
        )
        assert embedder._model == "text-embedding-3-large"


class TestEmbedQuery:
    """Test the embed_query method."""

    @patch("azure.ai.inference.EmbeddingsClient")
    def test_returns_embedding_vector(self, mock_client_cls: MagicMock) -> None:
        """embed_query should return the embedding vector from the response."""
        expected_vector = [0.1, 0.2, 0.3, 0.4]
        mock_client = MagicMock()
        mock_client.embed.return_value = _mock_embedding_response(expected_vector)
        mock_client_cls.return_value = mock_client

        embedder = AzureAIEmbedder(
            endpoint="https://myhost.models.ai.azure.com",
            credential=MagicMock(),
        )
        result = embedder.embed_query("test text")

        assert result == expected_vector

    @patch("azure.ai.inference.EmbeddingsClient")
    def test_passes_correct_params_to_client(self, mock_client_cls: MagicMock) -> None:
        """embed_query should call client.embed with correct parameters."""
        mock_client = MagicMock()
        mock_client.embed.return_value = _mock_embedding_response([0.1])
        mock_client_cls.return_value = mock_client

        embedder = AzureAIEmbedder(
            endpoint="https://myhost.models.ai.azure.com",
            credential=MagicMock(),
            model="my-model",
        )
        embedder.embed_query("hello world")

        call_kwargs = mock_client.embed.call_args[1]
        assert call_kwargs["input"] == ["hello world"]
        assert call_kwargs["model"] == "my-model"

    @patch("azure.ai.inference.EmbeddingsClient")
    def test_raises_on_unexpected_embedding_type(self, mock_client_cls: MagicMock) -> None:
        """embed_query should raise ValueError if embedding is not a list."""
        mock_client = MagicMock()
        embedding_item = MagicMock()
        embedding_item.embedding = "not a list"
        response = MagicMock()
        response.data = [embedding_item]
        mock_client.embed.return_value = response
        mock_client_cls.return_value = mock_client

        embedder = AzureAIEmbedder(
            endpoint="https://myhost.models.ai.azure.com",
            credential=MagicMock(),
        )
        with pytest.raises(ValueError, match="Unexpected embedding type"):
            embedder.embed_query("test")


class TestClose:
    """Test the close method."""

    @patch("azure.ai.inference.EmbeddingsClient")
    def test_closes_credential_if_supported(self, _mock_client_cls: MagicMock) -> None:
        """close() should call credential.close() when available."""
        credential = MagicMock()

        embedder = AzureAIEmbedder(
            endpoint="https://myhost.models.ai.azure.com",
            credential=credential,
        )
        embedder.close()

        credential.close.assert_called_once()

    @patch("azure.ai.inference.EmbeddingsClient")
    def test_no_error_if_credential_not_closeable(self, _mock_client_cls: MagicMock) -> None:
        """close() should not fail if credential has no close method."""
        credential = MagicMock(spec=[])  # spec=[] means no attributes

        embedder = AzureAIEmbedder(
            endpoint="https://myhost.models.ai.azure.com",
            credential=credential,
        )
        # Should not raise
        embedder.close()
