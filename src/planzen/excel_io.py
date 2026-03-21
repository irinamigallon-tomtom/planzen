"""
Excel I/O for planzen.

Reads the input plan file and writes the output allocation table.
All file operations are isolated here; core_logic stays pure.
"""

from __future__ import annotations

import logging
from pathlib import Path

import openpyxl
import pandas as pd
from openpyxl.utils import get_column_letter

from planzen.config import (
    ALLOC_MODE_DEFAULT,
    COL_ALLOC_MODE,
    COL_BUDGET_BUCKET,
    COL_EPIC,
    COL_ESTIMATION,
    COL_LINK,
    COL_PRIORITY,
    TEAM_CONFIG_LABELS,
    TEAM_LABEL_ENG_ABSENCE,
    TEAM_LABEL_ENGINEERS,
    TEAM_LABEL_MGMT_ABSENCE,
    TEAM_LABEL_MANAGERS,
    LABEL_CAPACITY_ALERT_ROW,
    LABEL_ENG_ABSENCE,
    LABEL_ENG_BRUTO,
    LABEL_ENG_NET,
    LABEL_MGMT_ABSENCE,
    LABEL_MGMT_CAPACITY,
    LABEL_MGMT_NET,
    LABEL_TOTAL_ROW,
    OUT_COL_BUDGET_BUCKET,
    OUT_COL_EPIC,
    OUT_COL_ESTIMATION,
    OUT_COL_OFF_ESTIMATE,
    OUT_COL_PRIORITY,
    OUT_COL_TOTAL_WEEKS,
    VALID_ALLOC_MODES,
)

REQUIRED_INPUT_COLUMNS = {
    COL_EPIC,
    COL_ESTIMATION,
    COL_BUDGET_BUCKET,
    COL_LINK,
    COL_PRIORITY,
}

_log = logging.getLogger(__name__)

_NON_WEEK_COLS = {
    OUT_COL_BUDGET_BUCKET, OUT_COL_EPIC, OUT_COL_PRIORITY,
    OUT_COL_ESTIMATION, OUT_COL_TOTAL_WEEKS, OUT_COL_OFF_ESTIMATE,
}

_CAPACITY_LABELS = {
    LABEL_ENG_BRUTO, LABEL_ENG_ABSENCE, LABEL_ENG_NET,
    LABEL_MGMT_CAPACITY, LABEL_MGMT_ABSENCE, LABEL_MGMT_NET,
    LABEL_TOTAL_ROW, LABEL_CAPACITY_ALERT_ROW,
}


def _normalize_config_label(s: object) -> str:
    """Normalise a config row label for fuzzy matching.

    Applies in order:
    1. Strip whitespace and lowercase.
    2. Remove parenthetical suffixes, e.g. ``(days)``.
    3. Singularize common plural words (trailing *s* on words longer than 3
       characters) so ``"Engineers"`` and ``"Engineer"`` both match.
    """
    if not isinstance(s, str):
        return ""
    import re
    s = s.strip().lower()
    s = re.sub(r"\s*\(.*?\)", "", s).strip()
    s = " ".join(
        w[:-1] if w.endswith("s") and len(w) > 3 else w
        for w in s.split()
    )
    return s


# Mapping: normalised canonical label → canonical label string
_TEAM_CONFIG_LABELS_NORM: dict[str, str] = {
    _normalize_config_label(label): label
    for label in TEAM_CONFIG_LABELS
}

