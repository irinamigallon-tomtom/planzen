## Units

| Context | Unit |
|---|---|
| Team headcount (`Engineer Bruto Capacity`, `Manager Bruto Capacity`) | **FTE** (full-time equivalents; fractions allowed, e.g. 2.5) |
| Absence input (`Engineer Absence (days)`, `Manager Absence (days)`) | **working days** — total for the selected quarter |
| Epic `Estimation` | **Person-Weeks (PW)** — total effort |
| All output week columns (capacity rows and epic rows) | **PW / week** |
| `Total Weeks` column | **PW** — sum across all 13 weeks |

1 PW = 1 person working a full week. Cell values are rounded to **0.1 PW** increments.

---

## Input

The user provides a single `.xlsx` file with one sheet. Team config rows appear at the top; epic rows follow.

### Team config rows

| `Epic Description` label | `Estimation` value | Unit | Required? |
|---|---|---|---|
| `Engineer Bruto Capacity` | e.g. `5.0` | FTE | ✅ |
| `Manager Bruto Capacity` | e.g. `2.0` | FTE | ✅ |
| `Engineer Absence (days)` | e.g. `10` | working days (quarter total) | optional |
| `Manager Absence (days)` | e.g. `4` | working days (quarter total) | optional |

When absence is omitted the default formula applies: **37 days/year** (30 vacation + 7 sick) ÷ 52 weeks ÷ 5 days ≈ **0.142 PW/person/week**.

### Epic columns (required)

### Epic columns

| Column | Required | Unit |
|---|---|---|
| `Epic Description` | ✅ | — |
| `Estimation` | ✅ | PW (total effort) |
| `Budget Bucket` | ✅ | — |
| `Link` | ✅ | — |
| `Priority` | ✅ | — (lower = higher priority) |
| `Type` | optional | — |
| `Milestone` | optional | — |

Column order does not matter. Any additional columns are preserved.

---

## Output table structure

One row per Epic plus 6 capacity header rows and one total row.

### Capacity header rows (unit: PW/week)

| Row | Formula | Default example (5 eng, 2 mgr) |
|---|---|---|
| Engineer Capacity (Bruto) | `E × 1 PW/week` | 5.0 |
| Engineer Absence | `absence_days ÷ 5 ÷ n_weeks` OR `E × 0.142` | 0.7 |
| Engineer Net Capacity | Bruto − Absence | 4.3 |
| Management Capacity | `M × 1 PW/week` | 2.0 |
| Management Absence | `absence_days ÷ 5 ÷ n_weeks` OR `M × 0.142` | 0.3 |
| Management Net Capacity | Capacity − Absence | 1.7 |

### Epic rows

| Column | Unit |
|---|---|
| Budget Bucket | — |
| Epic / Capacity Metric | — |
| Priority | — |
| Estimation | PW (total) |
| Total Weeks | PW (total for the quarter) |
| `Mon.DD` week columns | PW/week |

### Total row

`Weekly Allocation` — sum of all epic allocations per week (PW/week).

---

## Mandatory checks

The tool validates these after allocation (violations indicate a logic bug):

1. The total capacity allocated over all weeks to a given Epic cannot exceed its **Estimation**.
2. The total capacity in a given week across all Epics cannot exceed the **Engineer Net Capacity** for that week.
3. *(Planned)* No Epic has more than **2 PW** allocated per week — at most a tandem of 2 people working full time on one thing.

---

## Allocation algorithm

1. Sort epics by Priority ascending (lower number = higher priority).
2. For each epic, compute `weekly_ideal = max(round(Estimation / n_weeks, 0.1), 0.1)`.
3. Iterate weeks: allocate `min(weekly_ideal, remaining_capacity, budget_left)`, minimum 0.1 PW when capacity > 0 and budget > 0 (sequential constraint).
4. A week gets 0 for an epic **only** when that week's remaining capacity is fully consumed by higher-priority epics.

Overflow is intentional: if total estimations exceed quarter capacity, lower-priority epics are partially allocated (`Total Weeks < Estimation`).

---

## 2026 Fiscal Quarters

| Quarter | Start Monday | End Monday | Weeks |
|---------|---|---|---|
| Q1 | 2025-12-29 | 2026-03-23 | 13 |
| Q2 | 2026-03-30 | 2026-06-22 | 13 |
| Q3 | 2026-06-29 | 2026-09-21 | 13 |
| Q4 | 2026-09-28 | 2026-12-21 | 13 |
