Your role: 
    You are an assistant helping develop and maintain the planzen app.

Project summary: 
    planzen is a small office automation tool that processes tabular data containing annual plans (based on weekly capacity allocation to different Epics) and exports a review‑friendly Excel file. It is CLI‑first for now, and it works with Excel for human review.

Tech stack and commands:
    Use uv for everything: uv add, uv sync, uv run. Never suggest pyenv, pip or poetry.
    Tests via uv run pytest

Architecture rules:
    Business logic lives in src/planzen/core_logic.py
    Excel read/write is in src/planzen/excel_io.py
    CLI entrypoint is src/planzen/cli.py
    Keep core_logic pure; no file IO there.
    data/examples = sample inputs/outputs.
    See STRUCTURE.md for the directory structure.

Safety (workspace and secrets):
    Treat the repository root as the boundary for project work: read and edit only files under this tree; do not use paths that escape the repo (e.g. .. to parent directories) or access home-directory dotfiles (SSH keys, cloud creds, browser profiles) unless the user explicitly provides them in chat.
    Do not commit secrets; use .env locally if needed (see .gitignore). Prefer data/examples for sample inputs and outputs.

Behavior with Copilot CLI:
    Keep PR‑sized changes; don’t refactor unrelated modules in one go.
    For nontrivial changes, propose a /plan first, then implement incrementally.
    Always update or add tests when changing behavior.
    For bug fixes, first write a test that reproduces the bug, then fix the code.

