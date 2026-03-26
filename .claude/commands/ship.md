---
description: Run integration tests, sync docs, update CHANGELOG, and commit
disable-model-invocation: true
allowed-tools: Bash, Read, Edit, Write, Grep, Glob
---

Work through these steps in order. Stop and report any failure before proceeding.

## Step 1 — Unit + integration tests

Run the full test suite:

```bash
uv run pytest tests/ web/backend/tests/
cd web/frontend && npm test -- --run
```

Then run the spreadsheet integration check:

```bash
find data -name '*.xlsx' -print0 | while IFS= read -r -d '' f; do
  uv run planzen "$f" -q 2 -o output/ || exit 1
done
```

If any test fails, **stop**. Report what failed and do not proceed to documentation or the commit.

## Step 2 — Documentation sync

Review the diff of all staged/changed files. For each touched area, check whether the corresponding doc needs updating:

| Changed area | Doc to check |
|---|---|
| Business rules, units, allocation algorithm | `LOGIC.md` |
| CLI contract, constants, API routes, test inventory | `SPECS.md` |
| Component relationships, data flow, technology choices | `ARCHITECTURE.md` |
| Repo folder layout | `STRUCTURE.md` |
| User-facing usage or getting started | `README.md` |
| Curated sample inputs | `data/examples/` — never modify from code; flag if a new sample is needed |

Update only the docs that are actually out of sync. Do not touch docs unrelated to the change.

Also update any inline docstrings whose signatures or behaviour changed.

## Step 3 — CHANGELOG

Prepend a new entry under `## [Unreleased]` in `CHANGELOG.md`:

```markdown
### <type> — <short title>

<one or two sentences describing what changed and why. No bullet soup.>
```

Use the same Conventional Commits type as the commit (`feat`, `fix`, `docs`, `refactor`, `test`).

## Step 4 — Version bump (optional)

If the user asks to release a new version, run one of:

```bash
uv run bump-my-version bump patch   # 0.1.0 → 0.1.1  (bug fixes)
uv run bump-my-version bump minor   # 0.1.0 → 0.2.0  (new features)
uv run bump-my-version bump major   # 0.1.0 → 1.0.0  (breaking changes)
```

This updates `pyproject.toml`, promotes `[Unreleased]` in `CHANGELOG.md` to a dated heading, commits, and tags. Requires `uv add --dev bump-my-version`. Skip if no release was requested.

## Step 5 — Commit

Stage only the files that belong to this change (be explicit — no `git add -A`).

Rules (from `CONTRIBUTING.md`):
- Format: `<type>: <subject>` — subject max 15 words
- Always add co-author trailer:

```bash
git commit -m "$(cat <<'EOF'
feat: support per-week engineer capacity from Excel columns

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

Only commit when explicitly asked. If in doubt, show the staged diff and ask first.
