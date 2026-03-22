## Role

You are an assistant helping develop and maintain the planzen app.

## Project summary

planzen is a CLI tool that reads quarterly engineering plans from Excel, allocates weekly capacity across Epics, and exports two review-friendly Excel files (values + formulas).

## Intended workflow

1. User runs `uv run planzen INPUT_FILE -q QUARTER [-o OUTPUT_DIR]`
2. `cli.py` calls `excel_io.py` to validate and read the input
3. Parsed data flows into `core_logic.py` for pure transformations
4. Results go back through `excel_io.py` to write two output Excel files
5. User opens the output in Excel for human review

Business rules are in **`LOGIC.md`**. Implementation spec is in **`SPECS.md`**.

## Ways of working

See **`CONTRIBUTING.md`** for: tech stack, architecture rules, file layout, workflow, testing, documentation sync, and commit conventions.

## Safety

Treat the repository root as the boundary: do not read or write paths outside it. Do not access home-directory dotfiles (SSH keys, cloud credentials). Do not commit secrets.
