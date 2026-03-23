# planzen — Implementation Specification

All behaviour described here is implemented and tested. For business rules, calculations, and algorithms see **[LOGIC.md](LOGIC.md)**.

---

## 1. Purpose

`planzen` reads a quarterly engineering plan from an Excel file, allocates weekly capacity to Epics, and writes one review-friendly Excel output file with auditable formulas.

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

One output file is written; its name is derived from the input stem + timestamp:
- `output_{YYMMDDhhmm}_{stem}_formulas.xlsx` — formulas file

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

Applied to the output file via openpyxl `FormulaRule`. See [LOGIC.md](LOGIC.md) for full colour table and rule details.

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

**`write_output(df, path)`** — internal helper: writes values to disk. Called by `write_output_with_formulas` as a first step (formulas are overlaid on top); not called directly by the CLI or the web backend.  
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
- **Q-first allocation**: high-priority Uniform epic with `estimation/n_weeks` rounding deficit must be fully allocated within Q (via Q top-up pass) even when lower-priority epics cause overflow — `Off Estimate = False`, no overflow spill
- `validate_allocation`: passes on valid output; returns violations on over-allocation or negative cells
- `Off Estimate = True` when epic can't be fully allocated in Q; `= False` when exactly allocated
- Epic with 0 PW estimation → allocated 0, `Off Estimate = False`
- Per-week bruto varies → capacity rows vary week by week; overflow check uses per-week sum

### `test_excel_io.py`

- `validate_input_file`: returns errors for missing columns, invalid allocation mode, partial per-week bruto
- `read_input`: returns `(epics_df, CapacityConfig)`; per-week fields populated when D.M. columns present; scalar absence converted to PW/week
- `write_output`: file created; numeric values; conditional formatting applied (internal helper, tested directly)
- `write_output_with_formulas`: `=SUM(first:last_Q_week)` in Total Weeks (capacity + epic rows); Net Capacity rows have subtraction formula; Off Estimate has `ABS`; Off Capacity has `ABS`; SUM references correct epic rows for 1, 3, 5 epics

### `test_integration.py`

- CLI runs end-to-end: one output file created; exit code 0
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
- Uniform epic with `est % n_weeks ≠ 0` (rounding gap) in overflow scenario → fully allocated in Q, no spill to overflow weeks

---

## 11. Web API

### 11.1 Technology

- Python FastAPI, Pydantic v2, uvicorn
- Shares the same `uv` environment as the CLI (same `pyproject.toml`)
- Lives in `web/backend/`; imports `planzen.*` as an installed package (no `sys.path` hacks)
- Session state persisted as JSON files in `tmp/sessions/{session_id}.json`
- `PLANZEN_SESSION_DIR` env var overrides the session directory (used in tests)

Run: `uv run uvicorn main:app --app-dir web/backend --reload --port 8000`

### 11.2 Pydantic Models

```python
class CapacityConfigModel(BaseModel):
    eng_bruto: float            # FTE
    eng_absence: float          # PW/week
    mgmt_capacity: float        # FTE
    mgmt_absence: float         # PW/week
    eng_bruto_by_week: dict[str, float] = {}   # "Mar.30" → PW/week
    eng_absence_by_week: dict[str, float] = {} # "Mar.30" → PW/week

class EpicModel(BaseModel):
    epic_description: str
    estimation: float
    budget_bucket: str
    priority: float
    allocation_mode: str = "Sprint"   # Sprint | Uniform | Gaps
    link: str = ""
    type: str = ""
    milestone: str = ""

class SessionState(BaseModel):
    session_id: str
    filename: str
    quarter: int
    capacity: CapacityConfigModel
    epics: list[EpicModel]
    manual_overrides: dict[str, dict[str, float]] = {}  # epic_description → week_label → PW

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

### 11.3 API Endpoints

All routes are prefixed `/api`.

| Method | Path | Request | Response | Notes |
|---|---|---|---|---|
| GET | `/health` | — | `{"status": "ok"}` | Health check |
| POST | `/sessions/upload` | multipart: `file` (xlsx), `quarter` (int) | `SessionState` | Calls `validate_input_file` then `read_input`; returns 422 with error list on validation failure |
| GET | `/sessions` | — | `list[SessionState]` | Lists all saved sessions |
| GET | `/sessions/{id}` | — | `SessionState` | 404 if not found |
| DELETE | `/sessions/{id}` | — | 204 | Deletes session file |
| PUT | `/sessions/{id}/capacity` | `CapacityConfigModel` | `SessionState` | Replaces capacity; persists |
| PUT | `/sessions/{id}/epics` | `list[EpicModel]` | `SessionState` | Replaces epics list; persists |
| PATCH | `/sessions/{id}/overrides` | `dict[str, dict[str, float]]` | `SessionState` | Merges manual overrides; persists |
| POST | `/sessions/{id}/compute` | — | `ComputeResponse` | Runs `build_output_table`; applies manual overrides as display post-processing; runs `validate_allocation` |
| GET | `/sessions/{id}/export` | — | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` | Runs `write_output_with_formulas`; streams the xlsx; cleans up temp files |

