"""
Configuration for the application - HARDCODED FOR DEPLOYMENT FIX v4
"""
from functools import lru_cache
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """
    Application settings
    """
    # Hardcoded Secrets (REMOVED FOR SECURITY - Set via Environment Variables)
    supabase_url: str = "https://nidpneaqxghqueniodus.supabase.co" # Non-secret
    supabase_service_key: str = "" # Set SUPABASE_SERVICE_KEY env var
    openai_api_key: str = "" # Set OPENAI_API_KEY env var
    anthropic_api_key: str = "" # Set ANTHROPIC_API_KEY env var
    supabase_db_url: str = "postgresql+asyncpg://postgres:postgres@10.132.0.2:5432/postgres" # Internal IP OK

    # Optionals with Defaults
    supabase_anon_key: str = "" # Set SUPABASE_ANON_KEY env var
    supabase_db_password: str = "postgres" # Internal Default OK
    redis_url: str = "redis://10.132.0.2:6379" # Internal IP OK
    frontend_url: str = "*"
    upload_api_key: str = ""

    # Semantic cache configuration
    semantic_cache_similarity_threshold: float = 0.90
    hybrid_search_enabled: bool = True
    hybrid_search_rrf_k: int = 60
    retrieval_min_score: float = 0.04
    retrieval_top_k: int = 20

    # Reranking configuration
    reranker_enabled: bool = False
    reranker_provider: str = "cohere"
    reranker_model: str = "rerank-english-v3.0"
    reranker_top_k: int = 5
    cohere_api_key: str = ""

    # Embedding model configuration
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    # Contextual retrieval configuration
    contextual_retrieval_enabled: bool = False
    contextual_context_window: int = 3

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
