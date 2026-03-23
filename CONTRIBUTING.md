# Contributing to planzen

## Tech stack & commands

- **Package manager:** `uv` — always. Never `pip`, `poetry`, or `pyenv`.
- Add dependencies: `uv add <package>`
- Sync environment: `uv sync`
- Run the CLI: `uv run planzen`
- Run tests: `uv run pytest`
- Start the web app (combined): `npm run dev` — press **`Ctrl+C`** to stop both processes
- Start separately: `uv run uvicorn main:app --app-dir web/backend --reload --port 8000` and `cd web/frontend && npm run dev` — press **`Ctrl+C`** in each terminal to stop

## Before you start

- Read **`LOGIC.md`** before implementing or changing any business rule.
- Read **`SPECS.md`** before starting any non-trivial change (API, architecture, constants).
- See **`STRUCTURE.md`** for the directory layout and module responsibilities.

## Development workflow

- **Nontrivial changes:** propose a plan before implementing.
- Keep changes PR-sized — don't refactor unrelated modules in one go.
- Keep it simple; avoid over-engineering.
- When testing the CLI manually, point at `data/examples/` and write output to `output/`.

## Testing

- `uv run pytest` must pass before any commit.
- Write or update tests for every behaviour change.
- **Bug fixes:** write a failing test that reproduces the bug first, then fix the code.

## Documentation sync

- Keep `LOGIC.md`, `SPECS.md`, `README.md`, and `data/examples/` in sync with code changes.
- Update inline docstrings when changing function signatures or behaviour.

## Safety

- Never write output to `/tmp`.
- Never modify files under `data/examples/` from code or scripts.
- Treat the repository root as the boundary — do not read or write paths outside it.
- Do not commit secrets.

## Commits

- Use [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, …
- Subject line: **15 words maximum**.
- Only commit when explicitly asked.
- Do not commit `SPECS.md` unless asked.
- Always add co-author trailer: `Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>`
