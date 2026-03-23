# planzen

planzen reads a quarterly engineering plan from an Excel file, allocates weekly capacity to Epics, and writes one review-friendly Excel output file with auditable formulas. It ships both as a **CLI tool** for scripted use and a **web frontend** for interactive editing and preview.

---

## Quick start

### CLI

Requires [uv](https://github.com/astral-sh/uv).

```bash
uv sync
uv run planzen INPUT_FILE -q QUARTER [-o OUTPUT_DIR]
```

### Web frontend

```bash
npm install   # first time only
npm run dev
```

This starts both the backend (port 8000) and the frontend (port 5173) in one terminal with colour-coded output. Opens at **http://localhost:5173**.

**To stop:** press `Ctrl+C` once in that terminal. `concurrently` forwards the signal to both processes and exits cleanly.

<details>
<summary>Start them separately instead</summary>

```bash
# Terminal 1 — backend
uv run uvicorn main:app --app-dir web/backend --reload --port 8000

# Terminal 2 — frontend
cd web/frontend && npm run dev
```

**To stop each process:** press `Ctrl+C` in its terminal.
</details>

---

## Web frontend — user guide

### 1. Upload a plan

- Drop an `.xlsx` file onto the upload zone (or click to browse)
- Select the fiscal quarter (Q1–Q4)
- Click **Upload** — the backend parses the file and creates a session
- Existing sessions from previous runs appear below the upload zone; click **Load** to resume

### 2. Edit capacity

- The **Capacity** panel shows Engineer and Management bruto/absence values
- Edit any field — the allocation table updates automatically after 500 ms

### 3. Edit epics

- The **Epics** table shows all epic fields (description, estimation, priority, budget bucket, allocation mode, milestone, type, link)
- Click any cell to edit it inline
- Use the **Add Epic** button to add a new row (defaults to priority 0); drag the row handle to reorder visually without changing priority values
- Edit the **Priority** cell directly to set a numeric priority (lower = higher priority; duplicates are flagged with an info banner)
- The **Delete** button (✕) on each row removes it
- Changes trigger a live re-compute after 500 ms

### 4. Allocation preview

- The **Allocation Preview** table shows the full computed allocation (capacity rows + epic rows + total + alert rows)
- Red cells: **Off Estimate** (epic not fully allocated) or **Off Capacity** (week over/under-allocated)
- Budget Bucket row colours match the Excel output
- Week cells in epic rows are editable — type a value to override the computed allocation for that cell

### 5. Export

- Click **Download Export** to download a single `.xlsx` file with auditable Excel formulas and conditional formatting
- This is identical to what the CLI produces

---

## CLI usage

```bash
uv run planzen INPUT_FILE -q QUARTER [-o OUTPUT_DIR]
```

| Option | Required | Default | Description |
|---|---|---|---|
| `INPUT_FILE` | ✅ | — | Path to the input `.xlsx` file |
| `-q / --quarter` | ✅ | — | Fiscal quarter (1–4) |
| `-o / --output-dir` | no | `./output/` | Output directory (created if absent) |

One file is written per run:
- `output_{YYMMDDhhmm}_{stem}_formulas.xlsx` — formulas + conditional formatting

### Fiscal quarters (2026)

| Q | Start | End |
|---|---|---|
| 1 | 2025-12-29 | 2026-03-23 |
| 2 | 2026-03-30 | 2026-06-22 |
| 3 | 2026-06-29 | 2026-09-21 |
| 4 | 2026-09-28 | 2026-12-21 |

---

## Input format

A single `.xlsx` file with one sheet. **Team config rows** appear first, followed by **epic rows**. Column order does not matter.

### Team config rows

Identified by a known label in the **`Budget Bucket`** column (checked first), then `Type`, then `Epic Description` — all case-insensitive, parenthetical suffixes stripped. In practice both formats are common: classic files put the label in `Budget Bucket`; newer files may put it in `Epic Description` with `Budget Bucket` left blank. The `Estimation` column holds the numeric value, or values can be spread across per-week columns (see below).

| Label | Value | Unit | Required |
|---|---|---|---|
| `Engineer Capacity (Bruto)` or `Num Engineers` | e.g. `5.0` | PW/week or FTE | ✅ one of these |
| `Management Capacity (Bruto)` | e.g. `2.0` | PW/week | optional (default: 1.0 PW/week) |
| `Engineer Absence` | e.g. `10` | working days (quarter total) | optional |
| `Management Absence` | e.g. `4` | working days (quarter total) | optional |

When absence is omitted the tool defaults to **37 days/year** ÷ 52 ÷ 5 ≈ 0.142 PW/person/week.

**Per-week capacity:** The input may also include columns labelled in `D.M.` format (e.g. `30.3.`, `6.4.`). When the `Engineer Capacity (Bruto)` row has values in all quarter week columns, those override the scalar `Estimation` value week-by-week. Absence is lenient: missing weeks default to 0. See `LOGIC.md` for details.

### Epic columns

Column order does not matter — named columns may appear in any order before the week columns. Columns with no header (e.g. helper totals) are silently ignored. Only the column explicitly named `Estimation` is used for epic effort.

| Column | Required |
|---|---|
| `Epic Description` | ✅ |
| `Estimation` (PW total) | ✅ |
| `Budget Bucket` | ✅ |
| `Priority` (integer, lower = higher priority) | optional* |
| `Link` | optional |
| `Allocation Mode` (`Sprint` / `Uniform` / `Gaps`) | optional |
| `Type`, `Milestone` | optional |

\* `Priority` is **imputed from `Budget Bucket`** when blank or absent — no manual entry needed. Unknown buckets default to 999 (lowest). See `LOGIC.md` for the full mapping.

Rows with an `Epic Description` but no `Budget Bucket` are silently discarded (this handles annotation rows, computed totals, and decorative section headers that appear in real-world files).

---

## Output format

### Structure

| Section | Description |
|---|---|
| 6 capacity header rows | Engineer and management bruto, absence, and net capacity (PW/week per week) |
| Epic rows (sorted by Priority) | Weekly allocation per epic, `Total Weeks` (Q-only sum), `Off Estimate` flag |
| `Weekly Allocation` total row | Sum of all epic allocations per week |
| `Off Capacity` alert row | `True` per week when weekly total diverges from net capacity by > 0.1 PW |

Week columns are labelled `Mon.DD` (e.g. `Mar.30`, `Jan.05`). Normal quarters have 13 week columns; overflow adds 13 more.

### Units

| Context | Unit |
|---|---|
| Capacity / absence input | FTE / working days |
| Weekly cells (capacity + epic allocation) | PW/week |
| `Total Weeks`, `Estimation` | PW (total for the quarter) |

1 PW = 1 person working a full week. Values rounded to 0.1 PW.

### Flags

- **`Off Estimate`** (`TRUE` = red): `abs(Total Weeks − Estimation) > 0.05` — epic not fully allocated within Q.
- **`Off Capacity`** (`TRUE` = red): weekly allocation differs from net capacity by > 0.1 PW.

Row background colours by `Budget Bucket` value and formula-based conditional formatting are applied to both output files. See `LOGIC.md` for the full colour table.

---

## Development

### Running tests

```bash
uv run pytest                              # all tests (CLI + backend)
cd web/frontend && npm test -- --run       # frontend tests
```

### Adding backend dependencies

```bash
uv add <package>   # updates pyproject.toml
```

### Adding frontend dependencies

```bash
cd web/frontend && npm install <package>
```

See `LOGIC.md` for allocation rules, `SPECS.md` for implementation details, `ARCHITECTURE.md` for system design, and `CONTRIBUTING.md` for workflow and commit conventions.
