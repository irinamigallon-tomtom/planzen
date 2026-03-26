# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with this repository.

## Agent guidance

See **[AGENTS.md](AGENTS.md)** — it is the shared source of truth for how coding agents should behave, including the documentation map, safety rules, and which doc to read before any given type of change.

## Architecture

The full design is in **[ARCHITECTURE.md](ARCHITECTURE.md)**. Key invariants:

- `src/planzen/` contains three modules: `core_logic.py` (pure functions, no I/O), `excel_io.py` (all file I/O), `config.py` (constants). No business logic lives anywhere else.
- The CLI (`cli.py`) and the FastAPI backend both call `core_logic.py` directly — there is no duplication.
- The web backend's `bridge.py` is the only place that converts between Pydantic/JSON types and the core's `CapacityConfig` + pandas DataFrames.
- Sessions are JSON files in `tmp/sessions/` — no database.
