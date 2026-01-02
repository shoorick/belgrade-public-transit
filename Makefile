req: requirements.txt
	pip install -r $<

test:
	pytest
