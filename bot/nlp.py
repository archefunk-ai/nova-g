"""Разбор дат и времени из обычных русских фраз ('завтра в 14:00', 'в пятницу')."""

from datetime import datetime

import dateparser

from . import config


def parse_datetime(text: str) -> datetime | None:
    settings = {
        "TIMEZONE": config.TIMEZONE,
        "RETURN_AS_TIMEZONE_AWARE": True,
        "PREFER_DATES_FROM": "future",
    }
    return dateparser.parse(text, languages=["ru"], settings=settings)
