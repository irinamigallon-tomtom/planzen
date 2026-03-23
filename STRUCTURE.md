# planzen — Repository layout

This file describes **how the repository is split into areas**. For how those areas connect at runtime (CLI, web stack, data flow), see **[ARCHITECTURE.md](ARCHITECTURE.md)**.

```
planzen/
├── pyproject.toml          # Python project metadata and dependencies (uv)
├── src/planzen/            # Installable Python package: CLI + shared logic + Excel I/O
├── tests/                  # Pytest suite and test fixtures
├── web/                    # Optional FastAPI backend and React frontend
├── data/                   # Spreadsheet inputs used for manual checks (see CONTRIBUTING.md)
├── data/examples/          # Curated sample inputs — do not modify from code or scripts
├── output/                 # Default CLI output directory (usually gitignored)
├── logs/                   # Runtime logs (usually gitignored)
├── tmp/                    # Scratch space (usually gitignored)
├── .github/                # Automation and tool hints
├── AGENTS.md               # Orientation for coding agents
├── CONTRIBUTING.md         # Workflow, testing, commits
├── LOGIC.md                # Business rules and algorithms
├── SPECS.md                # Implementation specification (APIs, tests, contracts)
├── ARCHITECTURE.md         # System design and component relationships
├── STRUCTURE.md            # This file
└── README.md               # User getting started
```

`web/` in more detail:

```
web/
├── backend/
│   ├── main.py             # FastAPI app
│   ├── models.py           # Pydantic schemas
│   ├── bridge.py           # JSON ↔ planzen core types
│   ├── persistence.py      # Session JSON files
│   ├── routes/             # API routers
│   └── tests/
└── frontend/
    └── src/
        ├── api/            # HTTP client
        ├── components/     # UI
        ├── store/          # Zustand
        └── types/          # TypeScript types
```
