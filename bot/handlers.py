"""Команды телеграм-бота."""

import functools
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import ContextTypes

from . import config, google_client, nlu
from .nlp import parse_datetime

HELP_TEXT = (
    "Привет! Я помогу тебе не забывать дела 🙂\n\n"
    "Можешь писать обычными словами — например «напомни завтра купить хлеб» "
    "или «встреча с другом в пятницу в 18:00» — я пойму.\n\n"
    "Или точными командами:\n\n"
    "Дела (Google Tasks):\n"
    "/task Купить хлеб | завтра — добавить дело\n"
    "/task Позвонить маме — добавить дело без даты\n"
    "/tasks — показать список дел\n"
    "/done 2 — отметить дело №2 выполненным\n\n"
    "События (Google Calendar):\n"
    "/event Встреча с другом | завтра в 18:00 — создать событие\n"
    "/agenda — что у меня сегодня\n"
    "/agenda завтра — что у меня завтра\n\n"
    "/help — показать эту подсказку"
)

# Простое хранилище «последнего списка» на чат, чтобы /done N и /agenda работали по номерам.
_last_tasks: dict[int, list[str]] = {}
_last_events: dict[int, list[str]] = {}


def restricted(handler):
    """Если в .env задан ALLOWED_USER_ID — отвечаем только этому человеку."""

    @functools.wraps(handler)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if config.ALLOWED_USER_ID is not None:
            user = update.effective_user
            if user is None or user.id != config.ALLOWED_USER_ID:
                await update.message.reply_text("Извини, этот бот настроен только для одного хозяина 🙂")
                return
        return await handler(update, context)

    return wrapper


def _friendly_error(exc: Exception) -> str:
    return f"Что-то пошло не так: {exc}"


# ---------- Общая логика (используется и командами, и свободным текстом) ----------


async def _do_add_task(update: Update, title: str, when_text: str = "") -> None:
    title = title.strip()
    if not title:
        await update.message.reply_text(
            "Напиши так: /task Купить хлеб | завтра\n(дату можно не указывать)"
        )
        return

    due = parse_datetime(when_text) if when_text else None
    if when_text and due is None:
        await update.message.reply_text(f"Не поняла дату «{when_text}» 🤔 Попробуй иначе, например «завтра».")
        return

    try:
        google_client.create_task(title, due=due)
    except Exception as exc:  # noqa: BLE001 - показываем причину пользователю
        await update.message.reply_text(_friendly_error(exc))
        return

    when_msg = f" (срок: {due.strftime('%d.%m.%Y')})" if due else ""
    await update.message.reply_text(f"Готово! Добавила дело: «{title}»{when_msg} ✅")


async def _do_list_tasks(update: Update) -> None:
    try:
        tasks = google_client.list_tasks()
    except Exception as exc:  # noqa: BLE001
        await update.message.reply_text(_friendly_error(exc))
        return

    if not tasks:
        await update.message.reply_text("Дел пока нет — можно отдыхать 🎉")
        return

    chat_id = update.effective_chat.id
    _last_tasks[chat_id] = [task["id"] for task in tasks]

    lines = ["Твои дела:"]
    for i, task in enumerate(tasks, start=1):
        due = task.get("due")
        due_str = f" (до {due[:10]})" if due else ""
        lines.append(f"{i}. {task['title']}{due_str}")
    lines.append("\nОтметить готовым: /done <номер>")
    await update.message.reply_text("\n".join(lines))


async def _do_done_task(update: Update, number: int | None) -> None:
    chat_id = update.effective_chat.id
    if not number:
        await update.message.reply_text("Напиши так: /done 2 (сначала посмотри номера через /tasks)")
        return

    index = number - 1
    task_ids = _last_tasks.get(chat_id, [])
    if index < 0 or index >= len(task_ids):
        await update.message.reply_text("Такого номера нет. Сначала вызови /tasks.")
        return

    try:
        google_client.complete_task(task_ids[index])
    except Exception as exc:  # noqa: BLE001
        await update.message.reply_text(_friendly_error(exc))
        return

    await update.message.reply_text("Отлично, отметила как сделано! 🎉")


