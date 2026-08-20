from pathlib import Path
from typing import List, Literal
from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directory configuration
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
ENV_PATH = BASE_DIR / ".env"


class Settings(BaseSettings):
    """Application settings using Pydantic BaseSettings for environment variable management."""

    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database Settings
    POSTGRES_USER: str = "user"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_SERVER: str = "db"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "lang_tutor_db"

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        """Constructs the asynchronous PostgreSQL database URL."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Application Settings
    DEBUG: bool = True
    PROJECT_NAME: str = "Linguaml API"

    # JWT Settings
    SECRET_KEY: str = "1111"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # ChromaDB Settings
    CHROMA_HOST: str = "chroma"
    CHROMA_PORT: int = 8000

    # Gemini LLM Settings
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL_NAME: str = "gemini-3.1-flash-lite"

    # CORS Settings
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # Script Batch Sizes
    BATCH_SIZE_RULES: int = 20
    BATCH_SIZE_EXERCISES: int = 30

    # User Levels & Paths
    VALID_USER_LEVELS: List[Literal["A1", "A2", "B1", "B2"]] = ["A1", "A2", "B1", "B2"]
    DATA_PATH: Path = BASE_DIR / "data" / "grammar_annotated"


settings = Settings()
