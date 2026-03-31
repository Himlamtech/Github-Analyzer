PYTHON ?= python3.12
PIP ?= $(PYTHON) -m pip
COMPOSE ?= docker compose

.PHONY: install install-dev format lint type-check test frontend-install frontend-dev frontend-build docker-up docker-down

install:
	$(PIP) install -e .

install-dev:
	$(PIP) install -e .[dev]
	pre-commit install

format:
	$(PYTHON) -m ruff format src tests scripts

lint:
	$(PYTHON) -m ruff check src tests scripts

type-check:
	$(PYTHON) -m mypy src tests scripts

test:
	$(PYTHON) -m pytest

frontend-install:
	npm --prefix frontend install

frontend-dev:
	npm --prefix frontend run dev

frontend-build:
	npm --prefix frontend run build

docker-up:
	$(COMPOSE) up --build

docker-down:
	$(COMPOSE) down --remove-orphans
