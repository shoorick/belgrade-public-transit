#!/usr/bin/env python3

import os
import sys
from datetime import datetime
from pathlib import Path


def main() -> int:
    root_dir = Path(__file__).resolve().parent
    src_dir = root_dir / "src"
    sys.path.insert(0, str(src_dir))

    from dotenv import load_dotenv
    load_dotenv()

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Missing TELEGRAM_BOT_TOKEN", file=sys.stderr)
        return 1

    from telegram import Update
    from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

    from public_transit.schedule import detect_service_type, get_schedule, transliterate

    HELP_TEXT = {
        "en": "Send a stop name to get upcoming routes for the next 30 minutes.",
        "ru": "Напишите название остановки, чтобы получить список маршрутов, проходящих через неё в ближайшие полчаса",
        "sr": "Pošaljite naziv stajališta da biste dobili polaske za narednih 30 minuta.",
    }

    NOT_FOUND_TEXT = {
        "en": "Not found",
        "ru": "Ничего не найдено",
        "sr": "Ništa nije pronađeno",
    }

    EMPTY_STOP_TEXT = {
        "en": "Please enter a stop name",
        "ru": "Введите название остановки",
        "sr": "Unesite naziv stajališta",
    }

    def translate(dictionary: dict[str, str], update: Update) -> str:
        lang = (getattr(update.effective_user, "language_code", None) or "").lower()
        lang = lang.split("-")[0]
        return dictionary.get(lang, dictionary["en"])

    async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.message is None:
            return
        await update.message.reply_text(translate(HELP_TEXT, update))

    async def stop_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.message is None or update.message.text is None:
            return

        stop_name_raw = update.message.text.strip()
        if not stop_name_raw:
            await update.message.reply_text(translate(EMPTY_STOP_TEXT, update))
            return

        dt = datetime.now()
        service_ids = detect_service_type(dt)
        if not service_ids:
            await update.message.reply_text("No matching service_id found")
            return

        primary_service_id = sorted(service_ids)[0]
        stop_name = transliterate(stop_name_raw)
        rows = get_schedule(primary_service_id, dt, stop_name, 30)

        if not rows:
            await update.message.reply_text(translate(NOT_FOUND_TEXT, update))
            return

        types = {0: "Tm 🚋", 3: "A  🚌", 11: "Tb 🚎"}
        lines: list[str] = []
        for row in rows[:40]:
            type_emoji = types.get(row.route_type, "Unknn")
            number = (row.route_short_name or "").ljust(5)
            headsign = row.trip_headsign or ""
            lines.append(f"{row.arrival_time[:5]} {type_emoji} {number} {headsign}".rstrip())

        await update.message.reply_text("\n".join(lines))

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("start", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, stop_query))
    app.run_polling()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
