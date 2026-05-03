.PHONY: start stop logs mike-foreman mike-lint

# Run the full AUA Poker app with one command.
start:
	docker compose up --build --remove-orphans

# Stop and clean up containers.
stop:
	docker compose down

# Stream container logs.
logs:
	docker compose logs -f aua-poker

# Mike Foreman: quick compose health/config check.
mike-foreman:
	docker compose config --quiet

# Mike Lint: lightweight syntax/lint pass inside container.
mike-lint:
	docker compose run --rm aua-poker python -m compileall -q src main.py
