import json
import tempfile
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import pikepdf
import typer

from calpdf.cli import app
from calpdf.common import (
    AppError,
    ensure_backup,
    message,
    normalize_paths,
    same_path,
    validate_input_file,
    validate_output_dir,
)
from calpdf import output


class TocFormat(str, Enum):
    json = "json"
    tree = "tree"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_page_map(pdf: pikepdf.Pdf) -> dict[tuple[int, int], int]:
    return {page.obj.objgen: i for i, page in enumerate(pdf.pages)}


def _page_number_from_array(
    dest: pikepdf.Array, page_map: dict[tuple[int, int], int]
) -> Optional[int]:
    if len(dest) == 0:
        return None
    try:
        idx = page_map.get(dest[0].objgen)
        return idx + 1 if idx is not None else None
    except AttributeError:
        return None


def _lookup_named_dest(node, name: str) -> Optional[pikepdf.Object]:
    if not isinstance(node, pikepdf.Dictionary):
        return None

    if "/Names" in node:
        names = node["/Names"]
        for i in range(0, len(names), 2):
            key_str = str(names[i]).lstrip("/")
            if key_str == name.lstrip("/"):
                return names[i + 1]

    if "/Kids" in node:
        for kid in node["/Kids"]:
            result = _lookup_named_dest(kid, name)
            if result is not None:
                return result

    return None


def _resolve_dest_value(dest, page_map: dict[tuple[int, int], int]) -> Optional[int]:
    if isinstance(dest, pikepdf.Array):
        return _page_number_from_array(dest, page_map)

    if isinstance(dest, pikepdf.Dictionary) and "/D" in dest:
        inner = dest["/D"]
        if isinstance(inner, pikepdf.Array):
            return _page_number_from_array(inner, page_map)

    return None


def _resolve_named_destination(
    name: str, pdf: pikepdf.Pdf, page_map: dict[tuple[int, int], int]
) -> Optional[int]:
    root = pdf.Root

    if "/Names" in root and "/Dests" in root["/Names"]:
        found = _lookup_named_dest(root["/Names"]["/Dests"], name)
        if found is not None:
            result = _resolve_dest_value(found, page_map)
            if result is not None:
                return result

    if "/Dests" in root and isinstance(root["/Dests"], pikepdf.Dictionary):
        dests = root["/Dests"]
        for key in dests.keys():
            if str(key).lstrip("/") == name:
                result = _resolve_dest_value(dests[key], page_map)
                if result is not None:
                    return result

    return None


def resolve_page_number(
    item, pdf: pikepdf.Pdf, page_map: dict[tuple[int, int], int]
) -> Optional[int]:
    dest = item.destination
    if dest is not None:
        if isinstance(dest, pikepdf.Array):
            result = _page_number_from_array(dest, page_map)
            if result is not None:
                return result

        name = str(dest).lstrip("/")
        if name:
            return _resolve_named_destination(name, pdf, page_map)

    raw = getattr(item, "obj", None)
    if not isinstance(raw, pikepdf.Dictionary):
        return None

    action = raw.get("/A")
    if not isinstance(action, pikepdf.Dictionary):
        return None

    if str(action.get("/S", "")) != "/GoTo":
        return None

    action_dest = action.get("/D")
    if action_dest is None:
        return None

    if isinstance(action_dest, pikepdf.Array):
        result = _page_number_from_array(action_dest, page_map)
        if result is not None:
            return result

    name = str(action_dest).lstrip("/")
    if name:
        return _resolve_named_destination(name, pdf, page_map)

    return None


def extract_outline(
    items, pdf: pikepdf.Pdf, page_map: dict[tuple[int, int], int]
) -> list[dict[str, Any]]:
    result = []
    for item in items:
        page_num = resolve_page_number(item, pdf, page_map)
        entry = {
            "title": item.title,
            "pageNumber": page_num,
            "children": extract_outline(item.children, pdf, page_map),
        }
        result.append(entry)
    return result


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_toc(data: Any, total_pages: int, path: str = "root") -> list[str]:
    errors: list[str] = []

    if not isinstance(data, list):
        errors.append(f"{path}: expected a list, got {type(data).__name__}")
        return errors

    for i, entry in enumerate(data):
        prefix = f"{path}[{i}]"

        if not isinstance(entry, dict):
            errors.append(f"{prefix}: expected an object, got {type(entry).__name__}")
            continue

        if "title" not in entry:
            errors.append(f"{prefix}: missing 'title'")
        elif not isinstance(entry["title"], str):
            errors.append(
                f"{prefix}.title: expected a string, "
                f"got {type(entry['title']).__name__}"
            )
        elif not entry["title"].strip():
            errors.append(f"{prefix}.title: must not be empty")

        if "pageNumber" not in entry:
            errors.append(f"{prefix}: missing 'pageNumber'")
        elif not isinstance(entry["pageNumber"], int):
            errors.append(
                f"{prefix}.pageNumber: expected an integer, "
                f"got {type(entry['pageNumber']).__name__}"
            )
        elif entry["pageNumber"] < 1:
            errors.append(
                f"{prefix}.pageNumber: must be >= 1, got {entry['pageNumber']}"
            )
        elif entry["pageNumber"] > total_pages:
            errors.append(
                f"{prefix}.pageNumber: {entry['pageNumber']} exceeds "
                f"total pages ({total_pages})"
            )

        if "children" not in entry:
            errors.append(f"{prefix}: missing 'children'")
        elif not isinstance(entry["children"], list):
            errors.append(
                f"{prefix}.children: expected a list, "
                f"got {type(entry['children']).__name__}"
            )
        else:
            errors.extend(
                validate_toc(entry["children"], total_pages, f"{prefix}.children")
            )

    return errors


