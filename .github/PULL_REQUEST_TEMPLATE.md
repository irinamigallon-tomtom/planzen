## What and why

<!-- One paragraph: what changed and the reason for it. -->

## Checklist

- [ ] `uv run pytest tests/ web/backend/tests/` passes
- [ ] Frontend tests pass (`cd web/frontend && npm test -- --run`)
- [ ] Spreadsheet integration passes (`find data -name '*.xlsx' -print0 | while IFS= read -r -d '' f; do uv run planzen "$f" -q 2 -o output/ || exit 1; done`)
- [ ] Affected docs updated (`LOGIC.md`, `SPECS.md`, `ARCHITECTURE.md`, `README.md` as needed)
- [ ] `CHANGELOG.md` entry added under `[Unreleased]`
- [ ] `data/examples/` not modified
