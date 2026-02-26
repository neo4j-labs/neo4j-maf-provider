"""
Settings for Neo4j Context Provider.

This module provides pydantic settings classes for Neo4j connection
and Azure AI embeddings configuration.
"""

from __future__ import annotations

from pydantic import Field, SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Neo4jSettings(BaseSettings):
    """
    Neo4j configuration loaded from environment variables.

    All settings use the NEO4J_ prefix for environment variables.
    Example: NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD

    Attributes:
        uri: Neo4j connection URI
        username: Neo4j username
        password: Neo4j password (SecretStr for security)
        vector_index_name: Name of the vector index
        fulltext_index_name: Name of the fulltext index
    """

    model_config = SettingsConfigDict(
        env_prefix="NEO4J_",
        extra="ignore",
    )

    # Connection settings
    uri: str | None = Field(
        default=None,
        description="Neo4j connection URI (e.g., bolt://localhost:7687)",
    )
    username: str | None = Field(
        default=None,
        description="Neo4j username",
    )
    password: SecretStr | None = Field(
        default=None,
        description="Neo4j password",
    )

    # Index configuration
    index_name: str | None = Field(
        default=None,
        description="Default index name (can be vector or fulltext depending on usage)",
    )
    vector_index_name: str = Field(
        default="chunkEmbeddings",
        description="Name of the Neo4j vector index to query",
    )
    fulltext_index_name: str = Field(
        default="chunkFulltext",
        description="Name of the Neo4j fulltext index to query",
    )

    @property
    def is_configured(self) -> bool:
        """Check if all required Neo4j connection settings are provided."""
        return all([self.uri, self.username, self.password])

    def get_password(self) -> str | None:
        """Safely retrieve the password value."""
        if self.password is None:
            return None
        return self.password.get_secret_value()


class AzureAISettings(BaseSettings):
    """
    Azure AI configuration for embeddings.

    Loads from environment variables for Microsoft Foundry integration.
    """

    model_config = SettingsConfigDict(
        env_prefix="",
        extra="ignore",
    )

    # Microsoft Foundry project endpoint
    project_endpoint: str | None = Field(
        default=None,
        validation_alias="AZURE_AI_PROJECT_ENDPOINT",
    )

    # Embedding model deployment name
    embedding_model: str = Field(
        default="text-embedding-ada-002",
        validation_alias="AZURE_AI_EMBEDDING_NAME",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def inference_endpoint(self) -> str | None:
        """Get the model inference endpoint from project endpoint."""
        if not self.project_endpoint:
            return None
        # Convert project endpoint to model inference endpoint
        if "/api/projects/" in self.project_endpoint:
            base = self.project_endpoint.split("/api/projects/")[0]
            return f"{base}/models"
        return self.project_endpoint

    @property
    def is_configured(self) -> bool:
        """Check if Azure AI settings are provided."""
        return self.project_endpoint is not None
