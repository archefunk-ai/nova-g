import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TIMEZONE = os.getenv("TIMEZONE", "Europe/Moscow")

_allowed_user_id = os.getenv("ALLOWED_USER_ID", "").strip()
ALLOWED_USER_ID = int(_allowed_user_id) if _allowed_user_id else None

CREDENTIALS_PATH = BASE_DIR / "credentials.json"
TOKEN_PATH = BASE_DIR / "token.json"

GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/tasks",
]
