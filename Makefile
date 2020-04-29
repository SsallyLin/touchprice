install: install-poetry
	poetry install

install-poetry:
	pip install poetry

test-cov:
	poetry run pytest --cov=sjexample --cov-report=xml --cov-report=term