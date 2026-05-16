"""Centralized user-facing output.

Every command should use these helpers instead of calling ``typer.echo``
directly.  This keeps styling, verbosity, and color control in one place.
"""

from __future__ import annotations

import sys
from typing import Optional

from rich.console import Console
from rich.theme import Theme
from rich.tree import Tree

_theme = Theme(
    {
        "info": "default",
        "detail": "dim",
        "success": "bold green",
        "warning": "bold yellow",
        "error": "bold red",
    }
)

_out = Console(theme=_theme, highlight=False)
_err = Console(theme=_theme, highlight=False, stderr=True)

_quiet: bool = False


# ---------------------------------------------------------------------------
# Global configuration; called once from the CLI callback
# ---------------------------------------------------------------------------


def configure(*, quiet: bool = False, no_color: bool = False) -> None:
    """Apply global output settings.

    Must be called before any output helpers are used (typically from the
    top-level typer callback).
    """
    global _quiet, _out, _err

    _quiet = quiet

    if no_color:
        _out = Console(theme=_theme, highlight=False, no_color=True)
        _err = Console(theme=_theme, highlight=False, stderr=True, no_color=True)


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------


def info(text: str) -> None:
    """Neutral informational message (suppressed by --quiet)."""
    if not _quiet:
        _out.print(text, style="info")


def detail(text: str) -> None:
    """Secondary/progress detail (suppressed by --quiet)."""
    if not _quiet:
        _out.print(text, style="detail")


def success(text: str) -> None:
    """Success message (suppressed by --quiet)."""
    if not _quiet:
        _out.print(text, style="success")


def warning(text: str) -> None:
    """Warning: always shown, goes to stderr."""
    _err.print(f"Warning: {text}", style="warning")


def error(text: str) -> None:
    """Error: always shown, goes to stderr."""
    _err.print(f"Error: {text}", style="error")


# ---------------------------------------------------------------------------
# Structured output; intended for data that may be piped
# ---------------------------------------------------------------------------


def raw(text: str) -> None:
    """Raw unformatted output to stdout (never suppressed, never styled).

    Use for machine-readable data like JSON that may be piped.
    """
    sys.stdout.write(text)
    if not text.endswith("\n"):
        sys.stdout.write("\n")
    sys.stdout.flush()


# ---------------------------------------------------------------------------
# Tree rendering for ToC
# ---------------------------------------------------------------------------


def _build_tree_nodes(
    tree: Tree,
    entries: list[dict],
) -> None:
    for entry in entries:
        title = entry.get("title", "")
        page = entry.get("pageNumber")
        label = f"{title}  [dim](p. {page})[/dim]" if page else title
        branch = tree.add(label)
        children = entry.get("children", [])
        if children:
            _build_tree_nodes(branch, children)


def render_toc_tree(
    entries: list[dict],
    root_label: str = "Table of Contents",
) -> None:
    """Render a ToC structure as a Rich tree to stdout."""
    if not entries:
        info("(no bookmarks)")
        return

    tree = Tree(f"[bold]{root_label}[/bold]")
    _build_tree_nodes(tree, entries)
    _out.print(tree)