async def _do_add_event(update: Update, title: str, when_text: str) -> None:
    title = title.strip()
    if not title or not when_text:
        await update.message.reply_text(
            "Напиши так: /event Встреча с другом | завтра в 18:00"
        )
        return

    start = parse_datetime(when_text)
    if start is None:
        await update.message.reply_text(f"Не поняла дату «{when_text}» 🤔 Попробуй иначе.")
        return

    try:
        google_client.create_event(title, start)
    except Exception as exc:  # noqa: BLE001
        await update.message.reply_text(_friendly_error(exc))
        return

    await update.message.reply_text(
        f"Готово! Добавила в календарь: «{title}» на {start.strftime('%d.%m.%Y %H:%M')} 📅"
    )


async def _do_agenda(update: Update, when_text: str = "сегодня") -> None:
    day = parse_datetime(when_text or "сегодня")
    if day is None:
        await update.message.reply_text(f"Не поняла дату «{when_text}» 🤔")
        return

    day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)

    try:
        events = google_client.list_events(day_start, day_end)
    except Exception as exc:  # noqa: BLE001
        await update.message.reply_text(_friendly_error(exc))
        return

    if not events:
        await update.message.reply_text(f"На {day_start.strftime('%d.%m.%Y')} ничего не запланировано 🌤")
        return

    chat_id = update.effective_chat.id
    _last_events[chat_id] = [event["id"] for event in events]

    lines = [f"Планы на {day_start.strftime('%d.%m.%Y')}:"]
    for i, event in enumerate(events, start=1):
        start_info = event["start"].get("dateTime", event["start"].get("date"))
        time_str = start_info[11:16] if "T" in start_info else "весь день"
        lines.append(f"{i}. {time_str} — {event.get('summary', '(без названия)')}")
    await update.message.reply_text("\n".join(lines))


# ---------- Команды ----------


@restricted
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP_TEXT)


@restricted
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP_TEXT)


@restricted
async def add_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    raw = " ".join(context.args)
    if "|" in raw:
        title, when_text = (part.strip() for part in raw.split("|", 1))
    else:
        title, when_text = raw.strip(), ""
    await _do_add_task(update, title, when_text)


@restricted
async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _do_list_tasks(update)


@restricted
async def done_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    number = int(context.args[0]) if context.args and context.args[0].isdigit() else None
    await _do_done_task(update, number)


@restricted
async def add_event(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    raw = " ".join(context.args)
    if "|" not in raw:
        await update.message.reply_text("Напиши так: /event Встреча с другом | завтра в 18:00")
        return
    title, when_text = (part.strip() for part in raw.split("|", 1))
    await _do_add_event(update, title, when_text)


@restricted
async def agenda(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    when_text = " ".join(context.args) if context.args else "сегодня"
    await _do_agenda(update, when_text)


# ---------- Свободный текст (через Gemini) ----------


@restricted
async def freeform_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text or ""
    parsed = await nlu.interpret(text)
    action = parsed.get("action", "unknown")

    if action == "add_task":
        await _do_add_task(update, parsed.get("title", ""), parsed.get("when_text", ""))
    elif action == "list_tasks":
        await _do_list_tasks(update)
    elif action == "done_task":
        await _do_done_task(update, parsed.get("task_number"))
    elif action == "add_event":
        await _do_add_event(update, parsed.get("title", ""), parsed.get("when_text", ""))
    elif action == "agenda":
        await _do_agenda(update, parsed.get("when_text", "сегодня"))
    elif action == "help":
        await update.message.reply_text(HELP_TEXT)
    else:
        await update.message.reply_text(
            "Не поняла, что нужно сделать 🤔 Напиши иначе, или посмотри /help"
        )
