import importlib.metadata
from typing import Optional

import typer

from calpdf import dlcover, optimize, replace, toc
from calpdf.output import configure

app = typer.Typer(
    name="calpdf",
    help="A simple PDF toolkit to manage your Calibre library.",
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
        try:
            pkg_version = importlib.metadata.version("calpdf")
        except importlib.metadata.PackageNotFoundError:
            pkg_version = "unknown"
        typer.echo(f"calpdf {pkg_version}")
        raise typer.Exit()


# ---------------------------------------------------------------------------
# Command registration
#
# cli.py is the only place commands are attached to the app. Command modules
# merely define functions, so importing them has no side effects, and the
# entire command surface is visible at a glance. Command help text comes from
# each function's docstring.
# ---------------------------------------------------------------------------

app.command("dl-cover")(dlcover.main)
app.command("optimize")(optimize.main)
app.command("replace-cover")(replace.main)
app.command("set-cover")(replace.set_cover)
app.command("export-toc")(toc.export_toc)
app.command("apply-toc")(toc.apply_toc)
