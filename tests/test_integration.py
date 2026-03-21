"""
Integration tests for planzen.

These tests exercise the full stack — from reading real fixture files on disk
through validation and (where appropriate) the CLI entry point — to catch
regressions that unit tests with in-memory DataFrames cannot surface.

Fixture files live in tests/data/ and are committed to the repository so that
failures are immediately reproducible without any test setup.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from planzen.cli import app
from planzen.excel_io import validate_input_file

DATA = Path(__file__).parent / "data"

runner = CliRunner()


# ---------------------------------------------------------------------------
# validate_input_file against committed fixture files
# ---------------------------------------------------------------------------

def test_valid_input_has_no_errors() -> None:
    assert validate_input_file(DATA / "valid_input.xlsx") == []


def test_missing_config_rows_reports_both_required_rows() -> None:
    errors = validate_input_file(DATA / "missing_config_rows.xlsx")
    labels = "\n".join(errors)
    assert "Engineer Capacity (Bruto)" in labels
    # Management is now optional — should NOT appear as an error


def test_invalid_estimations_reports_all_bad_rows() -> None:
    errors = validate_input_file(DATA / "invalid_estimations.xlsx")
    labels = "\n".join(errors)
    assert "TBD" in labels          # non-numeric
    assert "Alpha" in labels
    assert "Beta" in labels         # negative


def test_missing_required_columns_reports_each_column() -> None:
    errors = validate_input_file(DATA / "missing_required_columns.xlsx")
    labels = "\n".join(errors)
    assert "Priority" in labels
    # Type is optional — should NOT be reported as missing
    assert "Type" not in labels


def test_no_epics_reports_missing_epics() -> None:
    errors = validate_input_file(DATA / "no_epics.xlsx")
    assert any("epic" in e.lower() for e in errors)


def test_bad_config_values_reports_multiple_issues() -> None:
    errors = validate_input_file(DATA / "bad_config_values.xlsx")
    text = "\n".join(errors)
    assert "Engineer Capacity (Bruto)" in text   # non-numeric
    assert "Management Capacity (Bruto)" in text  # zero (not positive)
    assert "Absence" in text                   # negative days
    assert len(errors) >= 3


# ---------------------------------------------------------------------------
# CLI integration — end-to-end via CliRunner
# ---------------------------------------------------------------------------

def test_cli_succeeds_on_valid_input(tmp_path: Path) -> None:
    result = runner.invoke(app, [
        str(DATA / "valid_input.xlsx"),
        "-q", "2",
        "-o", str(tmp_path),
    ])
    assert result.exit_code == 0, result.output
    xlsx_files = list(tmp_path.glob("*.xlsx"))
    assert len(xlsx_files) == 2
    stems = {p.stem for p in xlsx_files}
    assert any("formulas" in s for s in stems)
    assert any("formulas" not in s for s in stems)


def test_cli_exits_nonzero_on_invalid_input(tmp_path: Path) -> None:
    result = runner.invoke(app, [
        str(DATA / "bad_config_values.xlsx"),
        "-q", "2",
        "-o", str(tmp_path),
    ])
    assert result.exit_code != 0


def test_cli_prints_numbered_errors_for_invalid_input(tmp_path: Path) -> None:
    result = runner.invoke(app, [
        str(DATA / "missing_config_rows.xlsx"),
        "-q", "2",
        "-o", str(tmp_path),
    ])
    assert result.exit_code != 0
    assert "1." in result.output
    assert "Engineer Capacity (Bruto)" in result.output
    # Management is optional — no longer a hard error


def test_cli_writes_no_output_on_invalid_input(tmp_path: Path) -> None:
    runner.invoke(app, [
        str(DATA / "bad_config_values.xlsx"),
        "-q", "2",
        "-o", str(tmp_path),
    ])
    assert list(tmp_path.glob("*.xlsx")) == []


def test_cli_rejects_invalid_quarter(tmp_path: Path) -> None:
    result = runner.invoke(app, [
        str(DATA / "valid_input.xlsx"),
        "-q", "9",
        "-o", str(tmp_path),
    ])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Empty and unnamed row handling via fixture file
# ---------------------------------------------------------------------------

def test_empty_and_unnamed_rows_are_discarded(tmp_path: Path) -> None:
    """Fixture has 1 valid epic + 1 fully-empty row + 1 row without Epic Description."""
    from planzen.excel_io import read_input
    epics, eng, mgr, _, _ = read_input(DATA / "empty_and_unnamed_rows.xlsx")
    assert len(epics) == 1
    assert epics.iloc[0]["Epic Description"] == "Alpha"
    assert eng == 5.0
    assert mgr == 2.0


def test_cli_succeeds_despite_empty_rows(tmp_path: Path) -> None:
    result = runner.invoke(app, [
        str(DATA / "empty_and_unnamed_rows.xlsx"),
        "-q", "2",
        "-o", str(tmp_path),
    ])
    assert result.exit_code == 0, result.output
    assert len(list(tmp_path.glob("*.xlsx"))) == 2
