# planzen

planzen reads a quarterly engineering plan from an Excel file, allocates weekly capacity to Epics, and writes two review-friendly Excel output files — one with plain values, one with auditable formulas.

---

## Installation

Requires [uv](https://github.com/astral-sh/uv).

```bash
uv sync
```

---

## Usage

```bash
uv run planzen INPUT_FILE -q QUARTER [-o OUTPUT_DIR]
```

| Option | Required | Default | Description |
|---|---|---|---|
| `INPUT_FILE` | ✅ | — | Path to the input `.xlsx` file |
| `-q / --quarter` | ✅ | — | Fiscal quarter (1–4) |
| `-o / --output-dir` | no | `./output/` | Output directory (created if absent) |

Two files are written per run:
- `{stem}_{YYMMDDhhmm}.xlsx` — values
- `{stem}_{YYMMDDhhmm}_formulas.xlsx` — formulas

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

Identified by their value in the **`Budget Bucket`** column (case-insensitive, parenthetical suffixes stripped). The `Estimation` column holds the numeric value.

| `Budget Bucket` label | Value | Unit | Required |
|---|---|---|---|
| `Engineer Capacity (Bruto)` or `Num Engineers` | e.g. `5.0` | FTE | ✅ one of these |
| `Management Capacity (Bruto)` | e.g. `2.0` | FTE | optional (default: 1.0 PW/week) |
| `Engineer Absence` | e.g. `10` | working days (quarter total) | optional |
| `Management Absence` | e.g. `4` | working days (quarter total) | optional |

When absence is omitted the tool defaults to **37 days/year** ÷ 52 ÷ 5 ≈ 0.142 PW/person/week.

The input may also include **per-week capacity columns** in `D.M.` format (e.g. `30.3.`, `6.4.`) — see `LOGIC.md` for details.

### Epic columns

| Column | Required |
|---|---|
| `Epic Description` | ✅ |
| `Estimation` (PW total) | ✅ |
| `Budget Bucket` | ✅ |
| `Priority` (integer, lower = higher priority) | ✅ |
| `Link` | optional |
| `Allocation Mode` (`Sprint` / `Uniform` / `Gaps`) | optional |
| `Type`, `Milestone` | optional |

Extra columns are preserved without error.

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

```bash
uv run pytest        # run tests
```

See `LOGIC.md` for allocation rules, `SPECS.md` for implementation details, and `CONTRIBUTING.md` for workflow and commit conventions.