_KNOWN_COLUMNS: set[str] = {
    COL_EPIC, COL_ESTIMATION, COL_BUDGET_BUCKET, COL_LINK,
    COL_PRIORITY, COL_ALLOC_MODE,
}
_KNOWN_COLUMNS_LOWER: dict[str, str] = {c.lower(): c for c in _KNOWN_COLUMNS}


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename DataFrame columns to their canonical form (case-insensitive, stripped)."""
    rename = {
        col: _KNOWN_COLUMNS_LOWER[col.strip().lower()]
        for col in df.columns
        if isinstance(col, str) and col.strip().lower() in _KNOWN_COLUMNS_LOWER
        and col != _KNOWN_COLUMNS_LOWER[col.strip().lower()]
    }
    if rename:
        _log.info("Normalising column names: %s", rename)
    return df.rename(columns=rename)


def formulas_path(path: Path) -> Path:
    """Return the sibling path for the formulas variant of an output file."""
    return path.with_stem(path.stem + "_formulas")


def _config_label_series(df: pd.DataFrame) -> pd.Series:
    """Return a Series of normalised config labels for each row.

    Config rows are identified exclusively by their ``Budget Bucket`` value.
    ``Epic Description`` is not used for config row detection.
    """
    if COL_BUDGET_BUCKET in df.columns:
        label_vals = df[COL_BUDGET_BUCKET].fillna("").astype(str).str.strip()
    else:
        label_vals = pd.Series("", index=df.index)
    return label_vals.apply(_normalize_config_label)


def validate_input_file(path: Path) -> list[str]:
    """
    Validate the input Excel file and return a list of human-readable error
    messages.  An empty list means the file is valid.

    All issues are collected before returning so the user sees everything at
    once rather than fixing one problem at a time.
    """
    errors: list[str] = []

    # --- file-level ---
    if not path.exists():
        errors.append(
            f"File not found: '{path}'\n"
            "  → Check the path and make sure the file exists."
        )
        return errors  # nothing else can be checked

    try:
        df = pd.read_excel(path)
        df = _normalize_columns(df)
    except Exception as exc:
        errors.append(
            f"Cannot read '{path}' as an Excel file: {exc}\n"
            "  → Make sure the file is a valid .xlsx workbook and is not open in Excel."
        )
        return errors

    # --- required structural columns ---
    for col in (COL_EPIC, COL_ESTIMATION):
        if col not in df.columns:
            errors.append(
                f"Missing required column: \"{col}\"\n"
                f"  → Add a column with this exact header name."
            )

    if errors:
        return errors  # can't proceed without these two columns

    # --- team config rows (normalised matching) ---
    epic_norm = _config_label_series(df)
    config_mask = epic_norm.isin(_TEAM_CONFIG_LABELS_NORM)
    config_rows = df[config_mask].copy()
    config_rows[COL_EPIC] = epic_norm[config_mask].map(_TEAM_CONFIG_LABELS_NORM)
    config_df = config_rows.set_index(COL_EPIC)[COL_ESTIMATION]

    for label, hint in [
        (
            TEAM_LABEL_ENGINEERS,
            f'Add a row where "{COL_BUDGET_BUCKET}" = "{TEAM_LABEL_ENGINEERS}" '
            'and "Estimation" = the number of full-time engineers (e.g. 5).',
        ),
        (
            TEAM_LABEL_MANAGERS,
            f'Add a row where "{COL_BUDGET_BUCKET}" = "{TEAM_LABEL_MANAGERS}" '
            'and "Estimation" = the number of line managers (e.g. 2).',
        ),
    ]:
        if label not in config_df.index:
            errors.append(f'Missing required config row: "{label}"\n  → {hint}')
        else:
            val = config_df[label]
            try:
                fval = float(val)
                if fval <= 0:
                    errors.append(
                        f'"{label}" must be greater than 0 (got {val!r}).\n'
                        "  → Enter the number of FTE team members, e.g. 5."
                    )
            except (TypeError, ValueError):
                errors.append(
                    f'"{label}" must be a number (got {val!r}).\n'
                    "  → Enter the number of FTE team members, e.g. 5."
                )

    for label in (TEAM_LABEL_ENG_ABSENCE, TEAM_LABEL_MGMT_ABSENCE):
        if label in config_df.index and pd.notna(config_df[label]):
            val = config_df[label]
            try:
                fval = float(val)
                if fval < 0:
                    errors.append(
                        f'"{label}" cannot be negative (got {val!r}).\n'
                        "  → Enter the total absence days for the quarter, e.g. 10."
                        " Use 0 if none, or omit the row to use the default."
                    )
            except (TypeError, ValueError):
                errors.append(
                    f'"{label}" must be a number (got {val!r}).\n'
                    "  → Enter the total absence days for the quarter, e.g. 10."
                )

    # --- epic rows --- (apply same filtering as read_input)
    epics_df = df[~config_mask].reset_index(drop=True)
    epics_df = epics_df.dropna(how="all").reset_index(drop=True)
    epics_df = epics_df[epics_df[COL_EPIC].notna()].reset_index(drop=True)

    missing_cols = (REQUIRED_INPUT_COLUMNS - {COL_EPIC, COL_ESTIMATION}) - set(epics_df.columns)
    if missing_cols:
        for col in sorted(missing_cols):
            errors.append(
                f'Missing required epic column: "{col}"\n'
                "  → Add a column with this exact header name."
            )

    if len(epics_df) == 0:
        errors.append(
            "No epic rows found after the config rows.\n"
            "  → Add at least one epic row below the team config rows."
        )
        return errors

    # --- per-row epic data ---
    if COL_ESTIMATION in epics_df.columns:
        for i, row in epics_df.iterrows():
            val = row[COL_ESTIMATION]
            name = row.get(COL_EPIC, f"row {i + 1}")
            if pd.isna(val):
                pass  # empty Estimation defaults to 0 at read time
            else:
                try:
                    fval = float(val)
                    if fval < 0:
                        errors.append(
                            f'Epic "{name}": "Estimation" cannot be negative (got {val!r}).\n'
                            "  → Enter the total effort in Person-Weeks, e.g. 4.5."
                        )
                except (TypeError, ValueError):
                    errors.append(
                        f'Epic "{name}": "Estimation" must be a number (got {val!r}).\n'
                        "  → Enter the total effort in Person-Weeks, e.g. 4.5."
                    )

    if COL_PRIORITY in epics_df.columns:
        for i, row in epics_df.iterrows():
            val = row[COL_PRIORITY]
            name = row.get(COL_EPIC, f"row {i + 1}")
            if pd.isna(val):
                errors.append(
                    f'Epic "{name}": "Priority" is empty.\n'
                    "  → Enter a numeric priority (e.g. 1 = highest). "
                    "Lower numbers are scheduled first."
                )
            else:
                try:
                    float(val)
                except (TypeError, ValueError):
                    errors.append(
                        f'Epic "{name}": "Priority" must be a number (got {val!r}).\n'
                        "  → Enter a numeric priority, e.g. 1."
                    )

    if COL_ALLOC_MODE in epics_df.columns:
        for i, row in epics_df.iterrows():
            val = row[COL_ALLOC_MODE]
            if pd.notna(val) and str(val).strip() and str(val).strip() not in VALID_ALLOC_MODES:
                name = row.get(COL_EPIC, f"row {i + 1}")
                errors.append(
                    f'Epic "{name}": invalid "Allocation Mode": {val!r}.\n'
                    f'  → Valid values: {", ".join(sorted(VALID_ALLOC_MODES))}'
                    f" (or leave blank to use the default: {ALLOC_MODE_DEFAULT})."
                )

    return errors


def read_input(path: Path) -> tuple[
    pd.DataFrame,   # epics
    float,          # num_engineers
    float,          # num_managers
    float | None,   # eng_absence_days (total for quarter, or None → use default)
    float | None,   # mgmt_absence_days (total for quarter, or None → use default)
]:
    """
    Read the input Excel file and return epics plus team capacity config.

    The sheet must begin with team config rows in columns A/B before the epic
    data.  Recognised config labels (in the ``Epic Description`` column):

    - ``Engineer Bruto Capacity``  *(required)*
    - ``Manager Bruto Capacity`` *(required)*
    - ``Engineer Absence (days)``  *(optional — total days for the quarter)*
    - ``Manager Absence (days)``   *(optional — total days for the quarter)*

    Config rows are stripped before the epic DataFrame is returned.  The epic
    rows must contain all required columns; column order and extra columns are
    preserved.

    Raises
    ------
    ValueError
        If required config rows or epic columns are missing.
    """
    df = pd.read_excel(path)
    df = _normalize_columns(df)

    if COL_EPIC not in df.columns or COL_ESTIMATION not in df.columns:
        raise ValueError(
            f"Input file must have '{COL_EPIC}' and '{COL_ESTIMATION}' columns."
        )

    # --- extract team config rows (normalised matching) ---
    epic_norm = _config_label_series(df)
    config_mask = epic_norm.isin(_TEAM_CONFIG_LABELS_NORM)
    config_rows = df[config_mask].copy()
    config_rows[COL_EPIC] = epic_norm[config_mask].map(_TEAM_CONFIG_LABELS_NORM)
    config_df = config_rows.set_index(COL_EPIC)[COL_ESTIMATION]

    if TEAM_LABEL_ENGINEERS not in config_df.index:
        raise ValueError(
            f"Input file missing required config row: '{TEAM_LABEL_ENGINEERS}'"
        )
    if TEAM_LABEL_MANAGERS not in config_df.index:
        raise ValueError(
            f"Input file missing required config row: '{TEAM_LABEL_MANAGERS}'"
        )

    num_engineers: float = float(config_df[TEAM_LABEL_ENGINEERS])
    num_managers: float  = float(config_df[TEAM_LABEL_MANAGERS])
    eng_absence_days: float | None = (
        float(config_df[TEAM_LABEL_ENG_ABSENCE])
        if TEAM_LABEL_ENG_ABSENCE in config_df.index
        and pd.notna(config_df[TEAM_LABEL_ENG_ABSENCE])
        else None
    )
    mgmt_absence_days: float | None = (
        float(config_df[TEAM_LABEL_MGMT_ABSENCE])
        if TEAM_LABEL_MGMT_ABSENCE in config_df.index
        and pd.notna(config_df[TEAM_LABEL_MGMT_ABSENCE])
        else None
    )

    # --- epic rows (everything that isn't a config row) ---
    epics_df = df[~config_mask].reset_index(drop=True)

    # Drop fully-empty rows silently.
    epics_df = epics_df.dropna(how="all").reset_index(drop=True)

    # Rows with no Epic Description are unusable — log each one and discard.
    no_description = epics_df[COL_EPIC].isna()
    for idx in epics_df[no_description].index:
        _log.warning("Discarding row %d: no '%s' value.", idx + 1, COL_EPIC)
    epics_df = epics_df[~no_description].reset_index(drop=True)

    # Rows with no Estimation default to 0 — log each one and continue.
    no_estimation = epics_df[COL_ESTIMATION].isna()
    for _, row in epics_df[no_estimation].iterrows():
        _log.warning(
            "Epic \"%s\": 'Estimation' is empty — defaulting to 0.", row[COL_EPIC]
        )
    epics_df[COL_ESTIMATION] = epics_df[COL_ESTIMATION].fillna(0.0)

    missing = REQUIRED_INPUT_COLUMNS - set(epics_df.columns)
    if missing:
        raise ValueError(
            f"Input file is missing required columns: {sorted(missing)}"
        )

    return epics_df, num_engineers, num_managers, eng_absence_days, mgmt_absence_days


def write_output(df: pd.DataFrame, path: Path) -> None:
    """Write the output allocation table to an Excel file (values only)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Allocation")


