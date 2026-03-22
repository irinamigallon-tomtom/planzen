# planzen — Implementation Specification

All behaviour described here is implemented and tested. For business rules, calculations, and algorithms see **[LOGIC.md](LOGIC.md)**.

---

## 1. Purpose

`planzen` reads a quarterly engineering plan from an Excel file, allocates weekly capacity to Epics, and writes two review-friendly Excel output files (one with computed values, one with auditable formulas).

---

## 2. CLI Interface

```
planzen INPUT_FILE -q QUARTER [-o OUTPUT_DIR]
```

| Argument / Option | Required | Default | Description |
|---|---|---|---|
| `INPUT_FILE` | ✅ | — | Path to the input `.xlsx` file |
| `-q / --quarter` | ✅ | — | Fiscal quarter (1–4); determines the 13-week window |
| `-o / --output-dir` | no | `./output/` | Directory for output files (created if absent) |

Two output files are always written; names are derived from the input stem + timestamp:
- `{stem}_{YYMMDDhhmm}.xlsx` — values file
- `{stem}_{YYMMDDhhmm}_formulas.xlsx` — formulas file

On validation error: print numbered errors in red, exit code 1, write no files.  
On overflow: print informational message (not an error).  
Exit code 0 on success.

---

## 3. Fiscal Quarters

Each quarter spans exactly 13 Mondays (start and end inclusive). Week column headers use `strftime("%b.%d")` — abbreviated month name + zero-padded day (e.g. `Mar.30`, `Jan.05`, `Dec.29`).

| Q | Start Monday | End Monday |
|---|---|---|
| 1 | 2025-12-29 | 2026-03-23 |
| 2 | 2026-03-30 | 2026-06-22 |
| 3 | 2026-06-29 | 2026-09-21 |
| 4 | 2026-09-28 | 2026-12-21 |

---

## 4. Input Format

A single `.xlsx` file with one sheet. Team config rows appear first; epic rows follow. Any number of blank rows between them are ignored.

### 4.1 Team Config Rows

Config rows are identified by the value in the **`Budget Bucket`** column (case- and whitespace-insensitive; parenthetical suffixes stripped). If `Budget Bucket` has no recognised label, the **`Type`** column is used as a fallback. The `Estimation` column holds the numeric value.

See [LOGIC.md](LOGIC.md) for the full list of recognised labels, required/optional status, units, default values, and fuzzy matching rules.

The input file may also contain week columns in `D.M.` format (e.g. `30.3.`, `6.4.`) for per-week engineer capacity and absence distribution. See [LOGIC.md](LOGIC.md) — Per-week capacity mode.

### 4.2 Epic Columns

Column order does not matter. Extra columns are preserved in output rows.

| Column | Required |
|---|---|
| `Epic Description` | ✅ |
| `Estimation` | ✅ |
| `Budget Bucket` | ✅ |
| `Priority` | ✅ |
| `Link` | optional |
| `Allocation Mode` | optional (`Sprint` / `Uniform` / `Gaps`) |
| `Type` | optional |
| `Milestone` | optional |

### 4.3 Validation Rules

The following cause a hard error (all problems reported together):

1. Engineer capacity config row is missing (`Engineer Capacity (Bruto)` or `Num Engineers`).
2. Required epic columns (`Epic Description`, `Estimation`, `Budget Bucket`, `Priority`) are missing from the sheet.
3. `Estimation` values for epics are non-numeric.
4. `Priority` values are non-numeric.
5. When `Allocation Mode` is non-blank, it is not one of `Sprint`, `Uniform`, `Gaps`.
6. Per-week bruto is partially specified (some Q-weeks populated, some absent) — must be all-or-nothing.

---

## 5. Output Table Structure

### 5.1 Column Order

```
Budget Bucket | Epic / Capacity Metric | Priority | Estimation | Total Weeks | Off Estimate | [Mon.DD week columns…]
```

`Off Estimate` is blank for capacity header rows, the total row, and the alert row.

### 5.2 Row Order

1. 6 capacity header rows
2. Epic rows (sorted by `Priority` ascending)
3. Total row — label `Weekly Allocation`, `Budget Bucket` = `Total`
4. Alert row — label `Off Capacity`

For capacity header row labels, computations, and per-week mode behaviour see [LOGIC.md](LOGIC.md) — Output table structure.

### 5.3 Key Column Semantics

| Column | Notes |
|---|---|
| `Total Weeks` | Q-only sum: counts only the 13 requested-quarter weeks, even when overflow columns are present |
| `Off Estimate` | `True` when `abs(Total Weeks − Estimation) > 0.05` (Q-only comparison) |
| `Off Capacity` (alert row) | `True` per week when `abs(Weekly Allocation − Engineer Net Capacity) > 0.1` |

### 5.4 Formulas File

`write_output_with_formulas` calls `write_output` first, then reopens the file and replaces cells with Excel formulas:

| Cell | Formula pattern |
|---|---|
| `Engineer Net Capacity` (each week) | `=<bruto_cell> - <absence_cell>` |
| `Management Net Capacity` (each week) | `=<mgmt_cap_cell> - <mgmt_absence_cell>` |
| `Total Weeks` (capacity rows + each epic row) | `=SUM(<first_week>:<last_Q_week>)` — Q-only |
| `Estimation` (Total row) | `=SUM(<first_epic>:<last_epic>)` |
| `Total Weeks` (Total row) | `=SUM(<first_epic_tw>:<last_epic_tw>)` |
| `Weekly Allocation` (each week) | `=SUM(<first_epic_row>:<last_epic_row>)` |
| `Off Estimate` (each epic row) | `=ABS(<total_weeks> - <estimation>) > 0.05` |
| `Off Capacity` (each week) | `=ABS(<weekly_alloc> - <eng_net>) > 0.1` |

