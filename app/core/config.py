from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel


load_dotenv(Path(__file__).resolve().parents[2] / ".env")


class Settings(BaseModel):
    openai_enabled: bool = False
    openai_api_key: str | None = None
    openai_model: str = "gpt-5"
    cors_origins: tuple[str, ...] = ("*",)


def _csv_env(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    raw = os.getenv(name)
    if not raw:
        return default
    return tuple(value.strip() for value in raw.split(",") if value.strip())


def get_settings() -> Settings:
    return Settings(
        openai_enabled=os.getenv("OPENAI_ENABLED", "false").lower() == "true",
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-5"),
        cors_origins=_csv_env("CORS_ORIGINS", ("*",)),
    )
