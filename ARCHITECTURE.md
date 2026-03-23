# Architecture

This document explains the system architecture for developers and AI agents who want to understand how the components fit together, why certain technology choices were made, and how data flows through the system. It is not an API reference (that's in `SPECS.md`) — it explains the *why* and the *shape* of the system.

---

## 1. Overview

planzen is a local engineering planning tool with two interfaces — a CLI and a web frontend. Both share the same pure Python business logic in `src/planzen/`. The CLI provides a direct, scriptable interface for generating Excel output from a planning spreadsheet. The web frontend adds an interactive layer for uploading plans, editing capacities and epics, previewing computed allocations live, and downloading the final export — all without re-implementing any allocation logic.

---

## 2. Component Map

```
┌──────────────────────────────────────────────────────────┐
│                   planzen repository                      │
│                                                          │
│  ┌──────────────┐      ┌──────────────────────────────┐  │
│  │   CLI        │      │   Web Frontend               │  │
│  │  src/planzen │      │  ┌──────────┐  ┌──────────┐  │  │
│  │  /cli.py     │      │  │ backend  │  │ frontend │  │  │
│  └──────┬───────┘      │  │(FastAPI) │  │ (React)  │  │  │
│         │              │  └────┬─────┘  └────┬─────┘  │  │
│         ▼              │       │    REST API  │        │  │
│  ┌──────────────┐      │       ▼              │        │  │
│  │ core_logic   │◄─────│  core_logic.py       │        │  │
│  │ excel_io     │      │  excel_io.py         │        │  │
│  └──────────────┘      └──────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

---

## 3. Core Business Logic (shared)

`src/planzen/` is the heart of the system. All allocation logic lives here and is shared verbatim by both interfaces.

| Module | Role |
|---|---|
| `core_logic.py` | Pure functions, no I/O: `build_output_table`, `validate_allocation`, `CapacityConfig`, `get_quarter_dates` |
| `excel_io.py` | All file I/O: `read_input`, `validate_input_file`, `write_output`, `write_output_with_formulas` |
| `config.py` | Constants shared by everything (column names, defaults) |

**Invariant**: `core_logic.py` never does I/O. Both the CLI and the web backend call it directly — there is no duplication of business logic.

---

## 4. CLI Interface

`cli.py` is a thin orchestration layer:

```
parse args → read_input() → build_output_table() → write_output_with_formulas()
```

Exit code `1` on validation error, `0` on success. No business logic lives here.

---

## 5. Web Backend (`web/backend/`)

The backend is a layered FastAPI application.

### Layers

- **`main.py`** — FastAPI app factory. Configures CORS (allows `localhost:5173`), registers routers, and uses a lifespan hook to create `tmp/sessions/` on startup.
- **`routes/`** — Three routers (`sessions`, `compute`, `export`), each thin: validate request → call bridge → call core_logic → persist → respond.
- **`bridge.py`** — The key seam. Converts Pydantic models (JSON-friendly) to/from `CapacityConfig` + pandas DataFrames. Week label strings (`"Mar.30"`) ↔ `datetime.date` objects. This is the only place that knows about both representations.
- **`persistence.py`** — Sessions stored as JSON files in `tmp/sessions/`. No database. The `PLANZEN_SESSION_DIR` env var redirects writes during tests.
- **`models.py`** — Pydantic v2 request/response types. `SessionState` is the canonical in-memory representation of a plan.

### Import resolution

`planzen.*` is imported as an installed package (via `uv`/`pyproject.toml`). Backend-internal modules (`models`, `bridge`, etc.) are resolved because `web/backend/` is added to `pythonpath` in `[tool.pytest.ini_options]` for tests, and by `uvicorn --app-dir web/backend` at runtime. No `sys.path` hacks.

---

## 6. Web Frontend (`web/frontend/`)

### Component hierarchy

```
App
├── UploadView            (when no session selected)
│   └── SessionList       (inline: load existing sessions)
└── PlanEditor            (when session active)
    ├── CapacityEditor    (team capacity form, debounced PUT)
    ├── EpicsTable        (AG Grid, editable, debounced PUT)
    ├── AllocationPreview (AG Grid, live-computed, week-cell overrides)
    └── ExportBar         (download xlsx)
```

### Key design decisions

- **Live re-compute**: every edit debounces 500 ms then calls `POST /compute`. The backend runs the full allocation algorithm fresh each time. This is fast enough for typical plans (< 50 epics) and avoids stale-state bugs.
- **Manual overrides**: stored in `SessionState.manual_overrides` (epic_description → week_label → PW). Applied as a post-processing step on the serialised rows after compute — they do not re-run the algorithm with baked-in values. Overrides are display-layer only and do not affect allocation logic.
- **AG Grid**: chosen for its first-class in-cell editing API. The `ag-grid-community` (free) tier is sufficient.
- **No router library**: the app has only two views (upload and editor) managed by a single Zustand boolean (`currentSessionId`). A routing library would be over-engineering.

---

## 7. Data Flow — Edit → Preview

```
User edits a cell in EpicsTable
        │ debounce 500ms
        ▼
PUT /api/sessions/{id}/epics  ──►  persistence.save_session()
        │
        ▼
POST /api/sessions/{id}/compute
        │
        ▼  (backend)
bridge.epics_df_from_models()
        │
        ▼
core_logic.build_output_table(epics_df, capacity, start, end)
        │
        ▼
bridge.allocation_df_to_rows()  +  apply manual_overrides
        │
        ▼
ComputeResponse (JSON)
        │
        ▼  (frontend)
AllocationPreview re-renders with new rows
```

---

## 8. Data Flow — Export

```
User clicks "Download Export"
        │
        ▼
GET /api/sessions/{id}/export
        │
        ▼  (backend)
build_output_table()  →  apply manual_overrides  →  write_output_with_formulas()
        │
        ▼
StreamingResponse (application/vnd.openxmlformats-officedocument.spreadsheetml.sheet)
        │
        ▼  (frontend)
Blob  →  createObjectURL  →  <a download>  →  revokeObjectURL
```

---

## 9. Session Persistence

Sessions are stored as JSON files (`tmp/sessions/{uuid4}.json`). There is no database. This is intentional:

- The tool is designed for local single-user use.
- JSON files are human-readable and debuggable.
- No migration strategy needed.
- Sessions survive backend restarts.

The session JSON is a serialised `SessionState` Pydantic model.

---

## 10. Technology Choices Summary

| Decision | Choice | Rationale |
|---|---|---|
| Backend language | Python (FastAPI) | Business logic is Python; same venv; no polyglot boundary |
| Frontend framework | React + TypeScript | Large ecosystem; excellent AG Grid integration; strict TS for safety |
| Data grid | AG Grid Community | Best-in-class in-cell editing; free tier sufficient |
| State management | TanStack Query + Zustand | Clean separation: server state (Query) vs. UI state (Zustand) |
| Session storage | JSON files | Local-only tool; no DB overhead; human-readable |
| Build tool | Vite | Fast HMR; excellent TS/React support |
| Styling | Tailwind CSS v4 | Utility-first; consistent rapid development |
| Package manager | uv (Python), npm (JS) | Each ecosystem's modern best-in-class tool |

---

## 11. Testing Strategy

| Layer | Tool | Location | Count |
|---|---|---|---|
| CLI core logic | pytest | `tests/` | ~127 tests |
| Web backend | pytest + FastAPI TestClient | `web/backend/tests/` | 25 tests |
| Frontend components | Vitest + React Testing Library | `web/frontend/src/` | 35 tests |

Run all:

```bash
uv run pytest tests/ web/backend/tests/ && cd web/frontend && npm test -- --run
```

---

## 12. Directory Map (with responsibilities)

```
planzen/
├── src/planzen/            # Core business logic — shared by CLI and web
│   ├── cli.py              # CLI entrypoint only
│   ├── core_logic.py       # Pure allocation logic — NO I/O
│   ├── excel_io.py         # All Excel read/write
│   └── config.py           # Shared constants
├── web/
│   ├── backend/            # FastAPI web API
│   │   ├── main.py         # App factory
│   │   ├── models.py       # Pydantic schemas
│   │   ├── bridge.py       # JSON ↔ core_logic types
│   │   ├── persistence.py  # Session JSON storage
│   │   ├── routes/         # sessions, compute, export
│   │   └── tests/          # 25 backend tests
│   └── frontend/           # React + TypeScript
│       └── src/
│           ├── api/        # Typed fetch wrappers
│           ├── components/ # All UI components
│           ├── store/      # Zustand session store
│           └── types/      # Shared TypeScript interfaces
├── tests/                  # CLI + core_logic tests (127)
├── data/examples/          # Human-maintained sample inputs
├── tmp/sessions/           # Runtime: session JSON files (gitignored)
├── output/                 # CLI output directory (gitignored)
├── pyproject.toml          # Single Python env for CLI + backend
├── LOGIC.md                # Business rules and algorithms
├── SPECS.md                # Full implementation spec (CLI + web)
├── ARCHITECTURE.md         # This file
└── CONTRIBUTING.md         # Developer workflow
```
