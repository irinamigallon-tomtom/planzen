# planzen

planzen is a small office automation tool that processes tabular data containing quarterly plans (based on weekly capacity allocation to different Epics) and exports a review-friendly Excel file.

---

## Units at a glance

| Context | Value | Unit |
|---|---|---|
| Team headcount input | e.g. `5`, `2.5` | **FTE** (full-time equivalents; fractions allowed) |
| Absence input | e.g. `10`, `4` | **working days** — total for the selected quarter |
| Epic effort estimate | e.g. `80.0` | **Person-Weeks (PW)** — total effort for the epic |
| Output — weekly capacity cells | e.g. `5.0`, `4.3` | **PW / week** — constant for every week column |
| Output — epic allocation cells | e.g. `1.5` | **PW / week** — capacity assigned to that epic that week |
| Output — Total Weeks column | e.g. `55.9` | **PW** — sum across all 13 weeks of the quarter |

1 PW = 1 person working a full week.  Values are rounded to 0.1 PW increments.

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

Two output files are always written to `OUTPUT_DIR`. No `OUTPUT_FILE` argument is needed — file names are derived from the input name plus a timestamp.

### Options

| Option | Required | Default | Description |
|---|---|---|---|
| `-q`, `--quarter` | yes | — | Fiscal quarter (1–4). Determines the 13-week allocation window automatically. |
| `-o`, `--output-dir` | no | `./output/` | Directory for output files. Created automatically if it does not exist. |

### Fiscal quarters

| Quarter | Start Monday | End Monday | Weeks |
|---|---|---|---|
| Q1 | 2025-12-29 | 2026-03-23 | 13 |
| Q2 | 2026-03-30 | 2026-06-22 | 13 |
| Q3 | 2026-06-29 | 2026-09-21 | 13 |
| Q4 | 2026-09-28 | 2026-12-21 | 13 |

### Example

```bash
uv run planzen data/examples/input_example.xlsx -q 2
# writes: output/input_example_202603211430.xlsx
#         output/input_example_202603211430_formulas.xlsx

uv run planzen data/examples/input_example.xlsx -q 2 -o /tmp/review
# writes: /tmp/review/input_example_202603211430.xlsx
#         /tmp/review/input_example_202603211430_formulas.xlsx
```

---

## Input format

A single `.xlsx` file with one sheet. The sheet starts with **team config rows**, followed by **one row per Epic**. Column order and extra columns do not matter.

### Team config rows (top of the sheet)

Identified by their value in the `Epic Description` column. The `Estimation` column holds the numeric value. All other columns may be left blank.

| `Epic Description` label | `Estimation` value | Unit | Required? |
|---|---|---|---|
| `Engineer Bruto Capacity` | e.g. `5` or `2.5` | **FTE** | ✅ |
| `Management Bruto Capacity` | e.g. `2` or `0.5` | **FTE** | ✅ |
| `Engineer Absence (days)` | e.g. `10` | **working days** — total for the quarter | optional |
| `Manager Absence (days)` | e.g. `4` | **working days** — total for the quarter | optional |

When absence is omitted the tool falls back to **37 days/year** (30 vacation + 7 sick), pro-rated to the quarter: `37 / 52 weeks / 5 days × FTE` ≈ 0.142 PW/person/week.

### Epic columns (required, order does not matter)

| Column | Type | Unit | Description |
|---|---|---|---|
| `Epic Description` | text | — | Name / description of the Epic |
| `Estimation` | float | **PW** (total effort) | Total capacity to allocate across all weeks |
| `Budget Bucket` | text | — | Cost/budget category (e.g. Platform, Analytics) |
| `Type` | text | — | Epic type (e.g. Feature, Improvement) |
| `Link` | text | — | URL to the Epic in your tracking tool |
| `Priority` | integer | — | Priority rank — lower number = higher priority; controls allocation order |

The optional column `Milestone` (e.g. Q1, Q2) and any additional columns are preserved without error.

### Example input (`data/examples/input_example.xlsx`)

| Epic Description | Estimation | Budget Bucket | Type | Link | Priority | Milestone |
|---|---|---|---|---|---|---|
| Engineer Bruto Capacity | **5.0 FTE** | | | | | |
| Management Bruto Capacity | **2.0 FTE** | | | | | |
| Engineer Absence (days) | **10 days** | | | | | |
| Auth & Identity Management | 80.0 PW | Platform | Feature | …/AUTH-1 | 0 | Q1 |
| Real-time Analytics | 120.0 PW | Analytics | Feature | …/ANA-1 | 0 | Q2 |
| Mobile App Redesign | 100.0 PW | Product | Improvement | …/MOB-1 | 1 | Q2 |
| API Gateway Optimization | 60.0 PW | Platform | Improvement | …/API-1 | 1 | Q3 |
| Data Quality Framework | 90.0 PW | Analytics | Feature | …/DQ-1 | 2 | Q3 |

