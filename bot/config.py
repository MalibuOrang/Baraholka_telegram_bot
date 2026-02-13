from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True, slots=True)
class Settings:
    bot_token: str
    admin_ids: set[int]
    db_path: Path
    moderation_chat_id: int | None
    publication_chat_id: int | None
    daily_ads_limit: int


def _parse_int_set(raw: str | None) -> set[int]:
    if not raw:
        return set()
    return {int(x.strip()) for x in raw.split(",") if x.strip()}


def _parse_optional_int(raw: str | None) -> int | None:
    if raw is None or raw.strip() == "":
        return None
    return int(raw.strip())


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    load_dotenv()
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise ValueError("BOT_TOKEN is required in .env")

    return Settings(
        bot_token=token,
        admin_ids=_parse_int_set(os.getenv("ADMIN_IDS")),
        db_path=Path(os.getenv("DB_PATH", "baraholka.db")),
        moderation_chat_id=_parse_optional_int(os.getenv("MODERATION_CHAT_ID")),
        publication_chat_id=_parse_optional_int(os.getenv("PUBLICATION_CHAT_ID")),
        daily_ads_limit=int(os.getenv("DAILY_ADS_LIMIT", "3")),
    )
