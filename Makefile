req: requirements.txt
	pip install -r $<

test:
	pytest

i18n-extract:
	pybabel extract -F babel.cfg -o locales/telegram_bot.pot .

i18n-update: i18n-extract
	pybabel update -i locales/telegram_bot.pot -d locales -D telegram_bot

i18n-compile:
	pybabel compile -d locales -D telegram_bot
