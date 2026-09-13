# Телеграм-бот для дел и календаря

Бот-помощник в Telegram: добавляет дела в Google Tasks и события в Google
Calendar прямо из чата, ничего не нужно платить.

## Что умеет

- `/task Купить хлеб | завтра` — добавить дело (дату можно не указывать)
- `/tasks` — показать список дел
- `/done 2` — отметить дело №2 выполненным
- `/event Встреча с другом | завтра в 18:00` — создать событие в календаре
- `/agenda` — что запланировано на сегодня
- `/agenda завтра` — что запланировано на завтра
- `/help` — подсказка по командам

## Шаг 1. Создать бота в Telegram

1. Открой Telegram, найди `@BotFather`.
2. Напиши ему `/newbot`, придумай имя.
3. Он пришлёт токен вида `123456:ABC-DEF...` — сохрани его, он понадобится дальше.

## Шаг 2. Разрешить боту доступ к Google Calendar и Google Tasks

1. Зайди на https://console.cloud.google.com/ и создай новый проект (бесплатно).
2. В разделе **APIs & Services → Library** включи:
   - **Google Calendar API**
   - **Google Tasks API**
3. В разделе **APIs & Services → OAuth consent screen** выбери тип **External**,
   заполни название приложения (любое) и свою почту. На вопрос про пользователей
   добавь свой Google-аккаунт в **Test users**.
4. В разделе **APIs & Services → Credentials** нажми **Create Credentials →
   OAuth client ID**, тип приложения — **Desktop app**.
5. Скачай файл credentials и переименуй его в `credentials.json`, положи в
   корень проекта (рядом с `main.py`).

## Шаг 3. Установить зависимости

```bash
python -m venv venv
source venv/bin/activate   # на Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Шаг 4. Настроить .env

```bash
cp .env.example .env
```

Открой `.env` и впиши туда токен бота из Шага 1:

```
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TIMEZONE=Europe/Moscow
```

(Необязательно) Узнай свой Telegram ID у `@userinfobot` и впиши в
`ALLOWED_USER_ID` — тогда бот будет слушаться только тебя.

## Шаг 5. Один раз войти в Google

```bash
python setup_google_auth.py
```

Откроется браузер — войди в свой Google-аккаунт и разреши доступ.
После этого появится файл `token.json` — это ключ, которым бот будет
пользоваться постоянно.

## Шаг 6. Запустить бота

```bash
python main.py
```

Иди в Telegram, напиши своему боту `/start` — и пробуй команды.

## Шаг 7 (когда всё проверено). Поселить бота в интернете навсегда

Пока терминал открыт — бот работает. Чтобы он работал и когда компьютер
выключен, задеплой его на бесплатный хостинг, например:

- **Render.com** (Background Worker, free plan)
- **Railway.app** (free plan)

На хостинге:
1. Загрузи туда весь проект (кроме `.env`, `credentials.json`, `token.json` — они и так игнорируются git'ом).
2. Пропиши переменные окружения (`TELEGRAM_BOT_TOKEN`, `TIMEZONE`, `ALLOWED_USER_ID`) в настройках хостинга.
3. Отдельно (через Secret Files или переменные) добавь содержимое `credentials.json` и `token.json` — они нужны боту для входа в Google.
4. Команда запуска: `python main.py`.

## Если что-то не понятно

Каждая команда бота присылает понятное сообщение об ошибке — просто
перешли его мне, и я помогу разобраться.
