"""Запусти этот файл ОДИН РАЗ на своём компьютере, чтобы разрешить боту
доступ к твоему Google Calendar и Google Tasks.

Перед запуском:
1. Скачай файл credentials.json из Google Cloud Console (OAuth client ID,
   тип приложения — Desktop app) и положи его в корень проекта.
2. Установи зависимости: pip install -r requirements.txt

Что произойдёт:
- Откроется браузер, попросит войти в Google-аккаунт и разрешить доступ.
- После подтверждения появится файл token.json — это и есть "ключ",
  которым бот будет пользоваться постоянно (пока ты его не отзовёшь).

token.json нужно держать в секрете, как пароль — не выкладывай его никуда.
"""

from google_auth_oauthlib.flow import InstalledAppFlow

from bot import config


def main() -> None:
    if not config.CREDENTIALS_PATH.exists():
        raise SystemExit(
            f"Не найден {config.CREDENTIALS_PATH}. Скачай credentials.json из Google Cloud Console "
            "и положи его в корень проекта рядом с этим файлом."
        )

    flow = InstalledAppFlow.from_client_secrets_file(
        str(config.CREDENTIALS_PATH), config.GOOGLE_SCOPES
    )
    creds = flow.run_local_server(port=0)

    config.TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
    print(f"Готово! Ключ доступа сохранён в {config.TOKEN_PATH}")


if __name__ == "__main__":
    main()
