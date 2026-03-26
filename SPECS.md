# planzen — Implementation specification

- **Behaviour and rules:** **[LOGIC.md](LOGIC.md)**
- **Structure, flows, UI stack:** **[ARCHITECTURE.md](ARCHITECTURE.md)**
- **This file:** contracts only — CLI, validation, output mechanics, `planzen` Python API, constants, HTTP API, and what tests must cover.

---

## 1. CLI

```
planzen INPUT_FILE -q QUARTER [-o OUTPUT_DIR]
```

| Argument / option | Required | Default | Description |
|---|---|---|---|
| `INPUT_FILE` | ✅ | — | Input `.xlsx` |
| `-q` / `--quarter` | ✅ | — | Quarter `1`–`4` |
| `-o` / `--output-dir` | no | `./output/` | Output directory |

Writes one file: `output_{YYMMDDhhmm}_{stem}_formulas.xlsx`.

| Outcome | Exit | Files |
|---|---|---|
| Validation errors | `1` | none |
| Success | `0` | formulas workbook |
| Overflow (estimation > Q capacity) | `0` | same; CLI prints an info line |

---

## 2. Quarters and week labels

Calendar (start/end Mondays): **[LOGIC.md](LOGIC.md)** — *2026 Fiscal quarters*.

Implementation: each quarter is **13 Mondays**. Generated week column headers use `strftime("%b.%d")` (e.g. `Mar.30`, `Jan.05`).

---

## 3. Input validation

Full input format (columns, config labels, per-week mode, row rules): **[LOGIC.md](LOGIC.md)** — *Input*.

**Hard errors** (all reported together; processing stops):

1. No engineer capacity row (`Engineer Capacity (Bruto)` or `Num Engineers`).
2. Sheet missing required epic columns: `Epic Description`, `Estimation`, `Budget Bucket`.
3. Epic `Estimation` not numeric.
4. Epic `Priority` provided but not numeric.
5. `Allocation Mode` set but not one of `Sprint`, `Uniform`, `Gaps`.
6. `Depends On` references an `Epic Description` not present in the file.
7. Epic B has `Depends On` set to epic A, but A does not have a strictly higher priority (lower priority number) than B — the dependency ordering cannot be honoured.

**Warnings** (processing continues):

8. Per-week engineer bruto partially filled for Q — missing weeks use scalar from the mean of filled weeks.

---

## 4. Output workbook

Semantics of rows/columns and flags: **[LOGIC.md](LOGIC.md)** — *Output table structure*, *Conditional formatting*.

### 4.1 Column order (metadata then weeks)

```
Budget Bucket | Epic Description | Priority | Estimation | Total Weeks | Off Estimate | [week columns…]
```

`Off Estimate` is empty on capacity rows, the total row, and the alert row.

### 4.2 Row order

1. Six capacity rows  
2. Epic rows (by `Priority` ascending)  
3. Total row — `Epic Description` = `Weekly Allocation`, `Budget Bucket` = `Total`  
4. Alert row — `Epic Description` = `Off Capacity`

### 4.3 Formulas (`write_output_with_formulas`)

`write_output_with_formulas` calls `write_output`, then replaces value cells with formulas.

| Cell | Pattern |
|---|---|
| Engineer Net Capacity (per week) | `=<bruto> - <absence>` |
| Management Net Capacity (per week) | `=<mgmt_cap> - <mgmt_absence>` |
| `Total Weeks` (capacity + epic rows) | `=SUM(<first_Q_week>:<last_Q_week>)` |
| `Estimation` on total row | `=SUM(<first_epic_est>:<last_epic_est>)` |
| `Total Weeks` on total row | `=SUM(<first_epic_tw>:<last_epic_tw>)` |
| `Weekly Allocation` (per week) | `=SUM(<first_epic_row>:<last_epic_row>)` |
| `Off Estimate` (epic rows) | `=ABS(<tw> - <estimation>) > 0.05` |
| `Off Capacity` (per week) | `=ABS(<weekly_alloc> - <eng_net>) > 0.1` |

Conditional formatting is applied via openpyxl `FormulaRule`; colours and rules match **[LOGIC.md](LOGIC.md)**.

---

## 5. Allocation and overflow

**[LOGIC.md](LOGIC.md)** — *Allocation*, *Overflow*, *Post-allocation checks*.