### 11.4 Bridge (`bridge.py`)

Thin adapter between JSON models and core_logic types:

- `capacity_config_from_model(model: CapacityConfigModel) -> CapacityConfig` — builds `CapacityConfig`; converts week-label strings (`"Mar.30"`) to `datetime.date` objects for per-week dicts
- `capacity_config_to_model(config: CapacityConfig, mondays: list[date]) -> CapacityConfigModel` — inverse; converts date keys back to label strings
- `epics_df_from_models(epics: list[EpicModel]) -> pd.DataFrame` — builds DataFrame with column names from `config.py` constants
- `allocation_df_to_rows(df, all_week_labels, quarter_week_labels) -> list[AllocationRow]` — serialises the output DataFrame to `AllocationRow` list; `week_values` uses string week labels as keys

### 11.5 Session Persistence (`persistence.py`)

- Sessions stored as `{PLANZEN_SESSION_DIR}/{session_id}.json` (default dir: `tmp/sessions/`)
- `save_session(state)`, `load_session(id)` (raises HTTP 404 if missing), `list_sessions()`, `delete_session(id)`
- Session IDs: UUID4

### 11.6 Backend Tests to Cover (`web/backend/tests/`)

**`test_bridge.py`:**
- `epics_df_from_models`: correct columns and values
- `capacity_config_from_model`: scalar fields; per-week dict date conversion
- `capacity_config_to_model`: round-trip preserves scalars
- `allocation_df_to_rows`: correct `AllocationRow` list with `week_values`

**`test_routes.py`:**
- `GET /api/health` → 200
- `POST /api/sessions/upload` with example xlsx + quarter=2 → 200, session_id present, epics non-empty
- `GET /api/sessions/{id}` → 200
- `PUT /api/sessions/{id}/capacity` → 200
- `PUT /api/sessions/{id}/epics` → 200
- `DELETE /api/sessions/{id}` → 204; subsequent GET → 404
- `POST /api/sessions/{id}/compute` → 200, rows non-empty, 13+ week_labels
- `GET /api/sessions/{id}/export` → 200, content-type `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`

Tests use `PLANZEN_SESSION_DIR` env var pointing to a `tmp_path` fixture to avoid polluting `tmp/sessions/`.

---

## 12. Web Frontend

### 12.1 Technology

- React 18 + TypeScript (strict mode) + Vite 8
- Tailwind CSS v4 (via `@tailwindcss/vite` plugin)
- AG Grid Community v35 — editable data grids
- TanStack Query v5 — server state (session data)
- Zustand v5 — UI state (current session ID)
- react-dropzone — file upload
- Vitest + React Testing Library + jsdom — tests

Lives in `web/frontend/`. Dev server: `npm run dev` → `http://localhost:5173` (proxies `/api` → `http://localhost:8000`).

### 12.2 TypeScript Types (`src/types/index.ts`)

```typescript
interface CapacityConfig {
  eng_bruto: number;
  eng_absence: number;
  mgmt_capacity: number;
  mgmt_absence: number;
  eng_bruto_by_week: Record<string, number>;
  eng_absence_by_week: Record<string, number>;
}

interface Epic {
  epic_description: string;
  estimation: number;
  budget_bucket: string;
  priority: number;
  allocation_mode: 'Sprint' | 'Uniform' | 'Gaps';
  link: string;
  type: string;
  milestone: string;
}

interface SessionSummary { session_id: string; filename: string; quarter: number; }
interface SessionState extends SessionSummary { capacity: CapacityConfig; epics: Epic[]; manual_overrides: Record<string, Record<string, number>>; }

interface AllocationRow {
  label: string;
  budget_bucket: string;
  priority: number | null;
  estimation: number | null;
  total_weeks: number | null;
  off_estimate: boolean | null;
  week_values: Record<string, number | boolean | null>;
}

interface ComputeResponse {
  session_id: string;
  rows: AllocationRow[];
  week_labels: string[];
  has_overflow: boolean;
  validation_errors: string[];
}
```

### 12.3 API Client (`src/api/client.ts`)

Typed `fetch` wrappers for all backend endpoints. All functions are async and throw on non-OK responses.

| Function | Method + Path |
|---|---|
| `uploadSession(file, quarter)` | POST `/api/sessions/upload` (FormData) |
| `listSessions()` | GET `/api/sessions` |
| `getSession(id)` | GET `/api/sessions/{id}` |
| `deleteSession(id)` | DELETE `/api/sessions/{id}` |
| `updateCapacity(id, capacity)` | PUT `/api/sessions/{id}/capacity` |
| `updateEpics(id, epics)` | PUT `/api/sessions/{id}/epics` |
| `updateOverrides(id, overrides)` | PATCH `/api/sessions/{id}/overrides` |
| `computeAllocation(id)` | POST `/api/sessions/{id}/compute` |
| `exportSession(id)` | GET `/api/sessions/{id}/export` → `Blob` |

### 12.4 State Management

