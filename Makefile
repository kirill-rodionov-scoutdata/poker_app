.PHONY: start lint tests coverage

# Run in Docker: first batch script, then web server.
start:
	docker compose up --build --remove-orphans

# Lint and format the whole project with Ruff.
lint:
	uv run ruff format .
	uv run ruff check . --fix

# Run tests.
tests:
	uv run pytest -q

# Run tests with coverage report.
coverage:
	uv run pytest --cov=src/poker --cov-report=term-missing --cov-report=xml
