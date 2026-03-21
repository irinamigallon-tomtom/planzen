"""
CLI entrypoint for planzen.

Usage:
    uv run planzen INPUT_FILE -q QUARTER [-o OUTPUT_DIR]

Two output files are always created in OUTPUT_DIR (default: ./output/):
  {input_stem}_YYYYMMddhhmm.xlsx           — values only
  {input_stem}_YYYYMMddhhmm_formulas.xlsx  — calculated cells as formulas
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import typer

from planzen.config import WORKING_DAYS_PER_WEEK
from planzen.core_logic import CapacityConfig, build_output_table, get_quarter_dates, _mondays_in_range
from planzen.excel_io import read_input, write_output, write_output_with_formulas

app = typer.Typer(help="planzen — weekly capacity allocation tool.")


@app.command()
def run(
    input_file: Path = typer.Argument(..., help="Path to the input Excel plan file."),
    quarter: int = typer.Option(..., "-q", "--quarter", help="Fiscal quarter (1–4)."),
    output_dir: Path = typer.Option(
        Path("output"),
        "-o", "--output-dir",
        help="Directory for output files (created if missing). Defaults to ./output/.",
    ),
) -> None:
    """Process an input plan and write two allocation tables to OUTPUT_DIR."""
    try:
        start_date, end_date = get_quarter_dates(quarter)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="'-q'") from exc

    epics_df, num_engineers, num_managers, eng_absence_days, mgmt_absence_days = (
        read_input(input_file)
    )

    n_weeks = len(_mondays_in_range(start_date, end_date))

    def _days_to_pw_per_week(days: float | None) -> float | None:
        if days is None:
            return None
        return days / WORKING_DAYS_PER_WEEK / n_weeks

    capacity = CapacityConfig(
        num_engineers=num_engineers,
        num_managers=num_managers,
        eng_absence_per_week=_days_to_pw_per_week(eng_absence_days),
        mgmt_absence_per_week=_days_to_pw_per_week(mgmt_absence_days),
    )

    output_df = build_output_table(epics_df, capacity, start_date, end_date)

    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d%H%M")
    stem = f"{input_file.stem}_{timestamp}"
    values_path = output_dir / f"{stem}.xlsx"
    formulas_file = output_dir / f"{stem}_formulas.xlsx"

    write_output(output_df, values_path)
    write_output_with_formulas(output_df, formulas_file)
    typer.echo(f"Values output written to   {values_path}")
    typer.echo(f"Formulas output written to {formulas_file}")


def main() -> None:
    app()
