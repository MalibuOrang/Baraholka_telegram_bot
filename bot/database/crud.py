from __future__ import annotations

import asyncio
import json
from pathlib import Path

import aiosqlite
from sqlite3 import OperationalError

from bot.database.models import AdCreate, AdRecord

_DB_PATH = Path("baraholka.db")
_DB: aiosqlite.Connection | None = None
_DB_LOCK = asyncio.Lock()


def configure(db_path: Path) -> None:
    global _DB_PATH
    _DB_PATH = db_path


async def _get_db() -> aiosqlite.Connection:
    global _DB
    if _DB is None:
        async with _DB_LOCK:
            if _DB is None:
                _DB = await aiosqlite.connect(_DB_PATH)
                _DB.row_factory = aiosqlite.Row
                await _DB.execute("PRAGMA journal_mode=WAL;")
    return _DB


async def close_db() -> None:
    global _DB
    if _DB is not None:
        await _DB.close()
        _DB = None


async def init_db() -> None:
    db = await _get_db()
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS ads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT,
            phone TEXT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            price_text TEXT NOT NULL,
            price_value REAL,
            category TEXT NOT NULL,
            photos_json TEXT NOT NULL DEFAULT '[]',
            city TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            published_at TEXT,
            publication_chat_id INTEGER,
            publication_message_ids_json TEXT NOT NULL DEFAULT '[]'
        )
        """
    )
    await db.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS ads_fts USING fts5(
            title, description, city, content='ads', content_rowid='id'
        )
        """
    )
    await db.execute(
        """
        CREATE TRIGGER IF NOT EXISTS ads_ai AFTER INSERT ON ads BEGIN
            INSERT INTO ads_fts(rowid, title, description, city)
            VALUES (new.id, new.title, new.description, new.city);
        END;
        """
    )
    await db.execute(
        """
        CREATE TRIGGER IF NOT EXISTS ads_ad AFTER DELETE ON ads BEGIN
            INSERT INTO ads_fts(ads_fts, rowid, title, description, city)
            VALUES ('delete', old.id, old.title, old.description, old.city);
        END;
        """
    )
    await db.execute(
        """
        CREATE TRIGGER IF NOT EXISTS ads_au AFTER UPDATE ON ads BEGIN
            INSERT INTO ads_fts(ads_fts, rowid, title, description, city)
            VALUES ('delete', old.id, old.title, old.description, old.city);
            INSERT INTO ads_fts(rowid, title, description, city)
            VALUES (new.id, new.title, new.description, new.city);
        END;
        """
    )
    await _ensure_column(
        db,
        "ads",
        "publication_chat_id",
        "INTEGER",
    )
    await _ensure_column(
        db,
        "ads",
        "publication_message_ids_json",
        "TEXT NOT NULL DEFAULT '[]'",
    )
    await db.execute("CREATE INDEX IF NOT EXISTS idx_ads_user_id ON ads(user_id)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_ads_status ON ads(status)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_ads_category ON ads(category)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_ads_city ON ads(city)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_ads_created_at ON ads(created_at)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_ads_status_category ON ads(status, category)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_ads_status_city ON ads(status, city)")
    await db.commit()


async def _ensure_column(
    db: aiosqlite.Connection,
    table_name: str,
    column_name: str,
    column_def: str,
) -> None:
    cursor = await db.execute(f"PRAGMA table_info({table_name})")
    rows = await cursor.fetchall()
    existing = {row[1] for row in rows}
    if column_name not in existing:
        await db.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}")


async def count_ads_last_24h(user_id: int) -> int:
    db = await _get_db()
    cursor = await db.execute(
        """
        SELECT COUNT(*)
        FROM ads
        WHERE user_id = ?
          AND created_at >= datetime('now', '-1 day')
        """,
        (user_id,),
    )
    row = await cursor.fetchone()
    return int(row[0]) if row else 0


async def create_ad(ad: AdCreate) -> int:
    db = await _get_db()
    cursor = await db.execute(
        """
        INSERT INTO ads (
            user_id, username, phone, title, description, price_text,
            price_value, category, photos_json, city, status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
        """,
        (
            ad.user_id,
            ad.username,
            ad.phone,
            ad.title,
            ad.description,
            ad.price_text,
            ad.price_value,
            ad.category,
            json.dumps(ad.photos, ensure_ascii=True),
            ad.city,
        ),
    )
    await db.commit()
    return int(cursor.lastrowid)


async def get_ad_by_id(ad_id: int) -> AdRecord | None:
    result = await get_ad_full_by_id(ad_id)
    return result[0] if result else None


async def get_ad_full_by_id(ad_id: int) -> tuple[AdRecord, int | None, list[int]] | None:
    db = await _get_db()
    cursor = await db.execute("SELECT * FROM ads WHERE id = ?", (ad_id,))
    row = await cursor.fetchone()
    if not row:
        return None
    photos = json.loads(row["photos_json"] or "[]")
    ad = AdRecord.from_row(row, photos)
    publication_chat_id = row["publication_chat_id"]
    message_ids = json.loads(row["publication_message_ids_json"] or "[]")
    return ad, publication_chat_id, [int(x) for x in message_ids]


