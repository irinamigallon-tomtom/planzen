## Units

| Context | Unit |
|---|---|
| Team headcount (`Engineer Bruto Capacity`, `Manager Bruto Capacity`) | **FTE** (full-time equivalents; fractions allowed, e.g. 2.5) |
| Absence input (`Engineer Absence (days)`, `Manager Absence (days)`) | **working days** — total for the selected quarter |
| Epic `Estimation` | **Person-Weeks (PW)** — total effort for the Epic|
| All output week columns (capacity rows and epic rows) | **PW / week** |
| `Total Weeks` column | **PW** — sum across all 13 weeks |

1 PW = 1 person working a full week. Cell values are rounded to **0.1 PW** increments.

---

## Input

The user provides a single `.xlsx` file with one sheet. Team config rows appear at the top; epic rows follow.

### Team config rows

The config label may appear in either the `Epic Description` column or the `Budget Bucket` column (useful when `Epic Description` is left blank for config rows). Matching is case-insensitive and strips parenthetical suffixes.

| Config label | `Estimation` value | Unit | Required? |
|---|---|---|---|
| `Engineer Bruto Capacity` | e.g. `5.0` | FTE | ✅ |
| `Manager Bruto Capacity` | e.g. `2.0` | FTE | ✅ |
| `Engineer Absence (days)` | e.g. `10` | working days (quarter total) | optional |
| `Manager Absence (days)` | e.g. `4` | working days (quarter total) | optional |

When absence is omitted the default formula applies: **37 days/year** (30 vacation + 7 sick) ÷ 52 weeks ÷ 5 days ≈ **0.142 PW/person/week**.

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

Column order does not matter. Any additional columns are preserved. Column names are matched case-insensitively (e.g. `estimation` is accepted).

### Row handling

- A row with no `Epic Description` value is **discarded** (logged as a warning).
- A row with an `Epic Description` but no `Estimation` value defaults to **0 PW** (logged as a warning).

---

## Output table structure

### Capacity header rows (unit: PW/week)

| Row | Formula | Default example (5 eng, 2 mgr) |
|---|---|---|
| Engineer Capacity (Bruto) | `E × 1 PW/week` | 5.0 |
| Engineer Absence | `absence_days ÷ 5 ÷ n_weeks` OR `E × 0.142` | 0.7 |
| Engineer Net Capacity | Bruto − Absence | 4.3 |
| Management Capacity (Bruto) | `M × 1 PW/week` | 2.0 |
| Management Absence | `absence_days ÷ 5 ÷ n_weeks` OR `M × 0.142` | 0.3 |
| Management Net Capacity | Bruto Capacity − Absence | 1.7 |

### Epic rows (sorted by Priority ascending)

| Column | Unit | Description |
|---|---|---|
| `Budget Bucket` | — | From input |
| `Epic Description` | — | Epic name |
| `Priority` | — | From input |
| `Estimation` | PW (total) | Total effort budget from input |
| `Total Weeks` | PW (total for the quarter) | Sum of all weekly allocations |
| `Off Estimate` | bool | `True` if `abs(Total Weeks − Estimation) > 0.05` — epic was not fully allocated |
| `Mon.DD` week columns | PW/week | Capacity allocated to this epic that week |

### Total row

`Weekly Allocation` — sum of all epic allocations per week (PW/week).

### Alert row

`Off Capacity` — last row. Per week column: `True` if `abs(Weekly Allocation − Engineer Net Capacity) > 0.1` — the week is under- or over-allocated.

---

## Allocation algorithm

Epics are processed in **Priority order** (lower number = higher priority). Each epic claims capacity before lower-priority ones.

The `Allocation Mode` column (optional per epic) controls how capacity is spread across weeks. When blank or unrecognised, **Sprint** mode is used.

### Modes

| Mode | Behaviour |
|---|---|
| **Sprint** (default) | Claim up to `MAX_WEEKLY_ALLOC_PW = 2.0` PW per week; sequential. |
| **Uniform** | Spread `Estimation / n_weeks` evenly across all weeks; sequential. |
| **Gaps** | Same rate as Sprint (`MAX_WEEKLY_ALLOC_PW`) but without the sequential minimum — a week may receive 0 even when capacity > 0. |

`MAX_WEEKLY_ALLOC_PW = 2.0` is configurable in `config.py` and represents at most a tandem of 2 people working full-time on one thing per week.

**Sequential constraint** (Sprint and Uniform): once an epic starts, every subsequent week with available capacity must receive ≥ 0.1 PW — a `0` is only allowed when that week is fully consumed by higher-priority epics.

---

## Overflow

Overflow is automatic: when `Σ(Estimation) > Engineer Net Capacity × 13`, the allocation window extends into Q+1 (13 additional Mondays). Without overflow, lower-priority epics would be partially allocated and show `Total Weeks < Estimation`. The CLI prints an informational message when overflow occurs.

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
