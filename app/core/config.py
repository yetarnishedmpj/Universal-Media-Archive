from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_environment: str
    mongodb_uri: str
    mongodb_db_name: str
    mongodb_timeout_ms: int
    seed_on_startup: bool
    seed_force_reset: bool
    page_size_default: int
    page_size_max: int
    enable_docs: bool
    cors_origins: list[str]
    base_dir: Path
    templates_dir: Path
    static_dir: Path


def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME", "Universal Media Archive"),
        app_environment=os.getenv("APP_ENVIRONMENT", "development"),
        mongodb_uri=os.getenv("MONGODB_URI", "mongodb://localhost:27017"),
        mongodb_db_name=os.getenv("MONGODB_DB_NAME", "universal_media_archive"),
        mongodb_timeout_ms=int(os.getenv("MONGODB_TIMEOUT_MS", "5000")),
        seed_on_startup=_as_bool(os.getenv("SEED_ON_STARTUP"), True),
        seed_force_reset=_as_bool(os.getenv("SEED_FORCE_RESET"), False),
        page_size_default=int(os.getenv("PAGE_SIZE_DEFAULT", "12")),
        page_size_max=int(os.getenv("PAGE_SIZE_MAX", "48")),
        enable_docs=_as_bool(os.getenv("ENABLE_DOCS"), True),
        cors_origins=[
            origin.strip()
            for origin in os.getenv("CORS_ORIGINS", "*").split(",")
            if origin.strip()
        ],
        base_dir=BASE_DIR,
        templates_dir=BASE_DIR / "app" / "templates",
        static_dir=BASE_DIR / "app" / "static",
    )


settings = get_settings()
