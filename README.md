# planzen

planzen is a small office automation tool that processes tabular data containing annual plans (based on weekly capacity allocation to different Epics) and exports a review‑friendly Excel file.

---

## Installation

Requires [uv](https://github.com/astral-sh/uv).

```bash
uv sync
```

---

## Usage

```bash
uv run planzen INPUT_FILE OUTPUT_FILE -q QUARTER [OPTIONS]
```

### Options

| Option | Default | Description |
|---|---|---|
| `-q`, `--quarter` | *(required)* | Fiscal quarter to plan (1–4). Sets the 13-week date range automatically. |
| `--num-engineers` | *(required)* | Number of engineers; supports fractions for part-time members (e.g. `2.5`) |
| `--num-managers` | *(required)* | Number of line managers; supports fractions (e.g. `0.5`) |

All capacity values are in **Person-Weeks (PW)**. Each person contributes 1 PW/week of bruto capacity. Absence is **37 days/year (30 vacation + 7 sick) = 0.71 days/week per person = ≈ 0.142 PW/person/week** (÷ 5 working days/week). Net capacity = bruto − absence.

### Fiscal quarters

| Quarter | Start Monday | End Monday |
|---|---|---|
| Q1 | 2025-12-29 | 2026-03-23 |
| Q2 | 2026-03-30 | 2026-06-22 |
| Q3 | 2026-06-29 | 2026-09-21 |
| Q4 | 2026-09-28 | 2026-12-21 |

### Example

```bash
uv run planzen data/examples/input_example.xlsx data/examples/output_example.xlsx \
  -q 2 \
  --num-engineers 5 \
  --num-managers 2
```

---

## Input format

The input is an Excel file (`.xlsx`) with **one row per Epic**. The following columns are required (column order and extra columns are ignored):

| Column | Type | Description |
|---|---|---|
| `Epic Description` | text | Name / description of the Epic |
| `Estimation` | float | Total capacity to allocate across all weeks (PW) |
| `Budget Bucket` | text | Cost/budget category (e.g. Platform, Analytics, Product) |
| `Type` | text | Epic type (e.g. Feature, Improvement) |
| `Link` | text | URL to the Epic in your tracking tool |
| `Priority` | integer | Priority rank (lower = higher priority; used for allocation order) |

The optional column `Milestone` (e.g. Q1, Q2) is preserved when present. Any other extra columns in the file are kept without error.

### Example input (`data/examples/input_example.xlsx`)

| Epic Description | Estimation | Budget Bucket | Type | Link | Priority | Milestone |
|---|---|---|---|---|---|---|
| Auth & Identity Management | 80.0 | Platform | Feature | …/AUTH-1 | 0 | Q1 |
| Real-time Analytics | 120.0 | Analytics | Feature | …/ANA-1 | 0 | Q2 |
| Mobile App Redesign | 100.0 | Product | Improvement | …/MOB-1 | 1 | Q2 |
| API Gateway Optimization | 60.0 | Platform | Improvement | …/API-1 | 1 | Q3 |
| Data Quality Framework | 90.0 | Analytics | Feature | …/DQ-1 | 2 | Q3 |

---

## Output format

The tool produces **two output files** from a single run:

| File | Contents |
|---|---|
| `OUTPUT_FILE` | All cells contain numeric values |
| `OUTPUT_FILE` (stem `_formulas`) | Calculated cells contain Excel formulas |

Cells that become formulas in the formulas file:

| Cell / range | Formula type | Example |
|---|---|---|
| Engineer Net Capacity (each week) | `=<bruto>-<absence>` | `=F2-F3` |
| Management Net Capacity (each week) | `=<mgmt_cap>-<mgmt_absence>` | `=F5-F6` |
| Total Weeks (each Epic row) | `=SUM(<first_week>:<last_week>)` | `=SUM(F8:R8)` |
| Weekly Allocation (each week) | `=SUM(<first_epic>:<last_epic>)` | `=SUM(F8:F14)` |

### Structure

**Header rows** (one per capacity metric, no Budget Bucket or Epic data):

| Row label | Description |
|---|---|
| `Engineer Capacity (Bruto)` | `E × 1 PW` |
| `Engineer Absence` | `E × 0.142 PW` (37 days/year = 0.71 days/week ÷ 5) |
| Engineer Net Capacity | Bruto − Absence; this is the weekly budget for Epic allocation |
| Management Capacity | `M × 1 PW` |
| Management Absence | `M × 0.142 PW` |
| Management Net Capacity | Management Capacity − Absence |

**Epic rows** (one per Epic from the input, sorted by Priority ascending):

| Column | Description |
|---|---|
| `Budget Bucket` | From input |
| `Epic / Capacity Metric` | Epic name from input |
| `Priority` | From input (rows sorted lowest → highest priority number) |
| `Estimation` | Total capacity budget from input |
| `Total Weeks` | Sum of all weekly allocations for this Epic |
| `M.DD` … | One column per Monday in the quarter; value = capacity allocated that week |

**Total row** (last row):

Labelled `Total / Weekly Allocation` — shows the sum of all Epic allocations for each week.

### Allocation constraints

- Epics are sorted by Priority (ascending = highest priority first); higher-priority epics claim capacity before lower ones
- Allocation is **sequential**: once an epic starts in a week, all following weeks with available capacity also receive allocation (≥ 0.1 PW). A week gets 0 only when capacity is fully consumed by higher-priority epics
- Per-Epic: sum of all week columns ≤ `Estimation`
- Per-week: sum across all Epic rows ≤ `Engineer Net Capacity` for that week
- Cell values are floats rounded to 0.1 PW increments
- If total estimations exceed quarter capacity, lower-priority epics overflow (Total Weeks < Estimation)

### Example output (truncated — `data/examples/output_example.xlsx`)

| Budget Bucket | Epic / Capacity Metric | Priority | Estimation | Total Weeks | Dec.29 | Jan.05 | … | Jun.22 |
|---|---|---|---|---|---|---|---|---|
| | Engineer Capacity (Bruto) | | | | 5.0 | 5.0 | … | 5.0 |
| | Engineer Absence | | | | 0.7 | 0.7 | … | 0.7 |
| | Engineer Net Capacity | | | | 4.3 | 4.3 | … | 4.3 |
| | Management Capacity | | | | 2.0 | 2.0 | … | 2.0 |
| | Management Absence | | | | 0.3 | 0.3 | … | 0.3 |
| | Management Net Capacity | | | | 1.7 | 1.7 | … | 1.7 |
| Platform | Auth & Identity Management | 0 | 80.0 | 55.9 | 4.3 | 4.3 | … | 4.3 |
| Analytics | Real-time Analytics | 0 | 120.0 | 0.0 | 0.0 | 0.0 | … | 0.0 |
| Product | Mobile App Redesign | 1 | 100.0 | 0.0 | 0.0 | 0.0 | … | 0.0 |
| Platform | API Gateway Optimization | 1 | 60.0 | 0.0 | 0.0 | 0.0 | … | 0.0 |
| Analytics | Data Quality Framework | 2 | 90.0 | 0.0 | 0.0 | 0.0 | … | 0.0 |
| Total | Weekly Allocation | | | | 4.3 | 4.3 | … | 4.3 |

Week column headers use the format `Mon.DD` (e.g. `Jan.05` = January 5, `Jun.22` = June 22). Each quarter has **13 week columns**.

---

## Development

```bash
uv run pytest        # run tests
```

Sample files live in `data/examples/`. See `LOGIC.md` for the full allocation rules and `STRUCTURE.md` for the project layout.