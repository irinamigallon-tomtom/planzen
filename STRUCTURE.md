# planzen — Directory Structure

```
planzen/
├── pyproject.toml              # project metadata and dependencies (managed by uv)
├── src/planzen/
│   ├── cli.py                  # CLI entrypoint (argparse, orchestration only)
│   ├── core_logic.py           # Pure business logic — no file I/O
│   ├── excel_io.py             # All Excel read/write
│   └── config.py               # Constants: labels, fiscal quarters, thresholds
├── tests/
│   ├── test_core_logic.py      # Unit + integration tests for allocation logic
│   ├── test_excel_io.py        # Tests for Excel I/O and formula generation
│   ├── test_integration.py     # End-to-end CLI tests
│   └── data/                   # Fixture files (.xlsx) used by tests
├── data/examples/              # Human-maintained sample inputs — never modify programmatically
├── output/                     # Default destination for generated files
├── logs/                       # Runtime log files (not committed)
├── tmp/                        # Scratch space (not committed)
├── .github/
│   └── copilot-instructions.md # Points AI tools to AGENTS.md
├── AGENTS.md                   # Agent orientation and doc map (read first)
├── CONTRIBUTING.md             # Developer workflow: commands, testing, commits
├── LOGIC.md                    # Business rules: what the app computes and why
├── SPECS.md                    # Implementation spec: API, architecture, constants, tests
├── STRUCTURE.md                # This file
└── README.md                   # End-user documentation
```
