"""Точка входа: запускает телеграм-бота (long polling)."""

import logging

from telegram.ext import Application, CommandHandler

from bot import config, handlers

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)


def main() -> None:
    if not config.TELEGRAM_BOT_TOKEN:
        raise RuntimeError(
            "Не найден TELEGRAM_BOT_TOKEN. Скопируй .env.example в .env и впиши туда токен от @BotFather."
        )

    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", handlers.start))
    app.add_handler(CommandHandler("help", handlers.help_command))
    app.add_handler(CommandHandler("task", handlers.add_task))
    app.add_handler(CommandHandler("tasks", handlers.list_tasks))
    app.add_handler(CommandHandler("done", handlers.done_task))
    app.add_handler(CommandHandler("event", handlers.add_event))
    app.add_handler(CommandHandler("agenda", handlers.agenda))

    print("Бот запущен. Останови его сочетанием Ctrl+C.")
    app.run_polling()


if __name__ == "__main__":
    main()
