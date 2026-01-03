req: requirements.txt
	pip install -r $<

test:
	pytest

i18n-extract:
	pybabel extract -F babel.cfg -o locales/belgrade_bot.pot .

i18n-update: i18n-extract
	pybabel update -i locales/belgrade_bot.pot -d locales -D belgrade_bot

i18n-compile:
	pybabel compile -d locales -D belgrade_bot
