import importlib.metadata
from typing import Optional

import typer

from calpdf import dlcover, extract, info, optimize, replace, toc
from calpdf.output import configure

# Help text shared by every command that reads or writes a ToC JSON file.
TOC_JSON_FORMAT = """\
The JSON file is a list of entries, and each entry has three fields:

- 'title': the bookmark text, a non-empty string.
- 'pageNumber': the physical page the bookmark points to, counting from 1.
- 'children': a list of nested entries. An empty list means no children.

'pageNumber' must be between 1 and the total number of pages. Page numbers are
1-indexed physical page positions, so page 1 is the first page of the file,
not the number printed on the page."""

# Backup behavior shared by every command that can modify a PDF in place.
BACKUP_BEHAVIOR = """\
Commands that modify a PDF in place keep the original file. This applies to
'replace-cover', 'set-cover', 'apply-toc', and 'optimize' without the
'--output' option. calpdf copies the original to a file with the same name
and a '.bak' suffix, such as 'book.pdf.bak'. If a '.bak' file already exists,
calpdf uses it as the source and does not overwrite it. To restore the
original, copy the '.bak' file back over the PDF."""

app = typer.Typer(
    name="calpdf",
    help="A simple PDF toolkit to run alongside Calibre.",
    no_args_is_help=True,
    epilog=BACKUP_BEHAVIOR,
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


# Commands are registered here. Modules have no import side effects.

app.command("dl-cover")(dlcover.main)
app.command("optimize")(optimize.main)
app.command("replace-cover")(replace.main)
app.command("set-cover")(replace.set_cover)
app.command("extract-cover")(extract.main)
app.command("info")(info.main)
app.command("export-toc", epilog=TOC_JSON_FORMAT)(toc.export_toc)
app.command("apply-toc", epilog=TOC_JSON_FORMAT)(toc.apply_toc)
