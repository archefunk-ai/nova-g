"""Разбор свободных сообщений (текст и голос) в команды через Gemini API."""

import asyncio
import base64
import json
import logging
import re

import httpx

from . import config

logger = logging.getLogger(__name__)

# Бесплатный тариф Gemini иногда отвечает 429 с "Please retry in Ns" —
# это короткое ограничение по скорости (не дневной лимит), стоит подождать и повторить.
_RETRY_DELAY_RE = re.compile(r"retry in ([\d.]+)s", re.IGNORECASE)
_MAX_RETRIES = 2

_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-3.6-flash:generateContent"
)

_SYSTEM_PROMPT = """\
Ты — модуль разбора команд для Telegram-бота планировщика. Пользователь \
пишет или наговаривает голосом сообщение обычным языком (если это аудио — \
сначала распознай речь). Определи, что он хочет, и верни JSON по схеме.

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
- unknown: не понятно, что хочет пользователь, или речь неразборчива.

Важно: пользователь редко говорит "добавь" или "напомни" явно — обычно просто \
описывает дело или планы своими словами, как будто говорит другу. Считай это \
командой добавить дело/событие, а не unknown. Примеры, которые нужно понимать \
как add_event: "мы должны созвониться с Альбертом в 22:00 сегодня", "сегодня \
вечером созвон с Альбертом", "в субботу поход в театр". Используй unknown, \
только если сообщение вообще не про дела, планы, встречи или списки дел \
(например случайные слова, шум, посторонний разговор).

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


async def _call_gemini(parts: list[dict]) -> dict:
    """Отправляет parts (текст и/или аудио) в Gemini и разбирает JSON-ответ."""

    if not config.GEMINI_API_KEY:
        return {"action": "unknown"}

    payload = {
        "system_instruction": {"parts": [{"text": _SYSTEM_PROMPT}]},
        "contents": [{"parts": parts}],
        "generationConfig": {
            "response_mime_type": "application/json",
            "response_schema": _RESPONSE_SCHEMA,
        },
    }

    for attempt in range(_MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=30, proxy=config.TELEGRAM_PROXY_URL or None) as client:
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
            body = exc.response.text
            logger.error("Gemini API error %s: %s", exc.response.status_code, body)
            if exc.response.status_code == 429 and attempt < _MAX_RETRIES:
                match = _RETRY_DELAY_RE.search(body)
                delay = float(match.group(1)) if match else 5.0
                await asyncio.sleep(min(delay, 15.0) + 1)
                continue
            return {"action": "unknown"}
        except Exception:  # noqa: BLE001 - любая проблема с ИИ не должна ронять бота
            logger.exception("Gemini interpret failed")
            return {"action": "unknown"}
    return {"action": "unknown"}


async def interpret(text: str) -> dict:
    """Возвращает {"action": ..., "title": ..., "when_text": ..., "task_number": ...}."""

    return await _call_gemini([{"text": text}])


async def interpret_audio(audio_bytes: bytes, mime_type: str = "audio/ogg") -> dict:
    """То же самое, но на входе — голосовое сообщение (Gemini сам распознаёт речь)."""

    audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
    return await _call_gemini([{"inline_data": {"mime_type": mime_type, "data": audio_b64}}])
