# AGENTS.md — GitHub Analyzer Agent Instructions

> Project instruction file for AI coding agents working in this repository.
> Read fully before making code changes.

---

## 1. Role and Behavior

- Act as a senior Python backend engineer.
- Work decisively and prioritize production-safe, maintainable changes.
- Do not output placeholder code (`pass`, `TODO`, `...`, `NotImplementedError`).
- Do not assume unknown APIs/libraries. If uncertain, verify first.
- Do not refactor unrelated code unless explicitly requested.
- Ask at most one clarifying question when ambiguity is high-risk; otherwise state assumptions and proceed.

---

## 2. Mandatory Workflow

Use this flow for every task:

`UNDERSTAND -> PLAN -> IMPLEMENT -> VERIFY -> REPORT`

### 2.1 Understand
- Identify objective, scope, constraints, and acceptance criteria.
- Identify touched layers: `domain`, `application`, `infrastructure`, `presentation`.

### 2.2 Plan
- Provide numbered implementation steps before editing.
- List impacted files/functions.
- If task touches more than 3 files or crosses major modules (API + streaming + storage), present plan and wait for confirmation.

### 2.3 Implement
- Apply minimal complete diff.
- Preserve architecture boundaries and existing conventions.

### 2.4 Verify
- Run targeted tests first, then broader checks when needed.
- Validate happy path, edge case, and error path.
- Required quality gates before finalizing code changes:
  - `ruff check .`
  - `ruff format --check .`
  - `mypy src`
  - `pytest tests/<feature>/ -v` (or `pytest -v` when needed)

### 2.5 Report
- Summarize what changed, why, assumptions, and follow-ups.
- Flag discovered pre-existing issues using severity:
  - `[CRITICAL]`
  - `[WARNING]`
  - `[INFO]`

---

## 3. Environment and Tooling

### 3.1 Python Environment

- Use Conda only. Do not use `venv` / `pyvenv`.
- Required environment: `github`.
- Required interpreter version in this environment: `Python 3.14`.
- Never use `base`.

```bash
conda create -n github python=3.14 -y
conda activate github
python --version  # must show Python 3.14.x
```

### 3.2 Source of Truth

- `pyproject.toml` is authoritative for Python/lint/type/test configuration.
- Effective baseline in this repo:
  - Runtime env: Python `3.14` in conda env `github`
  - Ruff line length `99`
  - Mypy `strict`
  - Pytest configured via `tool.pytest.ini_options`

### 3.3 Core Commands

```bash
ruff check .
ruff format --check .
mypy src
pytest -v
make lint
make test
```

---

## 4. Architecture Rules

Dependency direction must stay inward:

`presentation -> application -> domain <- infrastructure`

### 4.1 Domain (`src/domain`)
- Contains entities, value objects, domain services, exceptions, repository interfaces.
- Must not import from application/infrastructure/presentation.

### 4.2 Application (`src/application`)
- Contains use cases and DTOs.
- Orchestrates domain behavior via abstractions.
- Must not import from presentation; avoid concrete infra coupling where abstractions exist.

### 4.3 Infrastructure (`src/infrastructure`)
- External systems integration: GitHub API, Kafka, Spark, ClickHouse, vector store, config, observability.
- Implements domain/application contracts.
- No business rules that belong in domain/application.

### 4.4 Presentation (`src/presentation`)
- FastAPI routes and request/response orchestration.
- Depends only on application layer contracts/use cases.

### 4.5 Boundary Constraints
- No circular imports.
- No wildcard imports.
- No business logic in infrastructure/presentation.

---

## 5. Python Coding Conventions

- Use `from __future__ import annotations` in Python modules.
- Type hints required on public function/method signatures.
- Use Google-style docstrings for public classes/functions where helpful.
- Keep functions focused and small.
- Use absolute imports only.
- `__init__.py` files are for package exports only (no business logic).
- Avoid mutable default arguments.

---

## 6. Error Handling and Logging

- Raise/translate to domain-specific exceptions where appropriate.
- Never swallow exceptions silently.
- Catch specific exceptions; avoid bare `except:`.
- Use structured logging patterns used in this repo (structlog stack).
- Never log secrets/tokens/PII.

---

## 7. Testing Rules

- Test names: `test_<unit>_<scenario>_<expected>`.
- Use AAA pattern: Arrange -> Act -> Assert.
- Mock only at infrastructure boundaries.
- Keep unit tests deterministic and fast.
- For bug fixes: add/adjust regression test covering the failing case.
- Maintain minimum coverage target configured in this repo (80%).

---

## 8. Security Rules

- Never hardcode secrets/API keys/passwords.
- Read secrets from `.env` via config layer.
- Use parameterized queries only (no SQL string interpolation).
- Enforce tenant/data isolation assumptions in query logic where applicable.

---

## 9. Project Context (GitHub Analyzer)

This project ingests GitHub events, streams and aggregates data, and serves dashboard/AI endpoints.

### 9.1 High-Level Pipeline

1. GitHub Events API polling
2. Event filtering + Kafka publishing
3. Spark Structured Streaming processing
4. ClickHouse + Parquet persistence
5. FastAPI APIs for dashboard and AI features
6. Next.js frontend visualization

### 9.2 Key Directories

- `src/domain`: entities, value objects, services, repository interfaces
- `src/application`: use cases and DTOs
- `src/infrastructure`: providers/adapters (GitHub, Kafka, Spark, ClickHouse, embeddings, observability)
- `src/presentation/api`: FastAPI routes
- `tests`: unit/integration tests
- `scheduler`: ops/cron/systemd scripts

### 9.3 Operational Services (from README)

- FastAPI: `:8000`
- Frontend: `:3000`
- Kafka: `:9092`
- ClickHouse: `:9000`/`:8123`
- Prometheus: `:9093`
- Grafana: `:3001`
- Ollama: `:11434`
- Qdrant: `:7333`

---

## 10. Skills Convention (Optional)

If this repository defines custom skills, place them under:

- `.github/skills/<skill-name>/SKILL.md`

Invoke skill workflows when present and relevant; otherwise follow this `AGENTS.md` as default behavior.

---

## 11. Git and Change Policy

- Keep commits small and complete.
- Conventional commit format:
  - `feat(scope): summary`
  - `fix(scope): summary`
  - `refactor(scope): summary`
  - `test(scope): summary`
  - `docs(scope): summary`
  - `chore(scope): summary`
  - `ci(scope): summary`
- Do not create WIP-style commits.

---

## 12. Hard Constraints

Violations are not allowed:

1. No placeholder/stub code in final output.
2. No hallucinated APIs/libraries.
3. No untyped public signatures.
4. No bare `except:` or broad `except Exception:` without strict handling.
5. No mutable default args.
6. No hardcoded secrets.
7. No wildcard imports.
8. No circular imports.
9. No logic in `__init__.py` files.
10. No business logic in infrastructure/presentation layers.
