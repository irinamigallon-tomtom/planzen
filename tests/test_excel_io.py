"""
Tests for excel_io.py — values output and formula output.

Includes parametrized tests that vary the number of epics to ensure
formula row/column references are dynamically correct regardless of
sheet shape.
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import openpyxl
import pandas as pd
import pytest
from openpyxl.utils import get_column_letter

from planzen.config import (
    FISCAL_QUARTERS,
    LABEL_ENG_ABSENCE,
    LABEL_ENG_BRUTO,
    LABEL_ENG_NET,
    LABEL_MGMT_ABSENCE,
    LABEL_MGMT_CAPACITY,
    LABEL_MGMT_NET,
    LABEL_TOTAL_ROW,
    OUT_COL_EPIC,
    OUT_COL_TOTAL_WEEKS,
)
from planzen.core_logic import CapacityConfig, build_output_table
from planzen.excel_io import formulas_path, read_input, validate_input_file, write_output, write_output_with_formulas

# ---------------------------------------------------------------------------
# Shared fixtures and helpers
# ---------------------------------------------------------------------------

_CAPACITY = CapacityConfig(num_engineers=5, num_managers=2)
_Q1_START = FISCAL_QUARTERS[1][0]
_START = _Q1_START
_END = _Q1_START + timedelta(weeks=3)  # 4 Mondays

_EPICS = pd.DataFrame([
    {"Epic Description": "Epic A", "Estimation": 10.0, "Budget Bucket": "Core",
     "Type": "Feature", "Link": "https://jira.example.com/A", "Priority": 0, "Milestone": "Q1"},
    {"Epic Description": "Epic B", "Estimation": 5.0,  "Budget Bucket": "Core",
     "Type": "Feature", "Link": "https://jira.example.com/B", "Priority": 1, "Milestone": "Q1"},
])

_CAPACITY_LABELS = {
    LABEL_ENG_BRUTO, LABEL_ENG_ABSENCE, LABEL_ENG_NET,
    LABEL_MGMT_CAPACITY, LABEL_MGMT_ABSENCE, LABEL_MGMT_NET,
    LABEL_TOTAL_ROW,
}


def _make_epics(n: int) -> pd.DataFrame:
    """Build a DataFrame with *n* epics of varying estimations."""
    return pd.DataFrame([
        {
            "Epic Description": f"Epic {i}",
            "Estimation": float(10 * (i + 1)),
            "Budget Bucket": "Core",
            "Type": "Feature",
            "Link": f"https://jira.example.com/{i}",
            "Priority": i,
            "Milestone": "Q1",
        }
        for i in range(n)
    ])


@pytest.fixture()
def output_df() -> pd.DataFrame:
    return build_output_table(_EPICS, _CAPACITY, _START, _END)


@pytest.fixture()
def values_file(tmp_path: Path, output_df: pd.DataFrame) -> Path:
    p = tmp_path / "output.xlsx"
    write_output(output_df, p)
    return p


@pytest.fixture()
def formulas_file(tmp_path: Path, output_df: pd.DataFrame) -> Path:
    p = tmp_path / "output_formulas.xlsx"
    write_output_with_formulas(output_df, p)
    return p


def _find_row(ws, label: str, label_col: int = 2) -> int:
    """Return the 1-based Excel row number whose label_col cell equals *label*."""
    for row in ws.iter_rows():
        if row[label_col - 1].value == label:
            return row[0].row
    raise KeyError(f"Label {label!r} not found in worksheet")


def _week_cols(ws, header_row: int = 1) -> list[int]:
    """Return 1-based column indices for all week columns (non-metadata columns)."""
    non_week = {"Budget Bucket", "Epic / Capacity Metric", "Priority", "Estimation", "Total Weeks"}
    return [
        cell.column for cell in ws[header_row]
        if cell.value not in non_week and cell.value is not None
    ]


def _total_weeks_col(ws, header_row: int = 1) -> int:
    for cell in ws[header_row]:
        if cell.value == "Total Weeks":
            return cell.column
    raise KeyError("Total Weeks column not found")


# ---------------------------------------------------------------------------
# formulas_path helper
# ---------------------------------------------------------------------------

def test_formulas_path_appends_suffix() -> None:
    assert formulas_path(Path("out/result.xlsx")) == Path("out/result_formulas.xlsx")


def test_formulas_path_preserves_directory() -> None:
    p = formulas_path(Path("/data/examples/output_example.xlsx"))
    assert p == Path("/data/examples/output_example_formulas.xlsx")


# ---------------------------------------------------------------------------
# read_plan: column validation and flexibility
# ---------------------------------------------------------------------------

def _base_row(**extra) -> dict:
    return {
        "Epic Description": "E", "Estimation": 1.0, "Budget Bucket": "B",
        "Type": "Feature", "Link": "http://x", "Priority": 0,
        **extra,
    }


def _config_rows() -> list[dict]:
    return [
        {"Epic Description": "Engineer Bruto Capacity", "Estimation": 5.0},
        {"Epic Description": "Manager Bruto Capacity", "Estimation": 2.0},
    ]


def _write_input(path: Path, epics: list[dict], config: list[dict] | None = None) -> None:
    rows = (config if config is not None else _config_rows()) + epics
    pd.DataFrame(rows).to_excel(path, index=False)


# ---------------------------------------------------------------------------
# read_input: team config + epic parsing
# ---------------------------------------------------------------------------

def test_read_input_returns_engineers_and_managers(tmp_path: Path) -> None:
    p = tmp_path / "input.xlsx"
    _write_input(p, [_base_row()])
    _, eng, mgr, _, _ = read_input(p)
    assert eng == 5.0
    assert mgr == 2.0


def test_read_input_returns_none_when_absence_omitted(tmp_path: Path) -> None:
    p = tmp_path / "input.xlsx"
    _write_input(p, [_base_row()])
    _, _, _, eng_abs, mgmt_abs = read_input(p)
    assert eng_abs is None
    assert mgmt_abs is None


def test_read_input_parses_optional_absence_days(tmp_path: Path) -> None:
    p = tmp_path / "input.xlsx"
    config = _config_rows() + [
        {"Epic Description": "Engineer Absence (days)", "Estimation": 10.0},
        {"Epic Description": "Manager Absence (days)", "Estimation": 4.0},
    ]
    _write_input(p, [_base_row()], config=config)
    _, _, _, eng_abs, mgmt_abs = read_input(p)
    assert eng_abs == 10.0
    assert mgmt_abs == 4.0


def test_read_input_epic_rows_exclude_config_rows(tmp_path: Path) -> None:
    p = tmp_path / "input.xlsx"
    _write_input(p, [_base_row()])
    epics, _, _, _, _ = read_input(p)
    assert "Engineer Bruto Capacity" not in epics["Epic Description"].values
    assert "Manager Bruto Capacity" not in epics["Epic Description"].values
    assert len(epics) == 1


def test_read_input_accepts_extra_columns(tmp_path: Path) -> None:
    p = tmp_path / "input.xlsx"
    _write_input(p, [_base_row(**{"Extra Col": "ignored"})])
    epics, _, _, _, _ = read_input(p)
    assert "Extra Col" in epics.columns


def test_read_input_accepts_optional_milestone(tmp_path: Path) -> None:
    p_with = tmp_path / "with.xlsx"
    p_without = tmp_path / "without.xlsx"
    _write_input(p_with, [_base_row(Milestone="Q1")])
    _write_input(p_without, [_base_row()])
    read_input(p_with)
    read_input(p_without)


def test_read_input_preserves_column_order(tmp_path: Path) -> None:
    p = tmp_path / "input.xlsx"
    # Config rows come first; their keys (Epic Description, Estimation) set the
    # initial column order.  Epic-only keys follow in insertion order.
    rows = _config_rows() + [{
        "Epic Description": "E", "Estimation": 1.0,
        "Priority": 0, "Link": "http://x",
        "Type": "Feature", "Budget Bucket": "B",
    }]
    pd.DataFrame(rows).to_excel(p, index=False)
    epics, _, _, _, _ = read_input(p)
    # Column order must match the file: Epic Description and Estimation come first
    # (from config rows), then the remaining epic columns.
    assert epics.columns[0] == "Epic Description"
    assert epics.columns[1] == "Estimation"
    # All required epic columns must be present (Type is optional)
    for col in ("Priority", "Link", "Budget Bucket"):
        assert col in epics.columns


def test_read_input_raises_for_missing_engineers_row(tmp_path: Path) -> None:
    p = tmp_path / "input.xlsx"
    config = [{"Epic Description": "Manager Bruto Capacity", "Estimation": 2.0}]
    _write_input(p, [_base_row()], config=config)
    with pytest.raises(ValueError, match="Engineer Bruto Capacity"):
        read_input(p)


def test_read_input_raises_for_missing_required_epic_columns(tmp_path: Path) -> None:
    p = tmp_path / "input.xlsx"
    # Epic row missing Budget Bucket, Link, Priority (Type is optional)
    rows = _config_rows() + [{"Epic Description": "E", "Estimation": 1.0}]
    pd.DataFrame(rows).to_excel(p, index=False)
    with pytest.raises(ValueError, match="missing required columns"):
        read_input(p)


# ---------------------------------------------------------------------------
# read_input: fuzzy / case-insensitive config label matching
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("eng_label", [
    "Engineer Bruto Capacity",   # canonical
    "engineer bruto capacity",   # all lowercase
    "ENGINEER BRUTO CAPACITY",   # all uppercase
    "  Engineer Bruto Capacity ",  # extra whitespace
])
def test_read_input_accepts_engineer_label_variants(tmp_path: Path, eng_label: str) -> None:
    p = tmp_path / "input.xlsx"
    config = [
        {"Epic Description": eng_label, "Estimation": 4.0},
        {"Epic Description": "Manager Bruto Capacity", "Estimation": 2.0},
    ]
    _write_input(p, [_base_row()], config=config)
    _, eng, _, _, _ = read_input(p)
    assert eng == 4.0


@pytest.mark.parametrize("mgr_label", [
    "Manager Bruto Capacity",  # canonical
    "Manager Bruto Capacity",     # singular "Manager" instead of "Management"
    "manager bruto capacity",     # lowercase + singular
])
def test_read_input_accepts_manager_label_variants(tmp_path: Path, mgr_label: str) -> None:
    p = tmp_path / "input.xlsx"
    config = [
        {"Epic Description": "Engineer Bruto Capacity", "Estimation": 5.0},
        {"Epic Description": mgr_label, "Estimation": 2.0},
    ]
    _write_input(p, [_base_row()], config=config)
    _, _, mgr, _, _ = read_input(p)
    assert mgr == 2.0


@pytest.mark.parametrize("eng_abs_label,mgr_abs_label", [
    ("Engineer Absence (days)", "Manager Absence (days)"),  # canonical
    ("Engineers absence", "Managers absence"),              # plural, no "(days)"
    ("engineer absence", "manager absence"),                # lowercase, no "(days)"
])
def test_read_input_accepts_absence_label_variants(
    tmp_path: Path, eng_abs_label: str, mgr_abs_label: str
) -> None:
    p = tmp_path / "input.xlsx"
    config = _config_rows() + [
        {"Epic Description": eng_abs_label, "Estimation": 10.0},
        {"Epic Description": mgr_abs_label, "Estimation": 4.0},
    ]
    _write_input(p, [_base_row()], config=config)
    _, _, _, eng_abs, mgr_abs = read_input(p)
    assert eng_abs == 10.0
    assert mgr_abs == 4.0



# ---------------------------------------------------------------------------
# read_input: empty row and unnamed row handling
# ---------------------------------------------------------------------------

def test_read_input_discards_fully_empty_rows(tmp_path: Path) -> None:
    p = tmp_path / "input.xlsx"
    rows = _config_rows() + [
        _base_row(),
        # fully empty row
        {"Epic Description": None, "Estimation": None, "Budget Bucket": None,
         "Type": None, "Link": None, "Priority": None},
    ]
    pd.DataFrame(rows).to_excel(p, index=False)
    epics, _, _, _, _ = read_input(p)
    assert len(epics) == 1
    assert epics.iloc[0]["Epic Description"] == "E"


def test_read_input_discards_rows_without_epic_description(tmp_path: Path) -> None:
    p = tmp_path / "input.xlsx"
    rows = _config_rows() + [
        _base_row(),
        # row with data but no Epic Description
        {"Epic Description": None, "Estimation": 3.0, "Budget Bucket": "Core",
         "Type": "Feature", "Link": "http://x", "Priority": 2},
    ]
    pd.DataFrame(rows).to_excel(p, index=False)
    epics, _, _, _, _ = read_input(p)
    assert len(epics) == 1


def test_read_input_logs_warning_for_unnamed_rows(tmp_path: Path, caplog) -> None:
    import logging
    p = tmp_path / "input.xlsx"
    rows = _config_rows() + [
        _base_row(),
        {"Epic Description": None, "Estimation": 3.0, "Budget Bucket": "Core",
         "Type": "Feature", "Link": "http://x", "Priority": 2},
    ]
    pd.DataFrame(rows).to_excel(p, index=False)
    with caplog.at_level(logging.WARNING, logger="planzen.excel_io"):
        read_input(p)
    assert any("Discarding" in r.message for r in caplog.records)


def test_read_input_handles_mixed_empty_and_valid_rows(tmp_path: Path) -> None:
    """Empty rows scattered between valid rows are all silently dropped."""
    p = tmp_path / "input.xlsx"
    rows = _config_rows() + [
        _base_row(**{"Epic Description": "A", "Priority": 1}),
        {"Epic Description": None, "Estimation": None},  # empty
        _base_row(**{"Epic Description": "B", "Priority": 2}),
        {"Epic Description": None, "Estimation": None},  # empty
    ]
    pd.DataFrame(rows).to_excel(p, index=False)
    epics, _, _, _, _ = read_input(p)
    assert list(epics["Epic Description"]) == ["A", "B"]


# ---------------------------------------------------------------------------
# validate_input_file: user-friendly error collection
# ---------------------------------------------------------------------------

def test_validate_returns_empty_for_valid_file(tmp_path: Path) -> None:
    p = tmp_path / "input.xlsx"
    _write_input(p, [_base_row()])
    assert validate_input_file(p) == []


def test_validate_reports_unreadable_file(tmp_path: Path) -> None:
    p = tmp_path / "missing.xlsx"
    errors = validate_input_file(p)
    assert len(errors) == 1
    assert "not found" in errors[0].lower() or "cannot" in errors[0].lower()


def test_validate_reports_missing_epic_description_column(tmp_path: Path) -> None:
    p = tmp_path / "input.xlsx"
    pd.DataFrame([{"Estimation": 1.0}]).to_excel(p, index=False)
    errors = validate_input_file(p)
    assert any("Epic Description" in e for e in errors)


def test_validate_reports_missing_engineers_config_row(tmp_path: Path) -> None:
    p = tmp_path / "input.xlsx"
    config = [{"Epic Description": "Manager Bruto Capacity", "Estimation": 2.0}]
    _write_input(p, [_base_row()], config=config)
    errors = validate_input_file(p)
    assert any("Engineer Bruto Capacity" in e for e in errors)


def test_validate_reports_missing_managers_config_row(tmp_path: Path) -> None:
    p = tmp_path / "input.xlsx"
    config = [{"Epic Description": "Engineer Bruto Capacity", "Estimation": 5.0}]
    _write_input(p, [_base_row()], config=config)
    errors = validate_input_file(p)
    assert any("Manager Bruto Capacity" in e for e in errors)


def test_validate_reports_non_positive_engineers(tmp_path: Path) -> None:
    p = tmp_path / "input.xlsx"
    config = [
        {"Epic Description": "Engineer Bruto Capacity", "Estimation": 0},
        {"Epic Description": "Manager Bruto Capacity", "Estimation": 2.0},
    ]
    _write_input(p, [_base_row()], config=config)
    errors = validate_input_file(p)
    assert any("Engineer Bruto Capacity" in e for e in errors)
    assert any("greater than 0" in e or "positive" in e.lower() for e in errors)


def test_validate_reports_non_numeric_engineers(tmp_path: Path) -> None:
    p = tmp_path / "input.xlsx"
    config = [
        {"Epic Description": "Engineer Bruto Capacity", "Estimation": "lots"},
        {"Epic Description": "Manager Bruto Capacity", "Estimation": 2.0},
    ]
    _write_input(p, [_base_row()], config=config)
    errors = validate_input_file(p)
    assert any("Engineer Bruto Capacity" in e for e in errors)


def test_validate_reports_negative_absence_days(tmp_path: Path) -> None:
    p = tmp_path / "input.xlsx"
    config = _config_rows() + [
        {"Epic Description": "Engineer Absence (days)", "Estimation": -3},
    ]
    _write_input(p, [_base_row()], config=config)
    errors = validate_input_file(p)
    assert any("Absence" in e for e in errors)
    assert any("negative" in e.lower() or ">= 0" in e for e in errors)


def test_validate_reports_missing_required_epic_columns(tmp_path: Path) -> None:
    p = tmp_path / "input.xlsx"
    rows = _config_rows() + [{"Epic Description": "E", "Estimation": 1.0}]
    pd.DataFrame(rows).to_excel(p, index=False)
    errors = validate_input_file(p)
    assert any("Budget Bucket" in e or "Priority" in e for e in errors)


def test_validate_reports_no_epic_rows(tmp_path: Path) -> None:
    p = tmp_path / "input.xlsx"
    _write_input(p, [], config=_config_rows())
    errors = validate_input_file(p)
    assert any("epic" in e.lower() for e in errors)


def test_validate_reports_non_numeric_estimation(tmp_path: Path) -> None:
    p = tmp_path / "input.xlsx"
    _write_input(p, [_base_row(**{"Estimation": "TBD"})])
    errors = validate_input_file(p)
    assert any("Estimation" in e for e in errors)
    assert any("numeric" in e.lower() or "number" in e.lower() for e in errors)


def test_validate_reports_negative_estimation(tmp_path: Path) -> None:
    p = tmp_path / "input.xlsx"
    _write_input(p, [_base_row(**{"Estimation": -1.0})])
    errors = validate_input_file(p)
    assert any("Estimation" in e for e in errors)


def test_validate_reports_missing_priority(tmp_path: Path) -> None:
    p = tmp_path / "input.xlsx"
    row = _base_row()
    row["Priority"] = None
    _write_input(p, [row])
    errors = validate_input_file(p)
    assert any("Priority" in e for e in errors)


def test_validate_collects_multiple_errors(tmp_path: Path) -> None:
    """All issues are reported at once, not just the first one."""
    p = tmp_path / "input.xlsx"
    # No config rows at all, and epic has bad Estimation
    rows = [{"Epic Description": "E", "Estimation": "TBD", "Budget Bucket": "B",
             "Type": "F", "Link": "http://x", "Priority": 0}]
    pd.DataFrame(rows).to_excel(p, index=False)
    errors = validate_input_file(p)
    assert len(errors) >= 2  # at least: missing engineers row + bad estimation


# ---------------------------------------------------------------------------
# Values file: no formula strings
# ---------------------------------------------------------------------------

def test_values_file_is_created(values_file: Path) -> None:
    assert values_file.exists()


def test_values_file_net_capacity_cells_are_numeric(values_file: Path) -> None:
    wb = openpyxl.load_workbook(values_file, data_only=True)
    ws = wb.active
    eng_net_row = _find_row(ws, LABEL_ENG_NET)
    mgmt_net_row = _find_row(ws, LABEL_MGMT_NET)
    for col_idx in _week_cols(ws):
        assert isinstance(ws.cell(eng_net_row, col_idx).value, (int, float)), (
            f"Eng Net cell ({eng_net_row},{col_idx}) should be numeric in values file"
        )
        assert isinstance(ws.cell(mgmt_net_row, col_idx).value, (int, float)), (
            f"Mgmt Net cell ({mgmt_net_row},{col_idx}) should be numeric in values file"
        )


def test_values_file_total_weeks_is_numeric(values_file: Path, output_df: pd.DataFrame) -> None:
    wb = openpyxl.load_workbook(values_file, data_only=True)
    ws = wb.active
    tw_col = _total_weeks_col(ws)
    for row in ws.iter_rows(min_row=2):
        label = row[1].value  # column B
        if label not in _CAPACITY_LABELS and label is not None:
            cell_val = ws.cell(row[0].row, tw_col).value
            assert isinstance(cell_val, (int, float)), (
                f"Total Weeks for '{label}' should be numeric in values file, got {cell_val!r}"
            )


def test_values_file_weekly_allocation_is_numeric(values_file: Path) -> None:
    wb = openpyxl.load_workbook(values_file, data_only=True)
    ws = wb.active
    total_row = _find_row(ws, LABEL_TOTAL_ROW)
    for col_idx in _week_cols(ws):
        val = ws.cell(total_row, col_idx).value
        assert isinstance(val, (int, float)), (
            f"Weekly Allocation cell ({total_row},{col_idx}) should be numeric, got {val!r}"
        )


# ---------------------------------------------------------------------------
# Formula file: specific cells contain Excel formulas
# ---------------------------------------------------------------------------

def test_formulas_file_is_created(formulas_file: Path) -> None:
    assert formulas_file.exists()


def test_formulas_file_eng_net_has_subtraction_formula(formulas_file: Path) -> None:
    wb = openpyxl.load_workbook(formulas_file, data_only=False)
    ws = wb.active
    eng_net_row = _find_row(ws, LABEL_ENG_NET)
    for col_idx in _week_cols(ws):
        val = ws.cell(eng_net_row, col_idx).value
        assert isinstance(val, str) and val.startswith("="), (
            f"Eng Net cell ({eng_net_row},{col_idx}) should be a formula, got {val!r}"
        )
        assert "-" in val, f"Eng Net formula should subtract absence: {val!r}"


def test_formulas_file_mgmt_net_has_subtraction_formula(formulas_file: Path) -> None:
    wb = openpyxl.load_workbook(formulas_file, data_only=False)
    ws = wb.active
    mgmt_net_row = _find_row(ws, LABEL_MGMT_NET)
    for col_idx in _week_cols(ws):
        val = ws.cell(mgmt_net_row, col_idx).value
        assert isinstance(val, str) and val.startswith("="), (
            f"Mgmt Net cell ({mgmt_net_row},{col_idx}) should be a formula, got {val!r}"
        )
        assert "-" in val, f"Mgmt Net formula should subtract absence: {val!r}"


def test_formulas_file_total_weeks_is_sum_formula(formulas_file: Path) -> None:
    wb = openpyxl.load_workbook(formulas_file, data_only=False)
    ws = wb.active
    tw_col = _total_weeks_col(ws)
    for row in ws.iter_rows(min_row=2):
        label = row[1].value
        if label not in _CAPACITY_LABELS and label is not None:
            val = ws.cell(row[0].row, tw_col).value
            assert isinstance(val, str) and val.upper().startswith("=SUM("), (
                f"Total Weeks for '{label}' should be =SUM(...), got {val!r}"
            )


def test_formulas_file_weekly_allocation_is_sum_formula(formulas_file: Path) -> None:
    wb = openpyxl.load_workbook(formulas_file, data_only=False)
    ws = wb.active
    total_row = _find_row(ws, LABEL_TOTAL_ROW)
    for col_idx in _week_cols(ws):
        val = ws.cell(total_row, col_idx).value
        assert isinstance(val, str) and val.upper().startswith("=SUM("), (
            f"Weekly Allocation cell ({total_row},{col_idx}) should be =SUM(...), got {val!r}"
        )


def test_formulas_eng_net_references_correct_rows(formulas_file: Path) -> None:
    """Spot-check: Eng Net formula references Eng Bruto and Eng Absence rows."""
    wb = openpyxl.load_workbook(formulas_file, data_only=False)
    ws = wb.active
    r_bruto = _find_row(ws, LABEL_ENG_BRUTO)
    r_absence = _find_row(ws, LABEL_ENG_ABSENCE)
    r_net = _find_row(ws, LABEL_ENG_NET)
    week_cols = _week_cols(ws)
    # Check first week column
    col_idx = week_cols[0]
    formula = ws.cell(r_net, col_idx).value
    assert str(r_bruto) in formula, f"Formula {formula!r} should reference bruto row {r_bruto}"
    assert str(r_absence) in formula, f"Formula {formula!r} should reference absence row {r_absence}"


def test_formulas_total_weeks_spans_all_week_columns(formulas_file: Path) -> None:
    """Total Weeks SUM range must start at the first week col and end at the last."""
    wb = openpyxl.load_workbook(formulas_file, data_only=False)
    ws = wb.active
    tw_col = _total_weeks_col(ws)
    week_col_indices = _week_cols(ws)
    first_letter = get_column_letter(week_col_indices[0])
    last_letter = get_column_letter(week_col_indices[-1])
    # Check first epic row
    for row in ws.iter_rows(min_row=2):
        label = row[1].value
        if label not in _CAPACITY_LABELS and label is not None:
            r = row[0].row
            formula = ws.cell(r, tw_col).value
            assert first_letter in formula, f"SUM should start at {first_letter}: {formula!r}"
            assert last_letter in formula, f"SUM should end at {last_letter}: {formula!r}"
            break


# ---------------------------------------------------------------------------
# Parametrized tests: formula positions are correct for 1, 3, and 5 epics
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("n_epics", [1, 3, 5])
def test_weekly_allocation_sum_spans_exact_epic_rows(n_epics: int, tmp_path: Path) -> None:
    """
    The Weekly Allocation SUM formula must reference exactly the epic rows —
    from the row after the last capacity header to the row before the total row.
    This is verified for 1, 3, and 5 epics so that changes in sheet height are caught.
    """
    df = build_output_table(_make_epics(n_epics), _CAPACITY, _START, _END)
    p = tmp_path / f"out_{n_epics}.xlsx"
    write_output_with_formulas(df, p)

    wb = openpyxl.load_workbook(p, data_only=False)
    ws = wb.active

    # Identify expected epic rows from the sheet directly
    epic_rows_in_sheet = [
        row[0].row
        for row in ws.iter_rows(min_row=2)
        if row[1].value not in _CAPACITY_LABELS and row[1].value is not None
    ]
    assert len(epic_rows_in_sheet) == n_epics, (
        f"Expected {n_epics} epic rows, found {len(epic_rows_in_sheet)}"
    )

    expected_first = epic_rows_in_sheet[0]
    expected_last  = epic_rows_in_sheet[-1]
    total_row_num  = _find_row(ws, LABEL_TOTAL_ROW)

    for col_idx in _week_cols(ws):
        cl = get_column_letter(col_idx)
        formula = ws.cell(total_row_num, col_idx).value
        expected = f"=SUM({cl}{expected_first}:{cl}{expected_last})"
        assert formula == expected, (
            f"n_epics={n_epics}: Weekly Allocation formula for col {cl} "
            f"expected {expected!r}, got {formula!r}"
        )


@pytest.mark.parametrize("n_epics", [1, 3, 5])
def test_total_weeks_sum_references_own_row(n_epics: int, tmp_path: Path) -> None:
    """
    The Total Weeks formula for each epic must reference that epic's own row number
    (not a hardcoded constant), across sheet shapes with 1, 3, and 5 epics.
    """
    df = build_output_table(_make_epics(n_epics), _CAPACITY, _START, _END)
    p = tmp_path / f"out_{n_epics}.xlsx"
    write_output_with_formulas(df, p)

    wb = openpyxl.load_workbook(p, data_only=False)
    ws = wb.active

    tw_col = _total_weeks_col(ws)
    week_col_indices = _week_cols(ws)
    first_letter = get_column_letter(week_col_indices[0])
    last_letter  = get_column_letter(week_col_indices[-1])

    for row in ws.iter_rows(min_row=2):
        label = row[1].value
        if label in _CAPACITY_LABELS or label is None:
            continue
        r = row[0].row
        formula = ws.cell(r, tw_col).value
        expected = f"=SUM({first_letter}{r}:{last_letter}{r})"
        assert formula == expected, (
            f"n_epics={n_epics}, epic row {r}: "
            f"Total Weeks expected {expected!r}, got {formula!r}"
        )


@pytest.mark.parametrize("n_epics", [1, 3, 5])
def test_net_capacity_formulas_reference_fixed_header_rows(n_epics: int, tmp_path: Path) -> None:
    """
    Eng Net and Mgmt Net formulas must reference the bruto/absence rows, which
    are always at fixed positions (rows 2-7) regardless of how many epics follow.
    """
    df = build_output_table(_make_epics(n_epics), _CAPACITY, _START, _END)
    p = tmp_path / f"out_{n_epics}.xlsx"
    write_output_with_formulas(df, p)

    wb = openpyxl.load_workbook(p, data_only=False)
    ws = wb.active

    r_bruto        = _find_row(ws, LABEL_ENG_BRUTO)
    r_eng_absence  = _find_row(ws, LABEL_ENG_ABSENCE)
    r_eng_net      = _find_row(ws, LABEL_ENG_NET)
    r_mgmt_cap     = _find_row(ws, LABEL_MGMT_CAPACITY)
    r_mgmt_absence = _find_row(ws, LABEL_MGMT_ABSENCE)
    r_mgmt_net     = _find_row(ws, LABEL_MGMT_NET)

    for col_idx in _week_cols(ws):
        cl = get_column_letter(col_idx)
        eng_formula  = ws.cell(r_eng_net,  col_idx).value
        mgmt_formula = ws.cell(r_mgmt_net, col_idx).value
        assert eng_formula == f"={cl}{r_bruto}-{cl}{r_eng_absence}", (
            f"n_epics={n_epics}: Eng Net formula wrong: {eng_formula!r}"
        )
        assert mgmt_formula == f"={cl}{r_mgmt_cap}-{cl}{r_mgmt_absence}", (
            f"n_epics={n_epics}: Mgmt Net formula wrong: {mgmt_formula!r}"
        )
