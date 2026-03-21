# planzen — Implementation Specification

This document is a self-contained specification for a clean-room implementation of the `planzen` CLI tool. All behaviour described here is implemented and tested.

---

## 1. Purpose

`planzen` reads a quarterly engineering plan from an Excel file, allocates weekly capacity to Epics, and writes two review-friendly Excel output files (one with computed values, one with auditable formulas).

---

## 2. Units

| Context | Unit |
|---|---|
| Team headcount input (`Engineer Bruto Capacity`, `Manager Bruto Capacity`) | **FTE** (fractions allowed, e.g. 2.5) |
| Absence input (`Engineer Absence (days)`, `Manager Absence (days)`) | **working days** — total for the selected quarter |
| Epic `Estimation` | **Person-Weeks (PW)** — total effort budget |
| Output weekly cells (capacity rows and epic allocation) | **PW / week** |
| `Total Weeks` column | **PW** — sum across all week columns |

1 PW = 1 person working a full week. All numeric values are rounded to **0.1 PW** increments.

---

## 3. CLI Interface

```
planzen INPUT_FILE -q QUARTER [-o OUTPUT_DIR]
```

| Argument / Option | Required | Default | Description |
|---|---|---|---|
| `INPUT_FILE` | ✅ | — | Path to the input `.xlsx` file |
| `-q / --quarter` | ✅ | — | Fiscal quarter (1–4); determines the 13-week window |
| `-o / --output-dir` | no | `./output/` | Directory for output files (created if absent) |

Two output files are always written; file names are derived from the input stem + timestamp:
- `{stem}_{YYMMDDhhmm}.xlsx` — values file
- `{stem}_{YYMMDDhhmm}_formulas.xlsx` — formulas file

When `Σ(Estimation) > Engineer Net Capacity × 13`, the CLI prints an informational message and automatically extends the allocation window into the next quarter.

Exit codes: `0` = success; non-zero = validation or I/O error (error message printed to stderr).

---

## 4. Fiscal Quarters

Each quarter spans exactly 13 Mondays (start inclusive, end inclusive).

| Quarter | Start Monday | End Monday |
|---|---|---|
| Q1 | 2025-12-29 | 2026-03-23 |
| Q2 | 2026-03-30 | 2026-06-22 |
| Q3 | 2026-06-29 | 2026-09-21 |
| Q4 | 2026-09-28 | 2026-12-21 |

Week column header format: `Mon.DD` using `strftime("%b.%d")` (e.g. `Mar.30`, `Jun.22`).

---

## 5. Input Format

A single `.xlsx` file with one sheet. Team config rows appear first; epic rows follow. Any number of blank rows between config and epic rows are ignored. A row with no `Epic Description` value is treated as blank and discarded.

### 5.1 Team Config Rows

Identified by the value in the `Epic Description` column (case- and whitespace-insensitive; parenthetical suffixes stripped for matching). The `Estimation` column holds the numeric value. All other columns may be blank.

| `Epic Description` label | `Estimation` value | Unit | Required |
|---|---|---|---|
| `Engineer Bruto Capacity` | e.g. `5.0` | FTE | ✅ |
| `Manager Bruto Capacity` | e.g. `2.0` | FTE | ✅ |
| `Engineer Absence (days)` | e.g. `10` | working days (quarter total) | optional |
| `Manager Absence (days)` | e.g. `4` | working days (quarter total) | optional |

Fuzzy matching rules for config labels:
- Strip leading/trailing whitespace
- Lowercase
- Remove parenthetical suffixes (e.g. `(days)`)
- Strip a trailing `s` from individual words (naïve singularisation)

When absence days are omitted, the default formula is used: `37 days/year ÷ 52 weeks/year ÷ 5 days/week × FTE ≈ 0.142 PW/person/week`.

### 5.2 Epic Columns

Column order does not matter. Extra columns are preserved in output rows.

| Column | Required | Unit | Description |
|---|---|---|---|
| `Epic Description` | ✅ | — | Epic name |
| `Estimation` | ✅ | PW (total) | Total effort budget |
| `Budget Bucket` | ✅ | — | Cost/budget category |
| `Link` | ✅ | — | URL to the tracking issue |
| `Priority` | ✅ | integer | Lower number = higher priority |
| `Allocation Mode` | optional | — | `Sprint`, `Uniform`, or `Gaps` |
| `Type` | optional | — | Epic type |
| `Milestone` | optional | — | Target milestone |

### 5.3 Validation Rules

The following must hold or the tool exits with an error:

