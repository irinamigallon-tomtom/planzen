# Contributing to planzen

## Tech stack & commands

- **Package manager:** `uv` — always. Never `pip`, `poetry`, or `pyenv`.
- Add dependencies: `uv add <package>`
- Sync environment: `uv sync`
- Run the CLI: `uv run planzen`
- Run tests: `uv run pytest`

## Architecture rules

| Module | Responsibility |
|---|---|
| `src/planzen/cli.py` | CLI entrypoint only |
| `src/planzen/excel_io.py` | All Excel read/write |
| `src/planzen/core_logic.py` | Pure business logic — no file IO |

- Keep `core_logic.py` free of side effects.
- Apply separation of concerns: don't mix IO and logic.
- See `STRUCTURE.md` for the full directory layout.
- Read `LOGIC.md` before implementing or changing business rules.
- Read `LOGIC.md` and `SPECS.md` before starting any non-trivial change.

## File layout

| Path | Purpose |
|---|---|
| `src/planzen/` | Application source |
| `tests/` | Test suite |
| `tests/data/` | Fixture files for tests |
| `data/examples/` | Human-maintained sample input/output — do not modify programmatically |
| `output/` | Default destination for generated files; use `-o` to override |
| `LOGIC.md` | Business rules reference |
| `SPECS.md` | Clean-room implementation spec (handover doc; do not commit unless asked) |

- Never write output to `/tmp`.
- Never modify files under `data/examples/` from code or scripts.

## Development workflow

- **Nontrivial changes:** propose a plan before implementing; read `LOGIC.md` and `SPECS.md` first.
- Keep changes PR-sized — don't refactor unrelated modules in one go.
- Keep it simple; avoid over-engineering.
- When testing the CLI manually, point at `data/examples/` or `tests/data/` and write output to `output/`.

## Testing

- `uv run pytest` must pass before any commit.
- Write or update tests for every behaviour change.
- **Bug fixes:** write a failing test that reproduces the bug first, then fix the code.
- Run the full test suite after every change.

## Documentation sync

- Keep `LOGIC.md`, `SPECS.md`, and `data/examples/` in sync with code changes.
- Update inline docstrings when changing function signatures or behaviour.

## Commits

- Use [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, …).
- Subject line: **15 words maximum**.
- Only commit when explicitly asked.
- Do not commit `SPECS.md` unless asked.
- Always include the co-author trailer:
  ```
  Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>
  ```

## Safety

- Stay within the repository root — do not read or write paths outside it.
- Do not commit secrets. Use a local `.env` file if credentials are needed (it is git-ignored).