# ---------------------------------------------------------------------------
# Apply
# ---------------------------------------------------------------------------


def build_outline_items(
    pdf: pikepdf.Pdf, entries: list[dict[str, Any]]
) -> list[pikepdf.OutlineItem]:
    items = []
    for entry in entries:
        page_idx = entry["pageNumber"] - 1
        page = pdf.pages[page_idx]
        dest = pikepdf.Array([page.obj, pikepdf.Name("/Fit")])
        item = pikepdf.OutlineItem(entry["title"], dest)
        for child in build_outline_items(pdf, entry.get("children", [])):
            item.children.append(child)
        items.append(item)
    return items


# ---------------------------------------------------------------------------
# CLI commands
# ---------------------------------------------------------------------------


@app.command("export-toc")
def export_toc(
    input_pdf: Path = typer.Argument(..., help="Path to the input PDF file"),
    output_file: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output JSON file (default: stdout)",
    ),
    fmt: TocFormat = typer.Option(
        TocFormat.json,
        "--format",
        "-f",
        help="Output format: 'json' (default, machine-readable) or 'tree' (human-readable).",
    ),
) -> None:
    """Export the PDF's table of contents (bookmarks) to JSON or a tree view.

    Page numbers are 1-indexed physical page positions.
    """
    try:
        validate_input_file(input_pdf, label="Input PDF")

        with pikepdf.open(input_pdf) as pdf:
            page_map = _build_page_map(pdf)

            with pdf.open_outline() as outline:
                toc = extract_outline(outline.root, pdf, page_map)

        if fmt == TocFormat.tree:
            if output_file:
                output.warning(
                    "--output is ignored with --format tree (tree is always "
                    "printed to the terminal)."
                )
            output.render_toc_tree(toc, root_label=input_pdf.name)
        else:
            json_str = json.dumps(toc, indent=2, ensure_ascii=False)
            if output_file:
                validate_output_dir(output_file)
                output_file.write_text(json_str, encoding="utf-8")
                output.info(
                    f"Exported {len(toc)} top-level entries to '{output_file}'."
                )
            else:
                output.raw(json_str)

    except typer.Exit:
        raise
    except AppError as exc:
        output.error(str(exc))
        raise typer.Exit(1)
    except Exception as exc:
        output.error(message(exc))
        raise typer.Exit(1)


@app.command("apply-toc")
def apply_toc(
    input_pdf: Path = typer.Argument(..., help="Path to the input PDF file"),
    toc_file: Path = typer.Argument(..., help="Path to the JSON ToC file"),
    output_pdf: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Write to this path instead of replacing the input file in place",
    ),
) -> None:
    """Apply a JSON table of contents to the PDF, replacing any existing bookmarks.

    Page numbers are 1-indexed physical page positions. The PDF's page labels
    (e.g. roman numerals for front matter) are not modified.
    """
    in_place = output_pdf is None or same_path(input_pdf, output_pdf)

    if in_place:
        out_file, backup_file = normalize_paths(input_pdf)
    else:
        out_file = output_pdf
        backup_file = None

    try:
        validate_input_file(input_pdf, label="Input PDF")
        validate_input_file(toc_file, label="ToC file")
        validate_output_dir(out_file)

        try:
            raw_text = toc_file.read_text(encoding="utf-8")
            data = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            output.error(f"Invalid JSON in '{toc_file}': {exc}")
            raise typer.Exit(1)
        except Exception as exc:
            output.error(f"Could not read '{toc_file}': {message(exc)}")
            raise typer.Exit(1)

        if in_place:
            ensure_backup(out_file, backup_file)
            source = backup_file
        else:
            source = input_pdf

        with tempfile.TemporaryDirectory(dir=str(out_file.parent)) as tmp:
            temp_output = Path(tmp) / out_file.name

            with pikepdf.open(source) as pdf:
                total_pages = len(pdf.pages)
                if total_pages == 0:
                    raise AppError("Input PDF has no pages.")

                errors = validate_toc(data, total_pages)
                if errors:
                    for err in errors:
                        output.error(err)
                    raise typer.Exit(1)

                with pdf.open_outline() as outline:
                    outline.root.clear()
                    for item in build_outline_items(pdf, data):
                        outline.root.append(item)

                pdf.save(temp_output)

            temp_output.replace(out_file)

        backup_note = f" (backup: '{backup_file}')" if backup_file else ""
        output.success(f"Success: Applied ToC to '{out_file}'{backup_note}.")

    except typer.Exit:
        raise
    except AppError as exc:
        output.error(str(exc))
        raise typer.Exit(1)
    except Exception as exc:
        output.error(message(exc))
        raise typer.Exit(1)
