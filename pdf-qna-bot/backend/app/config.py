from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gemini_api_key: str = ""
    gen_model: str = "gemini-2.0-flash"
    embed_model: str = "gemini-embedding-001"
    chroma_path: str = "chroma_db"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    top_k: int = 5
    max_upload_mb: int = 25
    cors_origins: list[str] = ["http://localhost:4200"]


settings = Settings()
