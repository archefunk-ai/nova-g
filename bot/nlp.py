"""Разбор дат и времени из обычных русских фраз ('завтра в 14:00', 'в пятницу')."""

import re
from datetime import datetime

import dateparser
from dateparser.search import search_dates

from . import config

# dateparser не понимает "22.00" как время — принимает за дату/игнорирует.
_DOT_TIME = re.compile(r"(?<!\d)([01]?\d|2[0-3])\.([0-5]\d)(?!\.\d)(?!\d)")
# "вечером"/"ближайшую" рядом с днём недели или временем полностью ломают разбор.
_NEAREST = re.compile(r"\bближайш\w*\b", re.IGNORECASE)
_TIME_OF_DAY = re.compile(r"\bутром\b|\bднём\b|\bднем\b|\bвечером\b|\bночью\b", re.IGNORECASE)


def _clean(text: str) -> str:
    text = _DOT_TIME.sub(lambda m: f"{m.group(1)}:{m.group(2)}", text)
    text = _NEAREST.sub("", text)
    text = _TIME_OF_DAY.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


def clean_text(text: str) -> str:
    """Публичная обёртка над _clean — переиспользуется в rules.py."""
    return _clean(text)


def parse_datetime(text: str) -> datetime | None:
    settings = {
        "TIMEZONE": config.TIMEZONE,
        "RETURN_AS_TIMEZONE_AWARE": True,
        "PREFER_DATES_FROM": "future",
    }
    cleaned = _clean(text)

    result = dateparser.parse(cleaned, languages=["ru"], settings=settings)
    if result is not None:
        return result

    # Если Gemini подмешал в дату лишние слова ("с Альбертом", "с друзьями"),
    # dateparser.parse сдаётся на всей фразе целиком — ищем дату внутри неё.
    found = search_dates(cleaned, languages=["ru"], settings=settings)
    return found[0][1] if found else None
