"""
Azure AI Embedder for neo4j-graphrag integration.

Provides an embedder that uses Azure AI Inference SDK with DefaultAzureCredential,
compatible with neo4j-graphrag's Embedder interface.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from neo4j_graphrag.embeddings import Embedder
from neo4j_graphrag.utils.rate_limit import RateLimitHandler

if TYPE_CHECKING:
    from azure.ai.inference import EmbeddingsClient  # type: ignore[import-untyped]
    from azure.core.credentials import TokenCredential


class AzureAIEmbedder(Embedder):
    """
    Embedder using Azure AI Inference SDK with Azure credential authentication.

    This embedder implements neo4j-graphrag's Embedder interface while using
    Azure AI Inference SDK internally, allowing use of DefaultAzureCredential
    instead of API keys.

    Example:
        from azure.identity import DefaultAzureCredential
        from agent_framework_neo4j import AzureAIEmbedder

        embedder = AzureAIEmbedder(
            endpoint="https://your-project.models.ai.azure.com",
            credential=DefaultAzureCredential(),
            model="text-embedding-ada-002",
        )

        # Use with neo4j-graphrag retrievers
        retriever = VectorRetriever(driver, "index", embedder=embedder)

    Args:
        endpoint: Azure AI Inference endpoint (models endpoint).
        credential: Azure credential for authentication (e.g., DefaultAzureCredential).
        model: Embedding model deployment name.
        rate_limit_handler: Optional handler for rate limiting. Defaults to retry
            with exponential backoff (neo4j-graphrag default).
    """

    def __init__(
        self,
        endpoint: str,
        credential: TokenCredential,
        model: str = "text-embedding-ada-002",
        rate_limit_handler: RateLimitHandler | None = None,
    ) -> None:
        """
        Initialize the Azure AI embedder.

        Args:
            endpoint: Azure AI Inference endpoint (models endpoint).
            credential: Azure credential for authentication (e.g., DefaultAzureCredential).
            model: Embedding model deployment name.
            rate_limit_handler: Optional handler for rate limiting.
        """
        from azure.ai.inference import EmbeddingsClient

        super().__init__(rate_limit_handler)
        self._model = model
        self._credential = credential
        self._client: EmbeddingsClient = EmbeddingsClient(
            endpoint=endpoint,
            credential=credential,
            credential_scopes=["https://cognitiveservices.azure.com/.default"],
        )

    def embed_query(self, text: str) -> list[float]:
        """
        Embed query text into a vector.

        Implements the neo4j-graphrag Embedder interface.

        Args:
            text: Text to convert to vector embedding.

        Returns:
            Vector embedding as list of floats.
        """
        from azure.ai.inference.models import EmbeddingInputType  # type: ignore[import-untyped]

        response = self._client.embed(
            input=[text],
            model=self._model,
            input_type=EmbeddingInputType.QUERY,
        )
        embedding = response.data[0].embedding
        if not isinstance(embedding, list):
            raise ValueError(f"Unexpected embedding type: {type(embedding)}")
        return embedding

    def close(self) -> None:
        """Close the underlying credential if it supports closing."""
        if hasattr(self._credential, "close"):
            self._credential.close()
