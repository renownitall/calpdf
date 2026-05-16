from typing import Optional

import typer

from calpdf import __version__
from calpdf.output import configure

app = typer.Typer(
    name="calpdf",
    help="Personal PDF toolkit for Calibre library management.",
    no_args_is_help=True,
)


@app.callback(invoke_without_command=True)
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        is_eager=True,
        help="Show version and exit.",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        is_eager=True,
        help="Suppress all output except errors and warnings.",
    ),
    no_color: bool = typer.Option(
        False,
        "--no-color",
        is_eager=True,
        help="Disable colored output.",
    ),
) -> None:
    configure(quiet=quiet, no_color=no_color)

    if version:
        typer.echo(f"calpdf {__version__}")
        raise typer.Exit()


# Each module registers its subcommand(s) on import.
from calpdf import dlcover, optimize, replace, toc  # noqa: E402, F401
