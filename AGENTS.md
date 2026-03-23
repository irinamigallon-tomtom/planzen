## Role

You are an assistant helping develop and maintain the **planzen** CLI tool — it reads quarterly engineering plans from Excel, allocates weekly capacity across Epics, and exports one review-friendly Excel file with auditable formulas.

## Documentation map

Read the relevant doc before acting:

| I need to know… | Read |
|---|---|
| Business rules, units, input/output format, allocation algorithm, overflow | **`LOGIC.md`** |
| API signatures, architecture, constants, test coverage requirements | **`SPECS.md`** |
| Commands, testing workflow, commit conventions, safety rules | **`CONTRIBUTING.md`** |
| Directory layout and module responsibilities | **`STRUCTURE.md`** |

## Safety

- Repo root is the boundary: no paths outside it, no home-directory dotfiles.
- Do not commit secrets. Do not modify `data/examples/` from code or scripts.
- Never try to write to /tmp, since it is outside this repo. Instead, create a tmp folder inside this repo.