## Units

| Context | Unit |
|---|---|
| Team headcount (`Engineer Bruto Capacity`, `Manager Bruto Capacity`) | **FTE** (full-time equivalents; fractions allowed, e.g. 2.5) |
| Absence input (`Engineer Absence (days)`, `Manager Absence (days)`) | **working days** — total for the selected quarter |
| Epic `Estimation` | **Person-Weeks (PW)** — total effort for the Epic|
| All output week columns (capacity rows and epic rows) | **PW / week** |
| `Total Weeks` column | **PW** — sum of the requested quarter's weeks only (first 13 of up to 26 columns) |

1 PW = 1 person working a full week. Cell values are rounded to **0.1 PW** increments.

---

## Input

The user provides a single `.xlsx` file with one sheet. Team config rows appear at the top; epic rows follow.

### Team config rows

Config rows are identified by their label in the **`Budget Bucket`** column. The `Estimation` column holds the numeric value. `Epic Description` should be left blank for these rows. Matching is case-insensitive and strips parenthetical suffixes (e.g. `(Bruto)`, `(days)`).

If `Budget Bucket` has no recognised label, the **`Type`** column is checked as a fallback to identify config rows.

| `Budget Bucket` label | `Estimation` value | Unit | Required? |
|---|---|---|---|
| `Engineer Capacity (Bruto)` | e.g. `5.0` | FTE | ✅ (or use `Num Engineers`) |
| `Num Engineers` | e.g. `5` | FTE | alternative to `Engineer Capacity (Bruto)` |
| `Management Capacity (Bruto)` | e.g. `2.0` | FTE | optional |
| `Engineer Absence` | e.g. `10` | working days (quarter total) | optional |
| `Management Absence` | e.g. `4` | working days (quarter total) | optional |

**Engineer capacity precedence**: `Engineer Capacity (Bruto)` is used when present and has an `Estimation` value; otherwise `Num Engineers × 1.0 PW/FTE` is used. Both are checked; bruto takes precedence.

**Management capacity default**: when `Management Capacity (Bruto)` is absent, management bruto defaults to **1.0 PW/week**.

When absence is omitted the default formula applies: **37 days/year** (30 vacation + 7 sick) ÷ 52 weeks ÷ 5 days ≈ **0.142 PW/person/week**.

### Per-week capacity mode

When the input file contains week columns formatted as `D.M.` (e.g. `30.3.`, `6.4.`) that correspond to the quarter's Mondays, per-week capacity values are read directly from those columns.

**`Engineer Capacity (Bruto)` row** — if values are present in week columns, they are used as the per-week bruto (PW/week). This is **all-or-nothing**: all 13 Q-weeks must have values, or none. A partial set (some weeks present, some absent) is a **hard error**. When per-week values are present, the scalar `Estimation` on that row is ignored.

**`Engineer Absence` row** — if values are present in week columns, they are used as the per-week absence (PW/week, not days). Missing or NaN weeks default to **0 PW** (lenient). When any per-week absence values are present, the scalar `Estimation` on that row is ignored.

### Epic columns

| Column | Required | Unit |
|---|---|---|
| `Epic Description` | ✅ | — |
| `Estimation` | ✅ | PW (total effort) |
| `Budget Bucket` | ✅ | — |
| `Link` | optional | — |
| `Priority` | ✅ | — (lower = higher priority) |
| `Allocation Mode` | optional | — (see Allocation algorithm) |
| `Type` | optional | — |
| `Milestone` | optional | — |

Column order does not matter. Column names are matched case-insensitively. Any additional columns are preserved.

### Row handling

- A row with no `Epic Description` value is **discarded** (logged as a warning).
- A row with an `Epic Description` but no `Estimation` value defaults to **0 PW** (logged as a warning).

---

## Output table structure

### Capacity header rows (unit: PW/week)

| Row | Formula | Default example (5 eng, 2 mgr) |
|---|---|---|
| Engineer Capacity (Bruto) | `E × 1 PW/week` (or per-week values from input) | 5.0 |
| Engineer Absence | `absence_days ÷ 5 ÷ n_weeks` OR `E × 0.142` (or per-week values from input) | 0.7 |
| Engineer Net Capacity | Bruto − Absence | 4.3 |
| Management Capacity (Bruto) | `M × 1 PW/week` (default 1.0 when absent) | 2.0 |
| Management Absence | `absence_days ÷ 5 ÷ n_weeks` OR `M × 0.142` | 0.3 |
| Management Net Capacity | Bruto Capacity − Absence | 1.7 |

The `Total Weeks` column is populated for **all 6 capacity header rows** (not just epic rows). Its value sums only the requested quarter's weeks (columns 1–13), even when overflow columns are present. In the formulas file: `=SUM(first_week:last_Q_week)`.

### Epic rows (sorted by Priority ascending)

| Column | Unit | Description |
|---|---|---|
| `Budget Bucket` | — | From input |
| `Epic Description` | — | Epic name |
| `Priority` | — | From input |
| `Estimation` | PW (total) | Total effort budget from input |
| `Total Weeks` | PW (Q-only total) | Sum of weekly allocations for the requested quarter only (overflow weeks excluded) |
| `Off Estimate` | bool | `True` if `abs(Total Weeks − Estimation) > 0.05` — epic was not fully allocated within the quarter. Highlighted red by conditional formatting when `TRUE`. |
| `Mon.DD` week columns | PW/week | Capacity allocated to this epic that week |

