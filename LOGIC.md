## Units

| Context | Unit |
|---|---|
| Team capacity rows (`Engineer Capacity (Bruto)`, `Management Capacity (Bruto)`) | **FTE** (fractions allowed, e.g. `2.5`) |
| Absence rows (`Engineer Absence`, `Management Absence`) | **person-weeks** — total for the selected quarter |
| Epic `Estimation` | **Person-weeks (PW)** — total effort for the epic |
| Week columns in the output (capacity + epic rows) | **PW/week** |
| `Total Weeks` column | **PW** — sum over the quarter’s 13 weeks only (first 13 of up to 26 week columns if overflow exists) |

1 PW = one person full-time for one week. Cell values are rounded to **0.1 PW**.

---

## Input

The user provides a single `.xlsx` file with one sheet. Team config rows appear at the top; epic rows follow. Any blank rows between them are ignored. Unrecognised columns (helper totals, notes, columns with no header) are silently ignored.

### Team config rows

A row is a config row if a **known label** appears in **`Budget Bucket`**, **`Type`**, or **`Epic Description`** (that order; first match wins). Matching is case-insensitive; parenthetical suffixes like `(Bruto)` are stripped; common plurals are singularised. Config rows do not need `Budget Bucket` or `Priority`.

In practice both formats are common: older files store config labels in `Budget Bucket`; newer files may store them in `Epic Description` with the `Budget Bucket` cell left blank.

Use `Estimation` for scalar values; optional **week columns** override per week (see Per-week capacity mode).

| Config label | `Estimation` | Unit | Required |
|---|---|---|---|
| `Engineer Capacity (Bruto)` | e.g. `5.0` | FTE | ✅ (or use `Num Engineers`) |
| `Num Engineers` | e.g. `5` | FTE | alternative to `Engineer Capacity (Bruto)` |
| `Management Capacity (Bruto)` | e.g. `2.0` | FTE | optional |
| `Engineer Absence` | e.g. `10` | working days (quarter total) | optional |
| `Management Absence` | e.g. `4` | working days (quarter total) | optional |

**Engineer capacity precedence**: per-week values from week columns are used first (when present); otherwise the scalar `Estimation` value on the `Engineer Capacity (Bruto)` row is used; otherwise `Num Engineers × 1.0 PW/FTE` is used as the final fallback.

**Management capacity default**: when `Management Capacity (Bruto)` is absent, management bruto defaults to **1.0 PW/week**.

**Absence:** if a row is missing, use **37 days/year** ÷ 52 weeks ÷ 5 days per person ≈ **0.142 PW/person/week** of absence.

### Per-week capacity mode

If the sheet has week columns aligned to the quarter’s Mondays, capacity and absence values can be read per week. Header styles: **`D.M.`** (e.g. `30.3.`) or **`D-Mon`** (e.g. `30-Mar`). 

**`Engineer Capacity (Bruto)`:** week cells are **PW/week**. Partial Q coverage: warn, missing weeks use a scalar derived from the mean of filled weeks. If any week cells exist, the scalar `Estimation` on that row is ignored.

**`Engineer Absence`:** week cells are **PW/week** (not days). Missing/NaN weeks in Q default to **0**. Overflow weeks use the default absence formula (see Overflow). If any week cells exist, scalar `Estimation` on that row is ignored.

### Epic columns

| Column | Required | Unit |
|---|---|---|
| `Epic Description` | ✅ | — |
| `Estimation` | ✅ | PW (total effort) |
| `Budget Bucket` | ✅ | — |
| `Link` | optional | — |
| `Priority` | optional* | — (lower = higher priority) |
| `Allocation Mode` | optional | — (see Allocation algorithm) |
| `Depends On` | optional | — Epic Description of the upstream epic (see Epic dependencies) |
| `Type` | optional | — |
| `Milestone` | optional | — |

\* `Priority` is imputed from `Budget Bucket` when blank or absent (see Priority defaults below). Only the column explicitly named `Estimation` is used for epic effort; other numeric columns are ignored.

Column order does not matter — named metadata columns may appear in any order, as long as they all precede the week columns. Column names are 
matched case-insensitively. Any additional or unrecognised columns are silently ignored.

### Priority defaults

| Budget Bucket | Default Priority |
|---|---|
| `Customer Support` | 0 |
| `Critical Customer Commitments` | 0 |
| `Maintenance & Release` | 1 |
| `Security & Compliance` | 1 |
| `Critical Technical Debt` | 1 |
| `Critical Product Debt` | 1 |
| `Self-Service ML EV Range - Phase 1` | 3 |
| `Quality improvements through ML/AI experimentation` | 4 |

Unknown buckets → **999**. Defaults and bucket→colour mapping live in `config.py` (`BUCKET_PRIORITY`, `BUCKET_COLORS`).

Metadata columns may appear in any order **before** the week columns. Names are matched case-insensitively.

### Row handling

- A row with no `Epic Description` value is **discarded** (logged as a warning).
- A row with an `Epic Description` but no `Budget Bucket` value is **discarded** (logged as a warning). This naturally handles computed rows (e.g. net capacity totals), annotation rows, and decorative section headers that appear in real-world files.
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