---

## Output format

A single run produces **two files**:

| File | Contents |
|---|---|
| `{input_stem}_{YYYYMMddhhmm}.xlsx` | All cells are numeric values (PW) |
| `{input_stem}_{YYYYMMddhhmm}_formulas.xlsx` | Calculated cells contain Excel formulas for auditability |

Cells replaced by formulas in the formulas file:

| Cell / range | Formula | Example |
|---|---|---|
| Engineer Net Capacity (each week col) | `=<bruto> - <absence>` | `=F2-F3` |
| Management Net Capacity (each week col) | `=<mgmt_cap> - <mgmt_absence>` | `=F5-F6` |
| Total Weeks (each epic row) | `=SUM(<first_week_col>:<last_week_col>)` | `=SUM(F8:R8)` |
| Weekly Allocation row (each week col) | `=SUM(<first_epic_row>:<last_epic_row>)` | `=SUM(F8:F14)` |

### Output structure

**6 capacity header rows** — constant across all week columns (unit: PW/week):

| Row label | Formula | Example (5 eng, 10 absence days, Q2) |
|---|---|---|
| `Engineer Capacity (Bruto)` | `E FTE × 1 PW/week` | `5.0 PW/week` |
| `Engineer Absence` | `absence_days ÷ 5 ÷ 13 weeks` | `0.2 PW/week` |
| `Engineer Net Capacity` | Bruto − Absence | `4.8 PW/week` |
| `Management Capacity` | `M FTE × 1 PW/week` | `2.0 PW/week` |
| `Management Absence` | `37 days/yr default ÷ 52 ÷ 5 × M` | `0.3 PW/week` |
| `Management Net Capacity` | Capacity − Absence | `1.7 PW/week` |

**One row per Epic** (sorted by Priority ascending):

| Column | Unit | Description |
|---|---|---|
| `Budget Bucket` | — | From input |
| `Epic / Capacity Metric` | — | Epic name |
| `Priority` | — | From input |
| `Estimation` | PW (total) | Total effort budget from input |
| `Total Weeks` | PW (total) | Sum of all weekly allocations for this quarter |
| `Mon.DD` … | PW/week | Capacity allocated to this epic that week |

**Total row** — `Weekly Allocation`: sum of all epic allocations per week (PW/week).

### Allocation rules

- Epics allocated in Priority order (lower number first); higher-priority epics claim capacity before lower ones
- **Sequential**: once an epic starts receiving capacity, every subsequent week with available capacity also gets ≥ 0.1 PW — a 0 is only allowed when the week is fully consumed by higher-priority epics
- Per-epic total ≤ `Estimation`; per-week total ≤ `Engineer Net Capacity`
- Cell granularity: 0.1 PW increments
- Overflow is expected and visible: if total estimations exceed quarter capacity, lower-priority epics show `Total Weeks < Estimation`

### Example output (Q2, 5 engineers, 10 absence days, 2 managers — `data/examples/output_example.xlsx`)

| Budget Bucket | Epic / Capacity Metric | Priority | Estimation | Total Weeks | Mar.30 | Apr.06 | … | Jun.22 |
|---|---|---|---|---|---|---|---|---|
| | Engineer Capacity (Bruto) | | | | 5.0 | 5.0 | … | 5.0 |
| | Engineer Absence | | | | 0.2 | 0.2 | … | 0.2 |
| | Engineer Net Capacity | | | | 4.8 | 4.8 | … | 4.8 |
| | Management Capacity | | | | 2.0 | 2.0 | … | 2.0 |
| | Management Absence | | | | 0.3 | 0.3 | … | 0.3 |
| | Management Net Capacity | | | | 1.7 | 1.7 | … | 1.7 |
| Platform | Auth & Identity Management | 0 | 80.0 PW | 62.4 PW | 4.8 | 4.8 | … | … |
| Analytics | Real-time Analytics | 0 | 120.0 PW | … | … | … | … | … |
| … | … | … | … | … | … | … | … | … |
| Total | Weekly Allocation | | | | 4.8 | 4.8 | … | 4.8 |

Week column headers: `Mon.DD` format (e.g. `Mar.30`, `Jun.22`). Each quarter has **13 week columns**.

---

## Development

```bash
uv run pytest        # run tests
```

Sample files live in `data/examples/`. See `LOGIC.md` for the full allocation rules and `STRUCTURE.md` for the project layout.
