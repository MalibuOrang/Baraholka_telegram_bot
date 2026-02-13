from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class AdCreate:
    user_id: int
    username: str | None
    phone: str | None
    title: str
    description: str
    price_text: str
    price_value: float | None
    category: str
    photos: list[str]
    city: str


@dataclass(slots=True)
class AdRecord:
    id: int
    user_id: int
    username: str | None
    phone: str | None
    title: str
    description: str
    price_text: str
    price_value: float | None
    category: str
    photos: list[str]
    city: str
    status: str
    created_at: str
    published_at: str | None

    @classmethod
    def from_row(cls, row: Any, photos: list[str]) -> "AdRecord":
        return cls(
            id=row["id"],
            user_id=row["user_id"],
            username=row["username"],
            phone=row["phone"],
            title=row["title"],
            description=row["description"],
            price_text=row["price_text"],
            price_value=row["price_value"],
            category=row["category"],
            photos=photos,
            city=row["city"],
            status=row["status"],
            created_at=row["created_at"],
            published_at=row["published_at"],
        )
