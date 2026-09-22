"""Разбор свободных сообщений в команды через Gemini API."""

import json
import logging

import httpx

from . import config

logger = logging.getLogger(__name__)

_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-3.6-flash:generateContent"
)

_SYSTEM_PROMPT = """\
Ты — модуль разбора команд для Telegram-бота планировщика. Пользователь \
пишет сообщение обычным языком. Определи, что он хочет, и верни JSON по схеме.

Возможные action:
- add_task: добавить дело/напоминание (Google Tasks, без точного времени). \
title — текст дела. when_text — как пользователь описал срок ("завтра", \
"в пятницу"), только если назвал, иначе не указывай поле.
- list_tasks: показать список дел.
- done_task: отметить дело выполненным по номеру из последнего показанного \
списка. task_number — этот номер.
- add_event: добавить встречу/событие в календарь (обычно с точным временем, \
например "завтра в 18:00"). title — текст события. when_text — дата и время.
- agenda: спросить, что запланировано на день. when_text — про какой день, \
если не сказано явно — не указывай поле (будет "сегодня").
- help: пользователь спрашивает, что бот умеет, или поздоровался.
- unknown: не понятно, что хочет пользователь.

title и when_text бери как можно ближе к словам пользователя, на русском.
"""

_RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "action": {
            "type": "STRING",
            "enum": ["add_task", "list_tasks", "done_task", "add_event", "agenda", "help", "unknown"],
        },
        "title": {"type": "STRING"},
        "when_text": {"type": "STRING"},
        "task_number": {"type": "INTEGER"},
    },
    "required": ["action"],
}


async def interpret(text: str) -> dict:
    """Возвращает {"action": ..., "title": ..., "when_text": ..., "task_number": ...}."""

    if not config.GEMINI_API_KEY:
        return {"action": "unknown"}

    payload = {
        "system_instruction": {"parts": [{"text": _SYSTEM_PROMPT}]},
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {
            "response_mime_type": "application/json",
            "response_schema": _RESPONSE_SCHEMA,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=20, proxy=config.TELEGRAM_PROXY_URL or None) as client:
            response = await client.post(
                _ENDPOINT,
                params={"key": config.GEMINI_API_KEY},
                json=payload,
            )
        response.raise_for_status()
        data = response.json()
        raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
        parsed = json.loads(raw_text)
        if not isinstance(parsed, dict) or "action" not in parsed:
            return {"action": "unknown"}
        return parsed
    except httpx.HTTPStatusError as exc:
        logger.error("Gemini API error %s: %s", exc.response.status_code, exc.response.text)
        return {"action": "unknown"}
    except Exception:  # noqa: BLE001 - любая проблема с ИИ не должна ронять бота
        logger.exception("Gemini interpret failed")
        return {"action": "unknown"}