1. Both `Engineer Bruto Capacity` and `Manager Bruto Capacity` config rows are present.
2. All required epic columns exist in the sheet.
3. `Estimation` values for epics are numeric and > 0.
4. `Priority` values are numeric.
5. When `Allocation Mode` is non-blank, it must be one of `Sprint`, `Uniform`, `Gaps`.

---

## 6. Output Table Structure

### 6.1 Column Order

```
Budget Bucket | Epic / Capacity Metric | Priority | Estimation | Total Weeks | Off Estimate | [week columns…]
```

`Off Estimate` is omitted from capacity header rows and the total/alert rows (left blank).

### 6.2 Row Order

1. 6 capacity header rows (constant across all week columns)
2. Epic rows (sorted by `Priority` ascending, lower number first)
3. Total row (`Weekly Allocation`)
4. Alert row (`Off Capacity`)

### 6.3 Capacity Header Rows (PW/week)

| Row label | Computation | Example (5 eng, 10 absence days, Q2 = 13 weeks) |
|---|---|---|
| `Engineer Capacity (Bruto)` | `eng_fte × 1.0` | `5.0` |
| `Engineer Absence` | `eng_absence_days ÷ 5 ÷ 13` OR `eng_fte × 0.142` | `0.2` |
| `Engineer Net Capacity` | Bruto − Absence | `4.8` |
| `Management Capacity` | `mgr_fte × 1.0` | `2.0` |
| `Management Absence` | `mgr_absence_days ÷ 5 ÷ 13` OR `mgr_fte × 0.142` | `0.3` |
| `Management Net Capacity` | Capacity − Absence | `1.7` |

All capacity values are the same for every week column.

### 6.4 Epic Rows

| Column | Value |
|---|---|
| `Budget Bucket` | From input |
| `Epic / Capacity Metric` | Epic name |
| `Priority` | From input |
| `Estimation` | From input (PW total) |
| `Total Weeks` | `Σ(week columns)` for this epic |
| `Off Estimate` | `True` if `abs(Total Weeks − Estimation) > 0.05` |
| Week columns | Allocated PW/week per week (see Section 7) |

### 6.5 Total Row

Label: `Weekly Allocation`. `Budget Bucket` label: `Total`.

| Column | Value |
|---|---|
| `Estimation` | `Σ(Estimation)` across all epic rows |
| `Total Weeks` | `Σ(Total Weeks)` across all epic rows |
| Week columns | `Σ(epic allocations)` for that week |

### 6.6 Alert Row

Label: `Off Capacity`. Per week column: `True` if `abs(Weekly Allocation − Engineer Net Capacity) > 0.1`.

### 6.7 Formulas File

In the formulas file, the following cells contain Excel formulas instead of values:

| Cell | Formula pattern |
|---|---|
| `Engineer Net Capacity` (each week) | `=<bruto_cell> - <absence_cell>` |
| `Management Net Capacity` (each week) | `=<mgmt_cap_cell> - <mgmt_absence_cell>` |
| `Total Weeks` (each epic row) | `=SUM(<first_week>:<last_week>)` |
| `Estimation` (Total row) | `=SUM(<first_epic_estimation>:<last_epic_estimation>)` |
| `Total Weeks` (Total row) | `=SUM(<first_epic_total_weeks>:<last_epic_total_weeks>)` |
| `Weekly Allocation` (each week) | `=SUM(<first_epic_row_week>:<last_epic_row_week>)` |
| `Off Estimate` (each epic row) | `=ABS(<total_weeks_cell> - <estimation_cell>) > 0.05` |
| `Off Capacity` (each week) | `=ABS(<weekly_alloc_cell> - <eng_net_cell>) > 0.1` |

---

## 7. Allocation Algorithm

### 7.1 Inputs

- `epics_df`: DataFrame of epic rows, sorted by `Priority` ascending before allocation begins.
- `capacity`: object with fields `eng_net` (PW/week), `eng_bruto`, `eng_absence`, `mgmt_capacity`, `mgmt_absence`, `mgmt_net`.
- `mondays`: list of `date` objects — the allocation window (13 or 26 Mondays).

### 7.2 Overflow Detection

Compute:
- `total_estimation = Σ(Estimation)` across all epics
- `quarter_capacity = eng_net × 13` (primary quarter Mondays only)

