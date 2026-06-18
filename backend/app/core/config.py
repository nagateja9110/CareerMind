from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CareerMind"
    environment: str = "development"
    api_prefix: str = "/api"
    mongo_uri: str = "mongodb://mongo:27017"
    mongo_db: str = "CareerMind"
    solr_url: str = "http://solr:8983/solr/jobs"
    users_collection: str = "users"
    chats_collection: str = "chats"
    resumes_collection: str = "resumes"
    skills_taxonomy_collection: str = "skills_taxonomy"
    agent_max_tool_steps: int = 3
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    groq_base_url: str = "https://api.groq.com/openai/v1"
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7
    cors_origins: list[str] = ["http://localhost:5173"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