---

## 6. Python API (`src/planzen/`)

`core_logic.py` does **no** file I/O. Package layout: **[ARCHITECTURE.md](ARCHITECTURE.md)**.

| Function / type | Role |
|---|---|
| `read_input(path, quarter) -> (DataFrame, CapacityConfig)` | Parse sheet; build config (incl. per-week dicts). |
| `validate_input_file(path, quarter?) -> list[str]` | Validation errors; empty = ok. |
| `build_output_table(epics_df, capacity, start, end) -> DataFrame` | Full output table. |
| `validate_allocation(df, capacity, mondays) -> list[str]` | Post-allocation checks. |
| `write_output(df, path)` | Values only; internal; used inside `write_output_with_formulas`. |
| `write_output_with_formulas(df, path, n_base_weeks)` | Values + formulas; `n_base_weeks` = Q week count for `Total Weeks` sums. |

**`CapacityConfig`:** scalars `eng_bruto`, `eng_absence`, `eng_net`, `mgmt_capacity`, `mgmt_absence`, `mgmt_net`; optional `eng_bruto_by_week`, `eng_absence_by_week`; `q_weeks` when per-week absence must distinguish Q from overflow. Accessors `eng_bruto_for`, `eng_absence_for`, `eng_net_for` — Q vs overflow behaviour per **[LOGIC.md](LOGIC.md)** (*Overflow*).

---

## 7. Constants (`config.py`)

```python
MAX_WEEKLY_ALLOC_PW    = 2.0
DEFAULT_MGMT_CAPACITY_PW = 1.0

ALLOC_MODE_SPRINT  = "Sprint"
ALLOC_MODE_UNIFORM = "Uniform"
ALLOC_MODE_GAPS    = "Gaps"
ALLOC_MODE_DEFAULT = ALLOC_MODE_SPRINT
VALID_ALLOC_MODES  = frozenset({"Sprint", "Uniform", "Gaps"})

ABSENCE_DAYS_PER_YEAR  = 37
WORKING_WEEKS_PER_YEAR = 52
WORKING_DAYS_PER_WEEK  = 5
# → ABSENCE_PW_PER_PERSON ≈ 0.1423

OFF_ESTIMATE_THRESHOLD = 0.05
OFF_CAPACITY_THRESHOLD = 0.1

BUCKET_PRIORITY: dict[str, int]
BUCKET_COLORS: list[tuple[str, str]]
```

---

## 8. Tests to cover

### `tests/` — core + Excel + CLI

- **Quarters:** `get_quarter_dates` all four; invalid quarter raises; `_mondays_in_range` count/labels (Q1 `Mon.D` without leading zero on day).
- **`CapacityConfig`:** scalar mode; per-week mode, fallbacks, overflow behaviour per LOGIC.
- **`build_output_table`:** six capacity rows; epics sorted; `Total Weeks` Q-only; `Off Estimate` / `Off Capacity`; column order.
- **Modes:** Sprint cap 2.0 sequential; Uniform spread; Gaps allows zeros without sequential rule.
- **Dependencies:** B's first allocation is in a week strictly after A's last. Priority ordering enforced. Missing dep name → scheduling proceeds without constraint (validation catches it before this point).
- **Overflow:** when Σ estimation > Σ Q net; +13 columns; `Total Weeks` / `Off Estimate` still Q-only.
- **Q top-up:** Uniform rounding shortfall in Q filled in Q before overflow when applicable.
- **`validate_allocation`:** clean pass; violations on over-allocation / negatives.
- **`validate_input_file` / `read_input`:** errors for missing columns / bad mode; blank Priority ok; partial per-week bruto; config rows via Budget Bucket / Type / Epic Description; priority imputation; unnamed columns dropped; rows without Budget Bucket dropped; per-week-only bruto row.
- **`write_output` / `write_output_with_formulas`:** formulas and SUM ranges as in §4.3.
- **`test_integration.py`:** CLI success; validation → exit 1 and no file; messy sample runs.

**Edge cases:** estimation `0`; exact Q fit; single epic > Q capacity; absence > bruto → net ≥ 0 treatment; `Num Engineers` without bruto row; per-week absence NaN → 0 in Q; per-week + overflow bruto/absence rules; Uniform rounding in overflow scenario.