If `total_estimation > quarter_capacity + ε` (ε = 1e-9), extend the allocation window by 13 additional Mondays (the next quarter's Mondays). The `n_base_weeks` for Uniform rate computation always uses the primary 13 weeks even in overflow.

Overflow never extends beyond one additional quarter.

### 7.3 Allocation Modes

Each epic declares its `Allocation Mode` (blank → Sprint):

| Mode | `weekly_ideal` | Sequential constraint |
|---|---|---|
| **Sprint** | `MAX_WEEKLY_ALLOC_PW` (default: `2.0`) | ✅ enforced |
| **Uniform** | `max(round(estimation / n_base_weeks, 1), 0.1)` | ✅ enforced |
| **Gaps** | `MAX_WEEKLY_ALLOC_PW` | ❌ not enforced |

`MAX_WEEKLY_ALLOC_PW = 2.0` is configurable in `config.py`.

### 7.4 Per-Epic Allocation Loop

For each epic (in Priority order):

```
remaining[epic] = Estimation
budget_left = remaining[epic]

for each Monday w in order:
    capacity_available = eng_net - already_allocated[w]
    if budget_left <= 0:
        alloc = 0.0
    else:
        alloc = round(min(weekly_ideal, capacity_available, budget_left), 1)
        
        # Sequential constraint (Sprint and Uniform only):
        if enforce_sequential AND alloc < 0.1 AND capacity_available > 0 AND budget_left > 0:
            alloc = round(min(0.1, capacity_available, budget_left), 1)
    
    allocated[epic][w] = alloc
    already_allocated[w] += alloc
    budget_left -= alloc
```

### 7.5 Mandatory Constraints

After allocation, these invariants must hold (violations indicate a logic bug):

1. For every epic: `Σ(weekly allocations) ≤ Estimation + ε`
2. For every week: `Σ(epic allocations) ≤ Engineer Net Capacity + ε`
3. No allocation cell is negative.

Gaps (0 allocation in a week) are expected and valid for lower-priority epics when higher-priority epics exhaust capacity, or when an epic is complete.

---

## 8. Architecture

```
planzen/
├── src/planzen/
│   ├── cli.py          # Entrypoint: parse args, call excel_io + core_logic, write output
│   ├── core_logic.py   # Pure business logic (no file I/O): build_output_table, validate_allocation
│   ├── excel_io.py     # All file I/O: validate_input_file, read_input, write_output, write_output_with_formulas
│   └── config.py       # Constants: column names, labels, fiscal quarters, allocation mode constants
├── tests/
│   ├── test_core_logic.py      # Unit + integration tests for allocation logic
│   ├── test_excel_io.py        # Tests for I/O formatting and formulas
│   └── test_integration.py    # End-to-end CLI tests
└── data/examples/
    ├── input_example.xlsx
    ├── output_example.xlsx
    └── output_example_formulas.xlsx
```

**Invariant**: `core_logic.py` is pure — no file I/O. All pandas DataFrames flow through function parameters and return values.

### 8.1 Key Data Structures

**`CapacityConfig`** (dataclass in `core_logic.py`):
```python
@dataclass
class CapacityConfig:
    eng_bruto: float
    eng_absence: float          # PW/week
    eng_net: float              # eng_bruto - eng_absence
    mgmt_capacity: float
    mgmt_absence: float         # PW/week
    mgmt_net: float             # mgmt_capacity - mgmt_absence
```

**`read_input(path)`** returns:
```python
(epics_df: DataFrame, num_engineers: float, num_managers: float,
 eng_absence_days: float | None, mgmt_absence_days: float | None)
```

**`build_output_table(epics_df, capacity, start, end)`** returns a DataFrame with the full output structure.

---

## 9. Key Constants (`config.py`)

```python
MAX_WEEKLY_ALLOC_PW = 2.0           # cap per epic per week (Sprint and Gaps)

ALLOC_MODE_SPRINT  = "Sprint"
ALLOC_MODE_UNIFORM = "Uniform"
ALLOC_MODE_GAPS    = "Gaps"
ALLOC_MODE_DEFAULT = ALLOC_MODE_SPRINT

VALID_ALLOC_MODES = frozenset({"Sprint", "Uniform", "Gaps"})

ABSENCE_DAYS_PER_YEAR  = 37         # 30 vacation + 7 sick
WORKING_WEEKS_PER_YEAR = 52
WORKING_DAYS_PER_WEEK  = 5
ABSENCE_PW_PER_PERSON  ≈ 0.1423    # 37 / 52 / 5

# Alert thresholds
OFF_ESTIMATE_THRESHOLD = 0.05       # |Total Weeks − Estimation| > this → Off Estimate = True
OFF_CAPACITY_THRESHOLD = 0.1        # |Weekly Allocation − Eng Net| > this → Off Capacity = True
```
