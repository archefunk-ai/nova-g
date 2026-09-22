"""Быстрый разбор текста по простым правилам — без обращения к Gemini.

Понимает частые формулировки без ИИ, чтобы не тратить дневную квоту.
Если уверенности нет — возвращает None, и вызывающий код обращается к Gemini.
"""

import re

from dateparser.search import search_dates

from . import config
from .nlp import clean_text

_HELP_WORDS = ("привет", "здравствуй", "что ты умеешь", "помощь", "/help")
_LIST_TASKS_WORDS = ("список дел", "покажи дела", "мои дела", "какие дела")
_AGENDA_WORDS = ("что у меня", "что запланировано", "мои планы", "планы на", "агенда", "повестка")
_DONE_RE = re.compile(r"\b(готово|сделал\w*|выполнил\w*|сделан\w*|отмет\w*)\D{0,10}?(\d{1,3})\b", re.IGNORECASE)
_EVENT_WORDS = (
    "встреча", "встретиться", "созвон", "созвониться", "звонок", "позвонить",
    "поход", "приём", "прием", "собеседование", "визит",
)
_TASK_WORDS = ("напомни", "нужно", "надо", "купить", "куплю", "сделать", "дело", "не забыть")
_EXPLICIT_TIME_RE = re.compile(r"\b([01]?\d|2[0-3])[:.][0-5]\d\b")

_SETTINGS = {
    "TIMEZONE": config.TIMEZONE,
    "RETURN_AS_TIMEZONE_AWARE": True,
    "PREFER_DATES_FROM": "future",
}


def _contains_any(text: str, words) -> bool:
    return any(w in text for w in words)


def _strip_task_words(title: str) -> str:
    """Убирает вводные слова-триггеры ('напомни', 'нужно', ...) из заголовка,
    если после этого остаётся непустой текст."""

    stripped = title
    for word in _TASK_WORDS:
        stripped = re.sub(rf"\b{re.escape(word)}\b", "", stripped, flags=re.IGNORECASE)
    stripped = re.sub(r"\s+", " ", stripped).strip(" ,.-")
    return stripped or title


def parse_command(text: str) -> dict | None:
    """Пытается понять сообщение без ИИ. None — не уверена, нужно спросить Gemini."""

    lowered = text.lower().strip()
    if not lowered:
        return None

    if _contains_any(lowered, _HELP_WORDS):
        return {"action": "help"}

    done_match = _DONE_RE.search(lowered)
    if done_match:
        return {"action": "done_task", "task_number": int(done_match.group(2))}

    if _contains_any(lowered, _LIST_TASKS_WORDS):
        return {"action": "list_tasks"}

    if _contains_any(lowered, _AGENDA_WORDS):
        return {"action": "agenda", "when_text": text}

    cleaned = clean_text(text)
    found = search_dates(cleaned, languages=["ru"], settings=_SETTINGS)

    if found:
        # search_dates часто разбивает дату и время на отдельные куски
        # ("сегодня" ... "в 22:00"), если между ними есть текст — собираем
        # их обратно в одну строку, иначе итоговый parse_datetime потеряет время.
        fragments = [fragment for fragment, _ in found]
        when_text = " ".join(fragments)

        title = cleaned
        for fragment in fragments:
            title = title.replace(fragment, "")
        title = re.sub(r"\s+", " ", title).strip(" ,.-")
        if not title:
            return None  # осталась только дата — непонятно, что за дело/событие

        has_explicit_time = bool(_EXPLICIT_TIME_RE.search(cleaned))
        if has_explicit_time or _contains_any(lowered, _EVENT_WORDS):
            return {"action": "add_event", "title": _strip_task_words(title), "when_text": when_text}
        return {"action": "add_task", "title": _strip_task_words(title), "when_text": when_text}

    if _contains_any(lowered, _TASK_WORDS):
        title = _strip_task_words(text.strip())
        if title:
            return {"action": "add_task", "title": title}

    return None
