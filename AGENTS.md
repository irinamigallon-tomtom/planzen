Your role: 
    You are an assistant helping develop and maintain the planzen app.

Project summary: 
    planzen is a small office automation tool that processes tabular data containing annual plans (based on weekly capacity allocation to different Epics) and exports a review‑friendly Excel file. It is CLI‑first for now, and it works with Excel for human review.

Intended Workflow

 1. User runs the CLI (uv run planzen ...) pointing at an input Excel file that contains the following columns: Epics, Estimation, Budget Bucket, Priority, Milestone
 2. cli.py calls excel_io.py to read the tabular plan data
 3. Parsed data flows into core_logic.py for pure transformations
 4. The core logic creates a table where the weekly capacities are allocated over a period of time defined by the user, based on the input and the rules explained in LOGIC.md.
 4. Results go back through excel_io.py to write the output Excel file
 5. User opens the output in Excel for human review


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
    Keep it simple, don't overengineer: strive for simple architectures and maintainable code.
    Apply separation of concerns.
    Start with tests and run them after any change.
    For nontrivial changes, propose a /plan first, then implement incrementally.
    Always update or add tests when changing behavior.
    For bug fixes, first write a test that reproduces the bug, then fix the code.
    Update documentation and any sample data so it is in sync with the code.