**Dependency cases:** B starts the week after A's last; dep on unknown name → validation error; B priority ≤ A priority → validation error; `Depends On` blank → no constraint.

### `web/backend/tests/`

- **Bridge:** `epics_df_from_models`; `capacity_config_from_model` / `_to_model`; `allocation_df_to_rows`.
- **Routes:** `GET /api/health`; upload with fixture xlsx + quarter; get/put/delete session; `POST …/compute` returns rows and week labels; `GET …/export` returns spreadsheet MIME type. Use `PLANZEN_SESSION_DIR` on a temp dir.

### `web/frontend/`

- **`src/api/client.test.ts`:** each client function — method, URL, body.
- **`src/api/client.error.test.ts`:** non-OK responses propagate.
- **`src/store/sessionStore.test.ts`:** session id state.
- **Components:** `UploadView`, `CapacityEditor`, `EpicsTable`, `AllocationPreview`, `ExportBar` — behaviours described in **[ARCHITECTURE.md](ARCHITECTURE.md)** §6 (smoke/debounce/export).

**Vitest:** `environment: 'jsdom'`, `setupFiles` mocks `ResizeObserver` for AG Grid.

---

## 9. Web API (`web/backend/`)

Stack, CORS, bridge role, session files, and UI: **[ARCHITECTURE.md](ARCHITECTURE.md)**. **Routes and JSON shapes are defined here only.**

Run locally: `uv run uvicorn main:app --app-dir web/backend --reload --port 8000`

Session JSON path: `{PLANZEN_SESSION_DIR or tmp/sessions}/{uuid}.json`. `PLANZEN_SESSION_DIR` overrides the directory (tests).

### 9.1 Models

```python
class CapacityConfigModel(BaseModel):
    eng_bruto: float
    eng_absence: float
    mgmt_capacity: float
    mgmt_absence: float
    eng_bruto_by_week: dict[str, float] = {}
    eng_absence_by_week: dict[str, float] = {}

class EpicModel(BaseModel):
    epic_description: str
    estimation: float
    budget_bucket: str
    priority: float
    allocation_mode: str = "Sprint"
    link: str = ""
    type: str = ""
    milestone: str = ""
    depends_on: str = ""  # Epic Description of upstream epic, or "" for none

class SessionState(BaseModel):
    session_id: str
    filename: str
    quarter: int
    capacity: CapacityConfigModel
    epics: list[EpicModel]
    manual_overrides: dict[str, dict[str, float]] = {}

class AllocationRow(BaseModel):
    label: str
    budget_bucket: str = ""
    priority: float | None = None
    estimation: float | None = None
    total_weeks: float | None = None
    off_estimate: bool | None = None
    week_values: dict[str, float | bool | None] = {}

class ComputeResponse(BaseModel):
    session_id: str
    rows: list[AllocationRow]
    week_labels: list[str]
    has_overflow: bool
    validation_errors: list[str] = []
```

### 9.2 Routes

Prefix: `/api`.

| Method | Path | Request | Response |
|---|---|---|---|
| GET | `/health` | — | `{"status": "ok"}` |
| POST | `/sessions/upload` | multipart `file`, `quarter` | `SessionState` or 422 |
| GET | `/sessions` | — | `list[SessionState]` |
| GET | `/sessions/{id}` | — | `SessionState` |
| DELETE | `/sessions/{id}` | — | 204 |
| PUT | `/sessions/{id}/capacity` | `CapacityConfigModel` | `SessionState` |
| PUT | `/sessions/{id}/epics` | `list[EpicModel]` | `SessionState` |
| PATCH | `/sessions/{id}/overrides` | nested map | `SessionState` |
| POST | `/sessions/{id}/compute` | — | `ComputeResponse` |
| GET | `/sessions/{id}/export` | — | `.xlsx` stream |

`bridge.py` maps JSON ↔ `CapacityConfig` / DataFrames (`capacity_config_from_model`, `capacity_config_to_model`, `epics_df_from_models`, `allocation_df_to_rows`). `POST …/compute` runs `build_output_table`, applies `manual_overrides` to the serialised grid, then `validate_allocation`. `GET …/export` runs the same pipeline and `write_output_with_formulas`.

Frontend TypeScript types mirror these models under `web/frontend/src/types/`; the HTTP client is `web/frontend/src/api/client.ts` (same paths as the table above).
