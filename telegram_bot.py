#!/usr/bin/env python3

import gettext
import logging
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

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
    from telegram.constants import ParseMode
    from telegram.error import NetworkError
    from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters
    from telegram.helpers import escape_markdown

    from public_transit.config import read_config
    from public_transit.schedule import detect_service_type, get_schedule, transliterate
    import public_transit.project as project

    logger = logging.getLogger(__name__)

    localedir = root_dir / "locales"
    domain = "telegram_bot"
    default_interval = 30

    config = read_config(root_dir)
    lat_delta = float(config.geo.bbox.lat_delta)
    lon_delta = float(config.geo.bbox.lon_delta)

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
        interval = context.user_data.get("interval", default_interval)
        translator = get_translator(update, context)
        ngettext = translator.ngettext
        await update.message.reply_text(
            ngettext(
                "Send a stop name or code to get upcoming routes for the next %(interval)s minute.",
                "Send a stop name or code to get upcoming routes for the next %(interval)s minutes.",
                interval,
            )
            % {"interval": interval}
        )

    async def stop_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.message is None or update.message.text is None:
            return

        _ = get_translator(update, context).gettext

        interval = context.user_data.get("interval", default_interval)

        stop_name_raw = update.message.text.strip()
        if not stop_name_raw:
            await update.message.reply_text(_("Please enter a stop name or code"))
            return

        dt = datetime.now()
        service_ids = detect_service_type(dt)
        if not service_ids:
            await update.message.reply_text(_("No matching service type found"))
            return

        stop_name = transliterate(stop_name_raw)
        rows = get_schedule(dt, stop_name, interval)

        if not rows:
            await update.message.reply_text(_("Not found"))
            return

        types = {0: "Tm 🚋", 3: "A  🚌", 11: "Tb 🚎"}
        old_header_name = ''
        schedule_lines: list[str] = ['```']

        for row in rows[:33]:
            header_name = getattr(row, "stop_name", "?")
            if header_name != old_header_name:
                schedule_lines.extend([
                    "```",
                    f"*{escape_markdown(header_name, version=2)}*",
                    "```",
                ])
                old_header_name = header_name

            type_emoji = types.get(row.route_type, "Unknn")
            number = (row.route_short_name or "").ljust(5)
            headsign = row.trip_headsign or ""
            schedule_lines.append(f"{row.arrival_time[:5]} {type_emoji} {number} {headsign}".rstrip())

        schedule_lines.append("```")

        await update.message.reply_text(
            "\n".join(schedule_lines[2:]), # skip two lines of ```
            parse_mode=ParseMode.MARKDOWN_V2,
        )

    async def location_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.message is None or update.message.location is None:
            return

        _ = get_translator(update, context).gettext

        lat = update.message.location.latitude
        lon = update.message.location.longitude

        lat_min = lat - lat_delta
        lat_max = lat + lat_delta
        lon_min = lon - lon_delta
        lon_max = lon + lon_delta

        sql = """
            SELECT stop_code, stop_name, stop_lat, stop_lon
            FROM stops
            WHERE stop_lat BETWEEN ? AND ?
                AND stop_lon BETWEEN ? AND ?
            ORDER BY stop_name
        """

        with project.connect_db() as conn:
            rows = conn.execute(sql, (lat_min, lat_max, lon_min, lon_max)).fetchall()

        if not rows:
            await update.message.reply_text(_("No stops found nearby"))
            return

        lines: list[str] = []
        for row in rows[:30]:
            stop_code = row[0]
            stop_name = row[1]
            stop_lat = row[2]
            stop_lon = row[3]
            code_part = f"{stop_code} " if stop_code else ""
            lines.append(f"{code_part}{stop_name} ({stop_lat:.5f}, {stop_lon:.5f})")

        await update.message.reply_text("\n".join(lines))

    async def interval_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.message is None:
            return

        translator = get_translator(update, context)
        _ = translator.gettext
        ngettext = translator.ngettext

        if not context.args:
            choices = [5, 10, 20, 30, 60, 120, 240]
            keyboard = [
                [InlineKeyboardButton(str(m), callback_data=f"interval:{m}") for m in choices]
            ]
            await update.message.reply_text(
                _("Usage: /interval MINUTES"),
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
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

    async def interval_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = getattr(update, "callback_query", None)
        if query is None or query.data is None:
            return

        if not query.data.startswith("interval:"):
            return

        try:
            minutes = int(query.data.split(":", 1)[1])
        except ValueError:
            await query.answer()
            return

        if minutes <= 0:
            await query.answer()
            return

        translator = get_translator(update, context)
        ngettext = translator.ngettext

        context.user_data["interval"] = minutes
        await query.answer()
        await query.edit_message_text(
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
            choices = [
                ("English", "en"),
                ("Русский", "ru"),
                ("Srpski", "sr"),
            ]
            keyboard = [
                [InlineKeyboardButton(label, callback_data=f"language:{code}") for label, code in choices]
            ]
            await update.message.reply_text(
                _("Usage: /language LANGUAGE"),
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return

        requested = " ".join(context.args)
        lang = normalize_language(requested)
        if not lang:
            await update.message.reply_text(_("Unknown language"))
            return

        context.user_data["lang"] = lang
        translator = get_translator(update, context)
        _ = translator.gettext
        await update.message.reply_text(_("Language switched to English"))

    async def language_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = getattr(update, "callback_query", None)
        if query is None or query.data is None:
            return

        if not query.data.startswith("language:"):
            return

        lang = query.data.split(":", 1)[1]
        if lang not in {"en", "ru", "sr"}:
            await query.answer()
            return

        context.user_data["lang"] = lang
        translator = get_translator(update, context)
        _ = translator.gettext
        await query.answer()
        await query.edit_message_text(_("Language switched to English"))

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

        if head in {"/язык", "/језик"}:
            try:
                return await language_command(update, context)
            finally:
                context.args = prev_args

        context.args = prev_args

    async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        err = getattr(context, "error", None)
        if isinstance(err, NetworkError):
            logger.warning("Telegram network error: %s", err)
            return

        if err is None:
            logger.error("Telegram error handler called with no exception")
            return

        logger.error(
            "Unhandled Telegram exception: %r",
            err,
            exc_info=(type(err), err, err.__traceback__),
        )

    async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.message is None or update.message.text is None:
            return
        text = update.message.text.strip()
        if not text:
            return
        logger.warning("Unknown command: %s", text)

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("start", help_command))

    app.add_handler(CommandHandler("interval", interval_command))
    app.add_handler(MessageHandler(filters.Regex(r"^/интервал(\s|$)"), command_alias_router))
    app.add_handler(CallbackQueryHandler(interval_menu_callback, pattern=r"^interval:\d+$"))

    app.add_handler(CommandHandler("language", language_command))
    app.add_handler(CommandHandler("lang", language_command))
    app.add_handler(CommandHandler("jezik", language_command))
    app.add_handler(MessageHandler(filters.Regex(r"^/язык(\s|$)"), command_alias_router))
    app.add_handler(MessageHandler(filters.Regex(r"^/језик(\s|$)"), command_alias_router))
    app.add_handler(CallbackQueryHandler(language_menu_callback, pattern=r"^language:(en|ru|sr)$"))

    app.add_handler(MessageHandler(filters.LOCATION, location_query))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, stop_query))
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    app.add_error_handler(error_handler)
    app.run_polling()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