### Epic rows

| Column | Unit | Description |
|---|---|---|
| `Budget Bucket` | — | From input |
| `Epic Description` | — | Epic name |
| `Priority` | — | From input |
| `Estimation` | PW (total) | Total effort budget from input |
| `Total Weeks` | PW (Q-only total) | Sum of weekly allocations for the requested quarter only (overflow weeks excluded) |
| `Off Estimate` | bool | `True` if `abs(Total Weeks − Estimation) > 0.05` — epic was not fully allocated within the quarter. Highlighted red by conditional formatting when `TRUE`. |
| `Mon.DD` week columns | PW/week | Capacity allocated to this epic that week |

**`Off Estimate`:** `True` when **|Total Weeks − Estimation| > 0.05** (quarter total only). Red when `TRUE`.

`Weekly Allocation` — sum of all epic allocations per week (PW/week).

### Alert row

`Off Capacity` — last row. Per week column: `True` if `abs(Weekly Allocation − Engineer Net Capacity) > 0.1` — the week is under- or over-allocated. Highlighted red by conditional formatting when `TRUE`.

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

## Conditional formatting

The output file includes Excel formula-based conditional formatting rules so that highlights update automatically when the workbook is edited manually.

### Boolean alert highlighting

When per-week capacity data was provided for the primary quarter, overflow weeks use:

* **Engineer Capacity (Bruto)** — the Q mean (average of all Q per-week bruto values). This is the same scalar already derived as `num_engineers`.
* **Engineer Absence** — the default formula (`bruto × absence rate`), since Q-specific absence days don't apply to a future quarter.

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

### Steps per epic (Q then overflow)

Overflow adds 13 more week columns (next quarter’s Mondays). For each epic:

1. **Q phase** — allocate across the 13 requested-quarter weeks using the mode's `weekly_ideal`.
2. **Q top-up** — a second pass over Q weeks fills any remaining deficit (due to rounding or variable capacity) before overflow weeks are touched. Skipped if `block_quarter_completion` is active (see Priority Guard below).
3. **Overflow phase** — only if budget remains after Q top-up, allocate into overflow weeks.
4. **Overflow top-up** — fills any residual deficit in overflow weeks.

This ordering guarantees that a high-priority epic is never forced into overflow simply because its `weekly_ideal` rounds down (e.g. Uniform with `est=4`, `13 weeks` → `weekly_ideal=0.3`, main pass yields 3.9 PW; the Q top-up recovers the 0.1).

### Epic dependencies

An epic may declare a dependency on exactly one other epic using the optional `Depends On` column (the exact `Epic Description` of the upstream epic). The constraint is always "start after": epic B may not receive any allocation until the week **after** the last week in which epic A was allocated.

**Requirements:**
- The referenced epic must exist (exact match on `Epic Description`, case-sensitive).
- The upstream epic (A) must have a **strictly higher priority** (lower priority number) than the dependent epic (B), so that A is fully scheduled before B is considered.
- Only one upstream dependency per epic is supported.

**Effect on the output:** The dependency is a scheduling constraint only — it does not add any new columns to the output table. The weekly allocation cells for B are simply `0` for any week before the constraint is satisfied, which may trigger `Off Estimate = True` if B cannot fit within the quarter.

### Priority Guard

When a higher-priority epic is unfinished in the primary quarter (i.e. its `Total Weeks < Estimation - 0.05`), lower-priority epics are allowed to *start* in Q but are capped so they cannot *complete* in Q. This ensures the higher-priority work is not invisible — it appears as `Off Estimate = True` — and lower priorities are pushed into overflow rather than stealing remaining Q capacity.

---

## Overflow

If **Σ Estimation** over epics exceeds **Σ Engineer Net Capacity** over the **quarter weeks** (weeks can differ), the model adds **13 overflow weeks** (Q+1 Mondays). The CLI prints an info line when that happens.

**Overflow weeks — engineer side:** if you had per-week **bruto** in Q, overflow **bruto** uses the **mean** of those Q values. Overflow **absence** uses the **default rate** (Q-specific day totals do not apply to a future quarter).

---

## Constraints (mandatory checks)

These must hold; violations mean a bug:

1. The total capacity allocated over all weeks to a given Epic cannot exceed its **Estimation**.
2. The total capacity in a given week across all Epics cannot exceed the **Engineer Net Capacity** for that week.
3. No Epic has more than `MAX_WEEKLY_ALLOC_PW` (2.0) PW allocated per week (Sprint / Gaps modes enforce this via `weekly_ideal`; Uniform uses estimation÷n_weeks which may be higher).

---

## 2026 Fiscal quarters

| Quarter | Start Monday | End Monday | Weeks |
|---------|---|---|---|
| Q1 | 2025-12-29 | 2026-03-23 | 13 |
| Q2 | 2026-03-30 | 2026-06-22 | 13 |
| Q3 | 2026-06-29 | 2026-09-21 | 13 |
| Q4 | 2026-09-28 | 2026-12-21 | 13 |
