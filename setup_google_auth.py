"""Первичный вход в Google для бота — без браузера на этой машине.

Использование в два шага:

1) python setup_google_auth.py url
   Покажет ссылку. Открой её на СВОЁМ телефоне/компьютере, войди в Google,
   разреши доступ. Тебя перебросит на адрес вида http://localhost/?code=...
   Страница не откроется (это нормально) — просто скопируй код после
   "code=" и до следующего "&" из адресной строки браузера.

2) python setup_google_auth.py code ВСТАВЬ_СЮДА_КОД
   Обменяет код на постоянный ключ доступа и сохранит token.json.

token.json нужно держать в секрете, как пароль.
"""

import sys

from google_auth_oauthlib.flow import Flow

from bot import config


def _build_flow() -> Flow:
    if not config.CREDENTIALS_PATH.exists():
        raise SystemExit(f"Не найден {config.CREDENTIALS_PATH}.")
    return Flow.from_client_secrets_file(
        str(config.CREDENTIALS_PATH),
        scopes=config.GOOGLE_SCOPES,
        redirect_uri="http://localhost",
    )


def show_url() -> None:
    flow = _build_flow()
    auth_url, _ = flow.authorization_url(access_type="offline", prompt="consent")
    print("Открой эту ссылку и войди в свой Google-аккаунт:\n")
    print(auth_url)
    print(
        "\nПосле разрешения доступа браузер попробует открыть "
        "http://localhost/?code=... и не сможет — это ожидаемо. "
        "Скопируй значение code из адресной строки и пришли его."
    )


def exchange_code(code: str) -> None:
    flow = _build_flow()
    flow.fetch_token(code=code)
    config.TOKEN_PATH.write_text(flow.credentials.to_json(), encoding="utf-8")
    print(f"Готово! Ключ доступа сохранён в {config.TOKEN_PATH}")


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "url":
        show_url()
    elif len(sys.argv) == 3 and sys.argv[1] == "code":
        exchange_code(sys.argv[2])
    else:
        print(__doc__)
