from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent
REFERENCE_DIR = BASE_DIR / "reference"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    db_url: str = "sqlite:///./blueprints.db"
    log_level: str = "INFO"
    log_mode: str = "dev"
    scraper_rate_limit_delay: float = 1.0
    scraper_progress_db: Path = BASE_DIR / "scraper_progress.db"
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = ""
    api_rate_limit_per_minute: int = 60
    target_game_version: tuple[int, int, int] = (1, 1, 110)


settings = Settings()
