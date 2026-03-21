"""
CLI entrypoint for planzen.

Usage:
    uv run planzen INPUT_FILE OUTPUT_FILE -q QUARTER [OPTIONS]
"""

from __future__ import annotations

from pathlib import Path

import typer

from planzen.core_logic import CapacityConfig, build_output_table, get_quarter_dates
from planzen.excel_io import formulas_path, read_plan, write_output, write_output_with_formulas

app = typer.Typer(help="planzen — weekly capacity allocation tool.")


@app.command()
def run(
    input_file: Path = typer.Argument(..., help="Path to the input Excel plan file."),
    output_file: Path = typer.Argument(..., help="Path for the output Excel file."),
    quarter: int = typer.Option(..., "-q", "--quarter", help="Fiscal quarter (1–4)."),
    num_engineers: float = typer.Option(..., help="Number of engineers (supports fractions, e.g. 2.5)."),
    num_managers: float = typer.Option(..., help="Number of line managers (supports fractions, e.g. 0.5)."),
) -> None:
    """Process an input plan and write the allocation table to OUTPUT_FILE."""
    try:
        start_date, end_date = get_quarter_dates(quarter)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="'-q'") from exc

    epics_df = read_plan(input_file)
    capacity = CapacityConfig(
        num_engineers=num_engineers,
        num_managers=num_managers,
    )
    output_df = build_output_table(epics_df, capacity, start_date, end_date)
    write_output(output_df, output_file)
    formulas_file = formulas_path(output_file)
    write_output_with_formulas(output_df, formulas_file)
    typer.echo(f"Values output written to  {output_file}")
    typer.echo(f"Formulas output written to {formulas_file}")


def main() -> None:
    app()
