# planzen

planzen reads a quarterly engineering plan from Excel, allocates weekly capacity across epics, and writes one review-friendly workbook with auditable formulas. A **CLI** and an optional **web app** share the same engine.

---

## What you need

- **Input:** one `.xlsx` file with a single sheet. **Team capacity rows** (engineer/management headcount and absence, and optional per-week columns) come first; **epic rows** follow. Blank rows between sections are ignored.
- **Details:** column names, units, defaults, allocation rules, and how the output is built are documented in **[LOGIC.md](LOGIC.md)**.

---

## How to run

### CLI

Requires [uv](https://github.com/astral-sh/uv).

```bash
uv sync
uv run planzen INPUT_FILE -q QUARTER [-o OUTPUT_DIR]
```

`-q` is the fiscal quarter (1–4). Output defaults to `./output/` and is named like `output_YYYYMMddhhmm_<input-stem>_formulas.xlsx`.

### Web app (optional)

From the repository root (after `npm install` the first time):

```bash
npm run dev
```

Starts the API and the UI; open the URL shown in the terminal (typically **http://localhost:5173**). For layout, API, and UI behaviour, see **[ARCHITECTURE.md](ARCHITECTURE.md)**. Developer commands and workflow: **[CONTRIBUTING.md](CONTRIBUTING.md)**.

---

## Other documentation

| Doc | Use it for |
|-----|------------|
| [LOGIC.md](LOGIC.md) | Business rules, units, input/output, allocation, overflow |
| [SPECS.md](SPECS.md) | CLI contract, implementation details, tests, web API summary |
| [ARCHITECTURE.md](ARCHITECTURE.md) | How CLI, backend, and frontend fit together |
| [STRUCTURE.md](STRUCTURE.md) | Where files live in the repo (no deep design) |
