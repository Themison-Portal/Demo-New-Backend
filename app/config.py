"""
Configuration for the application
"""
from functools import lru_cache

from typing import Any
from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings
    """

    openai_api_key: str = ""
    anthropic_api_key: str = ""  # Required for Claude Opus 4.5
    database_url: str = ""  # PostgreSQL connection (asyncpg format)
    redis_url: str = ""
    frontend_url: str = "http://localhost:3000"  # Optional with default
    upload_api_key: str = ""  # API key for upload endpoint (X-API-KEY header)

    # Auth0 configuration
    auth0_domain: str = ""
    auth0_audience: str = ""
    auth0_client_id: str = ""
    auth0_client_secret: str = ""
    auth_disabled: bool = False  # Set to True to bypass Auth0 for testing

    # Google Cloud Storage configuration
    gcs_project_id: str = ""
    gcs_bucket_trial_documents: str = ""
    gcs_bucket_patient_documents: str = ""
    gcs_credentials_path: str = ""

    # Semantic cache configuration
    semantic_cache_similarity_threshold: float = 0.90  # Cosine similarity threshold for cache hits

    # Hybrid search configuration (Phase 1)
    hybrid_search_enabled: bool = True
    hybrid_search_rrf_k: int = 60  # RRF constant (typically 60)

    # Retrieval configuration
    retrieval_min_score: float = 0.04  # Minimum cosine similarity for vector-only search
    retrieval_top_k: int = 20  # Number of chunks to retrieve

    # Reranking configuration (Phase 2)
    reranker_enabled: bool = False
    reranker_provider: str = "cohere"  # Options: "cohere", "jina", "bge"
    reranker_model: str = "rerank-english-v3.0"
    reranker_top_k: int = 5  # Return top N after reranking
    cohere_api_key: str = ""

    # Embedding model configuration (Phase 3)
    embedding_model: str = "text-embedding-3-small"  # or "text-embedding-3-large"
    embedding_dimensions: int = 1536  # 1536 for small, 2000 for large (HNSW limit)

    # Contextual retrieval configuration (Phase 4)
    contextual_retrieval_enabled: bool = False
    contextual_context_window: int = 3  # Include N surrounding chunks for context

    # gRPC RAG Service configuration
    rag_service_address: str = "localhost:50051"  # Address of RAG gRPC service
    rag_service_timeout: float = 600.0  # gRPC timeout in seconds for RAG service calls
    use_grpc_rag: bool = False  # Feature flag for gradual rollout
    
    # Email Configuration
    sendgrid_api_key: str = ""
    email_from: str = "noreply@themison.com"
    email_from_name: str = "Themison Portal"

    @field_validator("*", mode="before")
    @classmethod
    def strip_strings(cls, v: Any, info) -> Any:
        """Strip whitespace from all string inputs and trailing slashes from URLs."""
        if isinstance(v, str):
            v = v.strip()
            # If the field is a URL field, strip the trailing slash
            if info.field_name == "frontend_url":
                v = v.rstrip("/")
            return v
        return v

    class Config:
        """
        Configuration for the application settings
        """
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

@lru_cache()
def get_settings() -> Settings:
    """
    Get the application settings with caching.
    
    Returns:
        Settings: The application configuration settings.
    """
    return Settings()