install: install-poetry
	poetry install

install-poetry:
	pip install poetry

test-cov:
	poetry run pytest --cov=touchprice --cov-report=xml --cov-report=term