---

## 6. Conditional Formatting

Applied to both output files via openpyxl `FormulaRule`. See [LOGIC.md](LOGIC.md) for full colour table and rule details.

Summary:
- `Off Estimate = TRUE` → red fill (`#FFC7CE`) + red font (`#9C0006`)
- `Off Capacity = TRUE` → same red
- Each `Budget Bucket` value maps to a full-row background colour (8 values defined)

---

## 7. Allocation Algorithm

See [LOGIC.md](LOGIC.md) — Allocation algorithm and Overflow.

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
│   ├── test_core_logic.py
│   ├── test_excel_io.py
│   └── test_integration.py
└── data/examples/
    ├── input_example.xlsx
    └── input_example_realistic_messy.xlsx
```

**Invariant**: `core_logic.py` is pure — no file I/O.

### 8.1 Key API

**`read_input(path: Path, quarter: int) -> tuple[DataFrame, CapacityConfig]`**  
Reads and validates the input file; builds the `CapacityConfig` (including per-week dicts when applicable).

**`validate_input_file(path: Path, quarter: int | None = None) -> list[str]`**  
Returns a list of human-readable error strings (empty = valid).

**`build_output_table(epics_df, capacity, start, end) -> DataFrame`**  
Pure: returns the full output DataFrame with capacity rows, epic rows, total row, alert row.

**`validate_allocation(df, capacity, mondays) -> list[str]`**  
Post-allocation invariant checks; returns violations (empty = valid).

**`write_output(df, path)`** — values file.  
**`write_output_with_formulas(df, path, n_base_weeks)`** — formulas file; `n_base_weeks` limits Total Weeks SUM to Q-only.

**`CapacityConfig`** (dataclass):
- Scalar fields: `eng_bruto`, `eng_absence`, `eng_net`, `mgmt_capacity`, `mgmt_absence`, `mgmt_net`
- Per-week dicts (optional): `eng_bruto_by_week`, `eng_absence_by_week`
- Accessors: `eng_bruto_for(monday)`, `eng_absence_for(monday)`, `eng_net_for(monday)` — return per-week value or fall back to scalar

---

## 9. Key Constants (`config.py`)

```python
MAX_WEEKLY_ALLOC_PW    = 2.0      # cap per epic per week (Sprint and Gaps modes)
DEFAULT_MGMT_CAPACITY_PW = 1.0   # used when Management Capacity row is absent

ALLOC_MODE_SPRINT  = "Sprint"
ALLOC_MODE_UNIFORM = "Uniform"
ALLOC_MODE_GAPS    = "Gaps"
ALLOC_MODE_DEFAULT = ALLOC_MODE_SPRINT
VALID_ALLOC_MODES  = frozenset({"Sprint", "Uniform", "Gaps"})

ABSENCE_DAYS_PER_YEAR  = 37
WORKING_WEEKS_PER_YEAR = 52
WORKING_DAYS_PER_WEEK  = 5
# → ABSENCE_PW_PER_PERSON ≈ 0.1423 PW/person/week

OFF_ESTIMATE_THRESHOLD = 0.05
OFF_CAPACITY_THRESHOLD = 0.1
```

---

## 10. Tests to Cover

### `test_core_logic.py`

- `get_quarter_dates`: correct start/end for all 4 quarters; raises for invalid quarter
- `_mondays_in_range`: correct count and values; Q1 labels use `Mon.D` format (no leading zero)
- `CapacityConfig` scalar mode: properties return correct derived values
- `CapacityConfig` per-week mode: accessors return per-week values; fall back to scalar for missing weeks
- `build_output_table`: 6 capacity rows at top; epics sorted by priority; `Total Weeks` Q-only; `Off Estimate` bool; `Off Capacity` row last; correct column order
- Allocation modes: Sprint fills sequentially at ≤ 2.0 PW/week; Uniform spreads evenly; Gaps allows 0-week holes
- Overflow: triggers when `Σ(Estimation) > Σ(eng_net_for(m))` over quarter; adds 13 columns; `Total Weeks` and `Off Estimate` still use Q-only weeks
- `validate_allocation`: passes on valid output; returns violations on over-allocation or negative cells
- `Off Estimate = True` when epic can't be fully allocated in Q; `= False` when exactly allocated
- Epic with 0 PW estimation → allocated 0, `Off Estimate = False`
- Per-week bruto varies → capacity rows vary week by week; overflow check uses per-week sum

### `test_excel_io.py`

- `validate_input_file`: returns errors for missing columns, invalid allocation mode, partial per-week bruto
- `read_input`: returns `(epics_df, CapacityConfig)`; per-week fields populated when D.M. columns present; scalar absence converted to PW/week
- `write_output`: file created; numeric values; conditional formatting applied
- `write_output_with_formulas`: `=SUM(first:last_Q_week)` in Total Weeks (capacity + epic rows); Net Capacity rows have subtraction formula; Off Estimate has `ABS`; Off Capacity has `ABS`; SUM references correct epic rows for 1, 3, 5 epics

### `test_integration.py`

- CLI runs end-to-end: both output files created; exit code 0
- Validation errors cause exit code 1 and no output files
- Realistic messy input file runs without errors

### Edge Cases

- Epic with `Estimation = 0` → no allocation, `Off Estimate = False`
- All epics fit exactly in Q → no overflow, 13 week columns
- Single epic with `Estimation > Q capacity` → overflow, `Off Estimate = True`
- Absence > Bruto → net capacity = 0 or negative (treat as 0)
- `Num Engineers` present but no `Engineer Capacity (Bruto)` → uses `Num Engineers × 1.0`
- Per-week absence with NaN weeks → defaults to 0 PW for those weeks
- Per-week bruto with partial weeks → hard validation error