### Total row

`Weekly Allocation` — sum of all epic allocations per week (PW/week).

### Alert row

`Off Capacity` — last row. Per week column: `True` if `abs(Weekly Allocation − Engineer Net Capacity) > 0.1` — the week is under- or over-allocated. Highlighted red by conditional formatting when `TRUE`.

---

## Conditional formatting

Both output files (values and formulas) include Excel formula-based conditional formatting rules so that highlights update automatically when the workbook is edited manually.

### Boolean alert highlighting

| Cell range | Rule | Colour |
|---|---|---|
| `Off Estimate` column (epic rows) | cell `= TRUE` | Red (`#FFC7CE` fill, `#9C0006` font) |
| `Off Capacity` row (week columns) | cell `= TRUE` | Red (`#FFC7CE` fill, `#9C0006` font) |

### Budget Bucket row colours

When a row's `Budget Bucket` matches one of the values below, the **entire row** receives that background colour. The rule is formula-based (`=$<budget_bucket_col>2="<label>"`, column anchored) so it survives manual edits.

| Budget Bucket | Colour |
|---|---|
| `Self-Service ML EV Range - Phase 1` | Dark green (`#548235`) |
| `Quality improvements through ML/AI experimentation` | Green (`#C6EFCE`) |
| `Maintenance & Release` | Blue (`#B4C6E7`) |
| `Security & Compliance` | Purple (`#D9D2E9`) |
| `Customer Support` | Red (`#FFC7CE`) |
| `Critical Technical Debt` | Orange (`#FCE4D6`) |
| `Critical Product Debt` | Yellow (`#FFF2CC`) |
| `Critical Customer Commitments` | Light orange (`#F8CBAD`) |

---

## Allocation algorithm

Epics are processed in **Priority order** (lower number = higher priority). Each epic claims capacity before lower-priority ones.

The `Allocation Mode` column (optional per epic) controls how capacity is spread across weeks. When blank or unrecognised, **Sprint** mode is used.

### Modes

| Mode | Behaviour |
|---|---|
| **Sprint** (default) | Claim up to `MAX_WEEKLY_ALLOC_PW = 2.0` PW per week; sequential. |
| **Uniform** | Spread `Estimation / n_base_weeks` evenly across all weeks; sequential. |
| **Gaps** | Same rate as Sprint (`MAX_WEEKLY_ALLOC_PW`) but without the sequential minimum — a week may receive 0 even when capacity > 0. |

`MAX_WEEKLY_ALLOC_PW = 2.0` is configurable in `config.py` and represents at most a tandem of 2 people working full-time on one thing per week.

**Sequential constraint** (Sprint and Uniform): once an epic starts, every subsequent week with available capacity must receive ≥ 0.1 PW — a `0` is only allowed when that week is fully consumed by higher-priority epics.

### Two-phase allocation per epic

Each epic is allocated in two explicit phases, even when overflow columns are present:

1. **Q phase** — allocate across the 13 requested-quarter weeks using the mode's `weekly_ideal`.
2. **Q top-up** — a second pass over Q weeks fills any remaining deficit (due to rounding or variable capacity) before overflow weeks are touched. Skipped if `block_quarter_completion` is active (see Priority Guard below).
3. **Overflow phase** — only if budget remains after Q top-up, allocate into overflow weeks.
4. **Overflow top-up** — fills any residual deficit in overflow weeks.

This ordering guarantees that a high-priority epic is never forced into overflow simply because its `weekly_ideal` rounds down (e.g. Uniform with `est=4`, `13 weeks` → `weekly_ideal=0.3`, main pass yields 3.9 PW; the Q top-up recovers the 0.1).

### Priority Guard

When a higher-priority epic is unfinished in the primary quarter (i.e. its `Total Weeks < Estimation - 0.05`), lower-priority epics are allowed to *start* in Q but are capped so they cannot *complete* in Q. This ensures the higher-priority work is not invisible — it appears as `Off Estimate = True` — and lower priorities are pushed into overflow rather than stealing remaining Q capacity.

---

## Overflow

Overflow is automatic: when `Σ(Estimation) > Σ(eng_net_for(week) for week in quarter)` — i.e. the sum of per-week net capacities across the quarter (which may vary week by week) — the allocation window extends into Q+1 (13 additional Mondays). Without overflow, lower-priority epics would be partially allocated and show `Total Weeks < Estimation`. The CLI prints an informational message when overflow occurs.

---

## Constraints (mandatory checks)

The tool validates these after allocation (violations indicate a logic bug):

1. The total capacity allocated over all weeks to a given Epic cannot exceed its **Estimation**.
2. The total capacity in a given week across all Epics cannot exceed the **Engineer Net Capacity** for that week.
3. No Epic has more than `MAX_WEEKLY_ALLOC_PW` (2.0) PW allocated per week (Sprint / Gaps modes enforce this via `weekly_ideal`; Uniform uses estimation÷n_weeks which may be higher).

---

## 2026 Fiscal Quarters

| Quarter | Start Monday | End Monday | Weeks |
|---------|---|---|---|
| Q1 | 2025-12-29 | 2026-03-23 | 13 |
| Q2 | 2026-03-30 | 2026-06-22 | 13 |
| Q3 | 2026-06-29 | 2026-09-21 | 13 |
| Q4 | 2026-09-28 | 2026-12-21 | 13 |
