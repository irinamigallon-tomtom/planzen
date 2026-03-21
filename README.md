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
uv run planzen INPUT_FILE OUTPUT_FILE --start YYYY-MM-DD --end YYYY-MM-DD [OPTIONS]
```

### Options

| Option | Default | Description |
|---|---|---|
| `--start` | *(required)* | First day of the planning period (any weekday; the tool finds the first Monday on or after this date) |
| `--end` | *(required)* | Last day of the planning period (inclusive) |
| `--eng-bruto` | `40.0` | Weekly engineering capacity in person-hours (bruto) |
| `--eng-absence` | `4.0` | Weekly engineering absence in person-hours |
| `--mgmt-capacity` | `10.0` | Weekly management capacity in person-hours |
| `--mgmt-absence` | `1.0` | Weekly management absence in person-hours |

### Example

```bash
uv run planzen data/examples/input_example.xlsx data/examples/output_example.xlsx \
  --start 2026-01-05 \
  --end 2026-12-28
```

---

## Input format

The input is an Excel file (`.xlsx`) with **one row per Epic**. The following columns are required (order does not matter):

| Column | Type | Description |
|---|---|---|
| `Epics` | text | Name of the Epic |
| `Estimation` | float | Total capacity to allocate across all weeks (person-hours) |
| `Budget Bucket` | text | Cost/budget category (e.g. Platform, Analytics, Product) |
| `Priority` | integer | Priority rank (lower = higher priority) |
| `Milestone` | text | Target milestone or quarter (e.g. Q1, Q2) |

Additional columns in the file are ignored.

### Example input (`data/examples/input_example.xlsx`)

| Epics | Estimation | Budget Bucket | Priority | Milestone |
|---|---|---|---|---|
| Auth & Identity Management | 80.0 | Platform | 0 | Q1 |
| Real-time Analytics | 120.0 | Analytics | 0 | Q2 |
| Mobile App Redesign | 100.0 | Product | 1 | Q2 |
| API Gateway Optimization | 60.0 | Platform | 1 | Q3 |
| Data Quality Framework | 90.0 | Analytics | 2 | Q3 |

---

## Output format

The output is an Excel file (`.xlsx`) with a single sheet named **Allocation**.

### Structure

**Header rows** (one per capacity metric, no Budget Bucket or Epic data):

| Row label | Description |
|---|---|
| Engineering Capacity (Bruto) | Raw weekly engineering capacity |
| Engineering Absence | Weekly absence to subtract |
| Engineering Net Capacity | Bruto − Absence; this is the weekly budget for Epic allocation |
| Management Capacity | Raw weekly management capacity |
| Management Absence | Weekly management absence |

**Epic rows** (one per Epic from the input):

| Column | Description |
|---|---|
| `Budget Bucket` | From input |
| `Epic / Capacity Metric` | Epic name from input |
| `Priority` | From input |
| `Estimation` | Total capacity budget from input |
| `Total Weeks` | Sum of all weekly allocations for this Epic |
| `M.DD` … | One column per Monday in the planning period; value = capacity allocated that week |

**Total row** (last row):

Labelled `Total / Weekly Allocation` — shows the sum of all Epic allocations for each week.

### Allocation constraints

- Per-Epic: sum of all week columns ≤ `Estimation`
- Per-week: sum across all Epic rows ≤ `Engineering Net Capacity` for that week
- Cell values are floats rounded to 0.1 increments

### Example output (truncated — `data/examples/output_example.xlsx`)

| Budget Bucket | Epic / Capacity Metric | Priority | Estimation | Total Weeks | 1.05 | 1.12 | … | 12.28 |
|---|---|---|---|---|---|---|---|---|
| | Engineering Capacity (Bruto) | | | | 40.0 | 40.0 | … | 40.0 |
| | Engineering Absence | | | | 4.0 | 4.0 | … | 4.0 |
| | Engineering Net Capacity | | | | 36.0 | 36.0 | … | 36.0 |
| | Management Capacity | | | | 10.0 | 10.0 | … | 10.0 |
| | Management Absence | | | | 1.0 | 1.0 | … | 1.0 |
| Platform | Auth & Identity Management | 0 | 80.0 | 78.0 | 1.5 | 1.5 | … | 1.5 |
| Analytics | Real-time Analytics | 0 | 120.0 | 119.6 | 2.3 | 2.3 | … | 2.3 |
| Product | Mobile App Redesign | 1 | 100.0 | 98.8 | 1.9 | 1.9 | … | 1.9 |
| Platform | API Gateway Optimization | 1 | 60.0 | 59.8 | 1.1 | 1.1 | … | 1.1 |
| Analytics | Data Quality Framework | 2 | 90.0 | 89.7 | 1.7 | 1.7 | … | 1.7 |
| Total | Weekly Allocation | | | | 8.5 | 8.5 | … | 8.5 |

Week column headers use the format `M.DD` (e.g. `1.05` = January 5, `12.28` = December 28). The full example output for a full 2026 year has **52 week columns**.

---

## Development

```bash
uv run pytest        # run tests
```

Sample files live in `data/examples/`. See `LOGIC.md` for the full allocation rules and `STRUCTURE.md` for the project layout.