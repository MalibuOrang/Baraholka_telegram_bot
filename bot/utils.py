from __future__ import annotations

from bot.database.models import AdRecord


def escape_md_v2(text: str) -> str:
    special = r"_*[]()~`>#+-=|{}.!"
    out = text
    for ch in special:
        out = out.replace(ch, f"\\{ch}")
    return out


def format_ad_md(ad: AdRecord, with_status: bool = False) -> str:
    status_map = {
        "pending": "На модерации",
        "published": "Опубликовано",
        "rejected": "Отклонено",
        "deleted": "Удалено",
        "draft": "Черновик",
    }
    status_text = status_map.get(ad.status, ad.status)
    parts = [
        f"*{escape_md_v2(ad.title)}*",
        "",
        f"Категория: {escape_md_v2(ad.category)}",
        f"Цена: {escape_md_v2(ad.price_text)}",
        f"Город/район: {escape_md_v2(ad.city)}",
        "",
        escape_md_v2(ad.description),
    ]
    if ad.phone:
        parts.append(f"\nТелефон: {escape_md_v2(ad.phone)}")
    if ad.username:
        parts.append(escape_md_v2(f"Опубликовал: @{ad.username}"))
    if with_status:
        parts.append(f"Статус: {escape_md_v2(status_text)}")
    return "\n".join(parts)
