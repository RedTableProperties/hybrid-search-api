from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Cache
    CACHE_TTL: int = 300

    # Search / Faiss
    DEFAULT_EF: int = 64
    MAX_CANDIDATE_IDS: int = 15000
    VECTOR_DIMS: tuple[int, ...] = (768, 1024)

    # Circuit breakers
    POSTGRES_CIRCUIT_FAIL_MAX: int = 5
    POSTGRES_CIRCUIT_RESET_TIMEOUT: int = 30
    FAISS_CIRCUIT_FAIL_MAX: int = 3
    FAISS_CIRCUIT_RESET_TIMEOUT: int = 15

    # Rate limiting
    SEARCH_RATE_LIMIT: str = "300/minute"
    SEARCH_RATE_LIMIT_BURST: int = 50

    # Cache warming
    ENABLE_CACHE_WARMING: bool = True
    CACHE_WARMING_INTERVAL_HOURS: int = 6

    # Connections (optional for local tests)
    DATABASE_URL: str = "postgresql://localhost/search"
    REDIS_URL: str = "redis://localhost:6379/0"
    FAISS_INDEX_PATH: str = "data/faiss.index"

    @property
    def search_refill_rate(self) -> float:
        """Tokens per second derived from strings like '300/minute'."""
        count, period = self.SEARCH_RATE_LIMIT.split("/")
        n = int(count.strip())
        unit = period.strip().lower()
        if unit in ("minute", "min"):
            return n / 60.0
        if unit in ("second", "sec"):
            return float(n)
        raise ValueError(f"Unsupported rate limit period: {unit}")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()