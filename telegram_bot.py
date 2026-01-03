#!/usr/bin/env python3

import os
import sys
import gettext
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

    localedir = root_dir / "locales"
    domain = "telegram_bot"
    default_interval = 30

    def normalize_language(value: str) -> str | None:
        v = value.strip().lower()
        if not v:
            return None

        if v in {"en", "eng", "english"}:
            return "en"
        if v in {"ru", "rus", "russian", "русский", "ру", "рус"}:
            return "ru"
        if v in {"sr", "ser", "serbian", "српски", "срп", "srpski", "srb", "srp"}:
            return "sr"

        return None

    def detect_language(update: Update) -> str:
        lang = (getattr(update.effective_user, "language_code", None) or "").lower()
        lang = lang.split("-")[0]
        lang = normalize_language(lang) or "en"
        return lang

    def get_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        lang = context.user_data.get("lang")
        if not lang:
            lang = detect_language(update)
            context.user_data["lang"] = lang
        return lang

    def get_translator(update: Update, context: ContextTypes.DEFAULT_TYPE) -> gettext.NullTranslations:
        lang = get_language(update, context)
        return gettext.translation(domain, localedir=str(localedir), languages=[lang], fallback=True)

    async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.message is None:
            return
        _ = get_translator(update, context).gettext
        await update.message.reply_text(
            _("Send a stop name to get upcoming routes for the next 30 minutes.")
        )

    async def stop_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.message is None or update.message.text is None:
            return

        _ = get_translator(update, context).gettext

        interval = context.user_data.get("interval", default_interval)

        stop_name_raw = update.message.text.strip()
        if not stop_name_raw:
            await update.message.reply_text(_("Please enter a stop name"))
            return

        dt = datetime.now()
        service_ids = detect_service_type(dt)
        if not service_ids:
            await update.message.reply_text(_("No matching service type found"))
            return

        primary_service_id = sorted(service_ids)[0]
        stop_name = transliterate(stop_name_raw)
        rows = get_schedule(primary_service_id, dt, stop_name, interval)

        if not rows:
            await update.message.reply_text(_("Not found"))
            return

        types = {0: "Tm 🚋", 3: "A  🚌", 11: "Tb 🚎"}
        lines: list[str] = []
        for row in rows[:40]:
            type_emoji = types.get(row.route_type, "Unknn")
            number = (row.route_short_name or "").ljust(5)
            headsign = row.trip_headsign or ""
            lines.append(f"{row.arrival_time[:5]} {type_emoji} {number} {headsign}".rstrip())

        await update.message.reply_text("\n".join(lines))

    async def interval_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.message is None:
            return

        translator = get_translator(update, context)
        _ = translator.gettext
        ngettext = translator.ngettext

        if not context.args:
            await update.message.reply_text(_("Usage: /interval MINUTES"))
            return

        try:
            minutes = int(context.args[0])
        except ValueError:
            await update.message.reply_text(_("Invalid interval"))
            return

        if minutes <= 0:
            await update.message.reply_text(_("Invalid interval"))
            return

        context.user_data["interval"] = minutes
        await update.message.reply_text(
            ngettext(
                "Interval set to %(minutes)s minute",
                "Interval set to %(minutes)s minutes",
                minutes,
            )
            % {"minutes": minutes}
        )

    async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.message is None:
            return

        translator = get_translator(update, context)
        _ = translator.gettext

        if not context.args:
            await update.message.reply_text(_("Usage: /language LANGUAGE"))
            return

        requested = " ".join(context.args)
        lang = normalize_language(requested)
        if not lang:
            await update.message.reply_text(_("Unknown language"))
            return

        context.user_data["lang"] = lang
        await update.message.reply_text(_("Language set to %(lang)s") % {"lang": lang})

    async def command_alias_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.message is None or update.message.text is None:
            return

        text = update.message.text.strip()
        if not text.startswith("/"):
            return

        parts = text.split()
        head = parts[0]
        if "@" in head:
            head = head.split("@", 1)[0]

        prev_args = getattr(context, "args", None)
        context.args = parts[1:]

        if head == "/интервал":
            try:
                return await interval_command(update, context)
            finally:
                context.args = prev_args

        if head == "/язык":
            try:
                return await language_command(update, context)
            finally:
                context.args = prev_args

        context.args = prev_args

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("start", help_command))

    app.add_handler(CommandHandler("interval", interval_command))
    app.add_handler(MessageHandler(filters.Regex(r"^/интервал(\s|$)"), command_alias_router))

    app.add_handler(CommandHandler("language", language_command))
    app.add_handler(CommandHandler("jezik", language_command))
    app.add_handler(MessageHandler(filters.Regex(r"^/язык(\s|$)"), command_alias_router))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, stop_query))
    app.run_polling()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