async def get_user_ads(user_id: int, limit: int = 20) -> list[AdRecord]:
    db = await _get_db()
    cursor = await db.execute(
        """
        SELECT * FROM ads
        WHERE user_id = ? AND status != 'deleted'
        ORDER BY id DESC
        LIMIT ?
        """,
        (user_id, limit),
    )
    rows = await cursor.fetchall()
    return [
        AdRecord.from_row(row, json.loads(row["photos_json"] or "[]"))
        for row in rows
    ]


async def search_ads(query: str, limit: int = 20) -> list[AdRecord]:
    cleaned = _sanitize_fts_query(query)
    if not cleaned:
        return []
    db = await _get_db()
    try:
        cursor = await db.execute(
            """
            SELECT a.*
            FROM ads_fts f
            JOIN ads a ON a.id = f.rowid
            WHERE a.status = 'published' AND f MATCH ?
            ORDER BY a.id DESC
            LIMIT ?
            """,
            (cleaned, limit),
        )
        rows = await cursor.fetchall()
    except OperationalError:
        # Fallback to LIKE if FTS query fails for any reason
        pattern = f"%{query}%"
        cursor = await db.execute(
            """
            SELECT * FROM ads
            WHERE status = 'published'
              AND (title LIKE ? OR description LIKE ? OR city LIKE ?)
            ORDER BY id DESC
            LIMIT ?
            """,
            (pattern, pattern, pattern, limit),
        )
        rows = await cursor.fetchall()
    return [
        AdRecord.from_row(row, json.loads(row["photos_json"] or "[]"))
        for row in rows
    ]


def _sanitize_fts_query(query: str) -> str:
    tokens = [t.strip() for t in query.replace("\n", " ").split(" ") if t.strip()]
    if not tokens:
        return ""
    safe_tokens: list[str] = []
    for t in tokens:
        t = t.replace('"', '""')
        safe_tokens.append(f'"{t}"')
    return " AND ".join(safe_tokens)


async def get_ads_by_category(category: str, limit: int = 20) -> list[AdRecord]:
    db = await _get_db()
    cursor = await db.execute(
        """
        SELECT * FROM ads
        WHERE status = 'published' AND category = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (category, limit),
    )
    rows = await cursor.fetchall()
    return [
        AdRecord.from_row(row, json.loads(row["photos_json"] or "[]"))
        for row in rows
    ]


async def delete_user_ad(ad_id: int, user_id: int) -> bool:
    db = await _get_db()
    cursor = await db.execute(
        """
        UPDATE ads
        SET status = 'deleted'
        WHERE id = ? AND user_id = ? AND status != 'deleted'
        """,
        (ad_id, user_id),
    )
    await db.commit()
    return cursor.rowcount > 0


async def list_ads(status: str | None = None, limit: int = 50) -> list[AdRecord]:
    db = await _get_db()
    if status:
        cursor = await db.execute(
            "SELECT * FROM ads WHERE status = ? ORDER BY id DESC LIMIT ?",
            (status, limit),
        )
    else:
        cursor = await db.execute(
            "SELECT * FROM ads ORDER BY id DESC LIMIT ?",
            (limit,),
        )
    rows = await cursor.fetchall()
    return [
        AdRecord.from_row(row, json.loads(row["photos_json"] or "[]"))
        for row in rows
    ]


async def update_ad_status(ad_id: int, new_status: str) -> bool:
    db = await _get_db()
    if new_status == "published":
        cursor = await db.execute(
            """
            UPDATE ads
            SET status = 'published', published_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (ad_id,),
        )
    else:
        cursor = await db.execute(
            "UPDATE ads SET status = ? WHERE id = ?",
            (new_status, ad_id),
        )
    await db.commit()
    return cursor.rowcount > 0


async def update_ad(
    ad_id: int,
    phone: str | None,
    title: str,
    description: str,
    price_text: str,
    price_value: float | None,
    category: str,
    city: str,
    photos: list[str],
) -> None:
    db = await _get_db()
    await db.execute(
        """
        UPDATE ads
        SET title = ?,
            description = ?,
            phone = ?,
            price_text = ?,
            price_value = ?,
            category = ?,
            city = ?,
            photos_json = ?,
            status = 'pending',
            published_at = NULL,
            publication_chat_id = NULL,
            publication_message_ids_json = '[]'
        WHERE id = ?
        """,
        (
            title,
            description,
            phone,
            price_text,
            price_value,
            category,
            city,
            json.dumps(photos, ensure_ascii=True),
            ad_id,
        ),
    )
    await db.commit()


async def set_publication_info(ad_id: int, chat_id: int, message_ids: list[int]) -> None:
    db = await _get_db()
    await db.execute(
        """
        UPDATE ads
        SET publication_chat_id = ?, publication_message_ids_json = ?
        WHERE id = ?
        """,
        (chat_id, json.dumps(message_ids, ensure_ascii=True), ad_id),
    )
    await db.commit()


async def get_publication_info(ad_id: int) -> tuple[int, list[int]] | None:
    db = await _get_db()
    cursor = await db.execute(
        """
        SELECT publication_chat_id, publication_message_ids_json
        FROM ads
        WHERE id = ?
        """,
        (ad_id,),
    )
    row = await cursor.fetchone()
    if not row or row["publication_chat_id"] is None:
        return None
    message_ids = json.loads(row["publication_message_ids_json"] or "[]")
    return int(row["publication_chat_id"]), [int(x) for x in message_ids]
