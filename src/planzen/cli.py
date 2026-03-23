"""
CLI entrypoint for planzen.

Usage:
    uv run planzen INPUT_FILE -q QUARTER [-o OUTPUT_DIR]

Two output files are always created in OUTPUT_DIR (default: ./output/):
  output_{input_stem}_YYYYMMddhhmm_formulas.xlsx  — calculated cells as formulas
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import typer

from planzen.config import COL_ESTIMATION
from planzen.core_logic import build_output_table, get_quarter_dates, _mondays_in_range
from planzen.excel_io import read_input, validate_input_file, write_output_with_formulas

app = typer.Typer(help="planzen — weekly capacity allocation tool.")
logging.basicConfig(level=logging.WARNING, format="⚠  %(message)s")


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

    errors = validate_input_file(input_file, quarter)
    if errors:
        typer.echo(
            typer.style(f"\n✗  '{input_file}' has {len(errors)} problem(s):\n", fg=typer.colors.RED, bold=True)
        )
        for i, msg in enumerate(errors, 1):
            typer.echo(typer.style(f"  {i}. ", fg=typer.colors.RED) + msg)
        typer.echo()
        raise typer.Exit(code=1)

    epics_df, capacity = read_input(input_file, quarter)

    primary_mondays = _mondays_in_range(start_date, end_date)
    n_primary_weeks = len(primary_mondays)

    total_estimation = round(float(epics_df[COL_ESTIMATION].sum()), 1)
    quarter_net_capacity = round(sum(capacity.eng_net_for(m) for m in primary_mondays), 1)

    if total_estimation > quarter_net_capacity + 1e-9:
        overflow_q = (quarter % 4) + 1
        typer.echo(
            f"ℹ  Total estimation ({total_estimation} PW) exceeds Q{quarter} net capacity "
            f"({quarter_net_capacity} PW). Extending allocation into Q{overflow_q}."
        )

    output_df = build_output_table(epics_df, capacity, start_date, end_date)

    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d%H%M")
    formulas_file = output_dir / f"output_{input_file.stem}_{timestamp}_formulas.xlsx"

    write_output_with_formulas(output_df, formulas_file, len(primary_mondays))
    typer.echo(f"Formulas output written to {formulas_file}")


def main() -> None:
    app()