- **Zustand `sessionStore`**: holds `currentSessionId: string | null` and `setCurrentSessionId`. Determines which view is shown (upload vs. editor).
- **TanStack Query**: fetches `['session', sessionId]` in `PlanEditor`; invalidated after capacity/epic updates.
- **Local component state**: `computeResult: ComputeResponse | null` and `isComputing: boolean` in `PlanEditor`.

### 12.5 Component Specifications

**`App.tsx`** — state-based routing: if `currentSessionId` is null, renders `<UploadView>`; otherwise renders `<PlanEditor>`.

**`UploadView`**
- react-dropzone file zone (accepts `.xlsx` only)
- Quarter selector (Q1–Q4)
- Upload button → calls `uploadSession` → on success: sets `currentSessionId`
- Existing sessions list (from `listSessions()`) with Load button per row

**`PlanEditor`** — orchestrator for the edit session:
- Fetches `SessionState` via TanStack Query
- Holds `computeResult` + `isComputing` state
- `recompute()`: calls `computeAllocation`, updates `computeResult`
- Triggers `recompute()` once on mount (after session loads)
- Renders in order: header (filename, quarter, Back button, "Computing…" spinner), `<CapacityEditor>`, `<EpicsTable>`, `<AllocationPreview>`
- `onCapacityChanged` / `onEpicsChanged` callbacks both call `recompute()`

**`CapacityEditor`** — props: `{ sessionId, capacity, onCapacityChanged }`
- Two-column form (Engineer | Management): bruto (FTE) + absence (PW/week) for each
- Debounced 500 ms: calls `updateCapacity` then `onCapacityChanged`
- Collapsible per-week overrides section (read-only display when `eng_bruto_by_week` / `eng_absence_by_week` are non-empty)

**`EpicsTable`** — props: `{ sessionId, epics, onEpicsChanged, debounceMs? }`
- AG Grid editable table with columns: priority, epic_description, estimation, budget_bucket, allocation_mode (dropdown: Sprint/Uniform/Gaps), milestone, type, link, delete action
- "Add Epic" button: appends row with defaults (priority = 0, estimation = 1.0, allocation_mode = "Sprint")
- Row drag-to-reorder (`rowDragManaged`): reorders the visual list without modifying priority values
- Duplicate priority detection: when two or more epics share a priority value, an amber info banner is shown listing the duplicate values
- Debounced 500 ms (0 ms in tests via `debounceMs` prop): calls `updateEpics` then `onEpicsChanged`

**`AllocationPreview`** — props: `{ sessionId, computeResponse, onOverrideChanged }`
- Null state: "No allocation computed yet."
- Validation errors: red banner listing errors
- Overflow: yellow banner "⚠ Overflow: some epics extend into Q+1"
- AG Grid table: pinned `label` column + dynamic week columns from `week_labels`
- `editable` only for week cells in epic rows (not capacity rows, not total/alert rows)
- Cell styling: `off_estimate = true` → `#FFC7CE` / `#9C0006`; Off Capacity row week = true → same; Budget Bucket row background colours matching Excel output (see LOGIC.md — Conditional Formatting)
- On week cell edit: debounced 300 ms → `updateOverrides` → `onOverrideChanged`

**`ExportBar`** — props: `{ sessionId, filename, quarter }`
- "Download Export" button
- On click: calls `exportSession` → creates object URL → triggers `<a download>` click → revokes URL
- Shows loading state ("Exporting…") and error message on failure

### 12.6 Frontend Tests to Cover

**`src/api/client.test.ts`**: `uploadSession`, `listSessions`, `getSession`, `deleteSession`, `updateCapacity`, `updateEpics`, `computeAllocation`, `exportSession` — each verifies correct HTTP method, URL, and body via `vi.stubGlobal('fetch', ...)`.

**`src/api/client.error.test.ts`**: error propagation on 4xx/5xx responses.

**`src/store/sessionStore.test.ts`**: initial state null, `setCurrentSessionId` updates and resets.

**`src/components/UploadView.test.tsx`**: renders inputs; shows error when no file selected; calls `uploadSession` with correct args.

**`src/components/CapacityEditor.test.tsx`**: renders all four fields; `updateCapacity` called after debounce; `onCapacityChanged` fires after successful save.

**`src/components/EpicsTable.test.tsx`**: renders N rows (mock ag-grid-react); Add Epic button exists; `updateEpics` called on add; `onEpicsChanged` fires after save. Uses `debounceMs={0}` + `fireEvent.click` to avoid fake-timer/userEvent incompatibility.

**`src/components/AllocationPreview.test.tsx`**: empty state text; row count matches data; overflow banner; validation error banner.

**`src/components/ExportBar.test.tsx`**: renders button; shows metadata; triggers `exportSession` on click; shows error on failure; button disabled during export.

### 12.7 Vite Configuration

- Proxy: `/api` → `http://localhost:8000` (dev only)
- Vitest: `environment: 'jsdom'`, `globals: true`, `setupFiles: ['./src/test-setup.ts']`
- `test-setup.ts`: imports `@testing-library/jest-dom`; mocks `global.ResizeObserver` for AG Grid
