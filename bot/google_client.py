"""Тонкая обёртка над Google Calendar API и Google Tasks API."""

from datetime import datetime, timedelta

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from . import config

_calendar_service = None
_tasks_service = None


def _load_credentials() -> Credentials:
    if not config.TOKEN_PATH.exists():
        raise RuntimeError(
            "Файл token.json не найден. Сначала запусти setup_google_auth.py, "
            "чтобы один раз войти в свой Google-аккаунт."
        )

    creds = Credentials.from_authorized_user_file(str(config.TOKEN_PATH), config.GOOGLE_SCOPES)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        config.TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")

    return creds


def get_calendar_service():
    global _calendar_service
    if _calendar_service is None:
        _calendar_service = build("calendar", "v3", credentials=_load_credentials())
    return _calendar_service


def get_tasks_service():
    global _tasks_service
    if _tasks_service is None:
        _tasks_service = build("tasks", "v1", credentials=_load_credentials())
    return _tasks_service


# ---------- Календарь ----------

def create_event(summary: str, start: datetime, end: datetime | None = None) -> dict:
    if end is None:
        end = start + timedelta(hours=1)

    body = {
        "summary": summary,
        "start": {"dateTime": start.isoformat(), "timeZone": config.TIMEZONE},
        "end": {"dateTime": end.isoformat(), "timeZone": config.TIMEZONE},
    }
    return get_calendar_service().events().insert(calendarId="primary", body=body).execute()


def list_events(time_min: datetime, time_max: datetime) -> list[dict]:
    response = (
        get_calendar_service()
        .events()
        .list(
            calendarId="primary",
            timeMin=time_min.isoformat(),
            timeMax=time_max.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    return response.get("items", [])


def delete_event(event_id: str) -> None:
    get_calendar_service().events().delete(calendarId="primary", eventId=event_id).execute()


# ---------- Задачи (Google Tasks) ----------

def _default_tasklist_id() -> str:
    result = get_tasks_service().tasklists().list(maxResults=1).execute()
    lists = result.get("items", [])
    if not lists:
        raise RuntimeError("В Google Tasks нет ни одного списка задач.")
    return lists[0]["id"]


def create_task(title: str, due: datetime | None = None, notes: str | None = None) -> dict:
    body: dict = {"title": title}
    if notes:
        body["notes"] = notes
    if due:
        # Google Tasks хранит due только как дату (UTC, полночь), без времени.
        body["due"] = due.strftime("%Y-%m-%dT00:00:00.000Z")

    return get_tasks_service().tasks().insert(tasklist=_default_tasklist_id(), body=body).execute()


def list_tasks(show_completed: bool = False) -> list[dict]:
    result = (
        get_tasks_service()
        .tasks()
        .list(tasklist=_default_tasklist_id(), showCompleted=show_completed, maxResults=100)
        .execute()
    )
    items = result.get("items", [])
    if not show_completed:
        items = [t for t in items if t.get("status") != "completed"]
    return items


def complete_task(task_id: str) -> None:
    tasklist_id = _default_tasklist_id()
    get_tasks_service().tasks().patch(
        tasklist=tasklist_id, task=task_id, body={"status": "completed"}
    ).execute()


def delete_task(task_id: str) -> None:
    tasklist_id = _default_tasklist_id()
    get_tasks_service().tasks().delete(tasklist=tasklist_id, task=task_id).execute()
