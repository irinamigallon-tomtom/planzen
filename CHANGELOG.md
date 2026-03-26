# Changelog

All notable changes to planzen are documented here.
Commit types follow [Conventional Commits](https://www.conventionalcommits.org/).

## [Unreleased]

### chore — add bump-my-version configuration

Adds `[tool.bumpversion]` to `pyproject.toml` so patch/minor/major releases can be cut with `uv run bump-my-version bump <part>`, and documents the command in `CONTRIBUTING.md`.

### fix — overflow weeks use Q-average bruto and default absence formula

Overflow week capacity previously used raw bruto values instead of the
quarter-average bruto, and the default absence formula was not applied.

### fix — per-week and team info detection

Improved detection of per-week engineer capacity columns and team config
rows. Closes #3.

### feat — support team config labels in Epic Description column

Config rows (Engineer Capacity, Absence, etc.) are now recognised when
their label appears in the `Epic Description` column, not only in
`Budget Bucket` or `Type`. This matches the format used in newer files.

### feat — robust loader with priority imputation and per-week bruto

Loader now imputes missing `Priority` values, reads per-week bruto from
week columns, drops unnamed columns silently, and applies
`Budget Bucket` filtering before passing epics to the allocation engine.