def write_output_with_formulas(df: pd.DataFrame, path: Path) -> None:
    """
    Write the output allocation table to an Excel file with formulas for
    calculated fields:

    - Engineer Net Capacity row: ``=<bruto_cell>-<absence_cell>`` per week
    - Management Net Capacity row: same pattern
    - Total Weeks column (epic rows): ``=SUM(<first_week>:<last_week>)``
    - Weekly Allocation row: ``=SUM(<first_epic>:<last_epic>)`` per week
    """
    # Write values first, then reopen to replace calculated cells with formulas.
    write_output(df, path)
    wb = openpyxl.load_workbook(path)
    ws = wb.active

    col_names = list(df.columns)
    week_col_indices = [
        col_names.index(c) + 1
        for c in col_names if c not in _NON_WEEK_COLS
    ]
    total_weeks_col_idx = col_names.index(OUT_COL_TOTAL_WEEKS) + 1

    # Excel row = DataFrame index + 2  (0-indexed df + 1 for header + 1 for 1-based)
    labels = list(df[OUT_COL_EPIC])

    def excel_row(label: str) -> int:
        return labels.index(label) + 2

    r_eng_bruto   = excel_row(LABEL_ENG_BRUTO)
    r_eng_absence = excel_row(LABEL_ENG_ABSENCE)
    r_eng_net     = excel_row(LABEL_ENG_NET)
    r_mgmt_cap    = excel_row(LABEL_MGMT_CAPACITY)
    r_mgmt_absence = excel_row(LABEL_MGMT_ABSENCE)
    r_mgmt_net    = excel_row(LABEL_MGMT_NET)
    r_total       = excel_row(LABEL_TOTAL_ROW)

    epic_excel_rows = [
        i + 2 for i, lbl in enumerate(labels) if lbl not in _CAPACITY_LABELS
    ]
    first_week_letter = get_column_letter(week_col_indices[0])
    last_week_letter  = get_column_letter(week_col_indices[-1])
    first_epic_row = epic_excel_rows[0]
    last_epic_row  = epic_excel_rows[-1]

    # Engineer Net Capacity: =<bruto> - <absence>
    for ci in week_col_indices:
        cl = get_column_letter(ci)
        ws.cell(r_eng_net, ci).value = f"={cl}{r_eng_bruto}-{cl}{r_eng_absence}"

    # Management Net Capacity: =<mgmt_cap> - <mgmt_absence>
    for ci in week_col_indices:
        cl = get_column_letter(ci)
        ws.cell(r_mgmt_net, ci).value = f"={cl}{r_mgmt_cap}-{cl}{r_mgmt_absence}"

    # Total Weeks for each epic: =SUM(<first_week_col><row>:<last_week_col><row>)
    for er in epic_excel_rows:
        ws.cell(er, total_weeks_col_idx).value = (
            f"=SUM({first_week_letter}{er}:{last_week_letter}{er})"
        )

    # Weekly Allocation row: =SUM(<col><first_epic>:<col><last_epic>)
    for ci in week_col_indices:
        cl = get_column_letter(ci)
        ws.cell(r_total, ci).value = (
            f"=SUM({cl}{first_epic_row}:{cl}{last_epic_row})"
        )

    # Total row Estimation and Total Weeks: sum over all epic rows
    estimation_col_idx = col_names.index(OUT_COL_ESTIMATION) + 1
    estimation_col_letter = get_column_letter(estimation_col_idx)
    total_weeks_col_letter = get_column_letter(total_weeks_col_idx)
    ws.cell(r_total, estimation_col_idx).value = (
        f"=SUM({estimation_col_letter}{first_epic_row}:{estimation_col_letter}{last_epic_row})"
    )
    ws.cell(r_total, total_weeks_col_idx).value = (
        f"=SUM({total_weeks_col_letter}{first_epic_row}:{total_weeks_col_letter}{last_epic_row})"
    )

    # Off Estimate column (epic rows only): =ABS(<total_weeks_cell>-<estimation_cell>)>0.05
    off_estimate_col_idx = col_names.index(OUT_COL_OFF_ESTIMATE) + 1
    for er in epic_excel_rows:
        ws.cell(er, off_estimate_col_idx).value = (
            f"=ABS({total_weeks_col_letter}{er}-{estimation_col_letter}{er})>0.05"
        )

    # Off Capacity row (week columns): =ABS(<weekly_alloc_cell>-<eng_net_cell>)>0.1
    r_capacity_alert = excel_row(LABEL_CAPACITY_ALERT_ROW)
    for ci in week_col_indices:
        cl = get_column_letter(ci)
        ws.cell(r_capacity_alert, ci).value = (
            f"=ABS({cl}{r_total}-{cl}{r_eng_net})>0.1"
        )

    wb.save(path)
