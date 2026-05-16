import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pikepdf


class AppError(Exception):
    pass


def message(exc: BaseException) -> str:
    text = str(exc).strip()
    return text if text else exc.__class__.__name__


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def same_path(a: Path, b: Path) -> bool:
    return a.expanduser().resolve() == b.expanduser().resolve()


def normalize_paths(input_path: Path) -> tuple[Path, Path]:
    """Normalize to (output_file, backup_file) pair.

    If *input_path* ends with ``.bak`` it is treated as the backup and the
    output is derived by stripping the suffix.  Otherwise *input_path* is the
    output and the backup is ``<name>.bak``.
    """
    if input_path.name.endswith(".bak"):
        backup_file = input_path
        output_file = input_path.with_name(input_path.name[:-4])
    else:
        output_file = input_path
        backup_file = input_path.with_name(input_path.name + ".bak")
    return output_file, backup_file


def ensure_backup(output_file: Path, backup_file: Path) -> Path:
    """Make sure *backup_file* exists, creating it from *output_file* if needed.

    Returns the backup path.  Raises :class:`AppError` when neither file is
    present or the copy fails.
    """
    if backup_file.is_file():
        return backup_file

    if not output_file.is_file():
        raise AppError(f"Neither '{output_file}' nor '{backup_file}' found.")

    try:
        shutil.copy2(output_file, backup_file)
    except Exception as exc:
        raise AppError(
            f"Could not create backup '{backup_file}': {message(exc)}"
        ) from exc

    return backup_file


def validate_input_file(path: Path, label: str = "File") -> None:
    if not path.is_file():
        raise AppError(f"{label} '{path}' not found.")


def validate_output_dir(path: Path) -> None:
    if not path.parent.exists():
        raise AppError(f"Directory '{path.parent}' does not exist.")
    if path.exists() and path.is_dir():
        raise AppError(f"Output path '{path}' is a directory.")


# ---------------------------------------------------------------------------
# Argument-swap detection
# ---------------------------------------------------------------------------


def detect_swap(input_pdf: Path, image_path: Path) -> Optional[str]:
    pdf_exts = {".pdf"}
    img_exts = {".png", ".jpg", ".jpeg"}

    in_ext = input_pdf.suffix.lower()
    img_ext = image_path.suffix.lower()

    if in_ext in img_exts and img_ext in pdf_exts:
        return (
            f"It looks like the arguments may be swapped: "
            f"got an image ('{input_pdf}') as INPUT_PDF "
            f"and a PDF ('{image_path}') as IMAGE_PATH. "
            f"Try reversing the argument order."
        )

    if in_ext not in pdf_exts and img_ext in pdf_exts:
        return (
            f"Expected INPUT_PDF to be a PDF, but got '{input_pdf}'. "
            f"If the arguments are swapped, try reversing them."
        )

    return None


# ---------------------------------------------------------------------------
# PDF structure pruning
# ---------------------------------------------------------------------------


def is_text_destination(obj) -> bool:
    class_name = obj.__class__.__name__
    return isinstance(obj, str) or class_name in {"String", "Name"}


def destination_name_variants(obj) -> set[str]:
    text = str(obj)
    if text.startswith("/"):
        return {text, text[1:]}
    return {text, "/" + text}


def page_objgen_from_destination(dest) -> Optional[tuple[int, int]]:
    if isinstance(dest, pikepdf.Array) and len(dest) > 0:
        try:
            return dest[0].objgen
        except AttributeError:
            return None

    if isinstance(dest, pikepdf.Dictionary) and "/D" in dest:
        return page_objgen_from_destination(dest["/D"])

    return None


def iter_named_destination_entries(node):
    if not isinstance(node, pikepdf.Dictionary):
        return

    if "/Names" in node:
        names = node["/Names"]
        for i in range(0, len(names), 2):
            yield names[i], names[i + 1]

    if "/Kids" in node:
        for kid in node["/Kids"]:
            yield from iter_named_destination_entries(kid)


def collect_removed_named_destinations(
    pdf: pikepdf.Pdf,
    removed_pages: set[tuple[int, int]],
) -> set[str]:
    removed_names = set()
    probe = RemovedTargets(removed_pages, set())
    root = pdf.Root

    if "/Names" in root and "/Dests" in root["/Names"]:
        for key, dest in iter_named_destination_entries(root["/Names"]["/Dests"]):
            if probe.destination_removed(dest):
                removed_names.update(destination_name_variants(key))

    if "/Dests" in root and isinstance(root["/Dests"], pikepdf.Dictionary):
        for key, dest in root["/Dests"].items():
            if probe.destination_removed(dest):
                removed_names.update(destination_name_variants(key))

    return removed_names


def prune_name_tree(node, removed_names: set[str]) -> bool:
    if not isinstance(node, pikepdf.Dictionary):
        return False

    if "/Kids" in node:
        kept_kids = pikepdf.Array()
        for kid in node["/Kids"]:
            if prune_name_tree(kid, removed_names):
                kept_kids.append(kid)

        if kept_kids:
            node["/Kids"] = kept_kids
        else:
            del node["/Kids"]

    if "/Names" in node:
        names = node["/Names"]
        kept_names = pikepdf.Array()

        for i in range(0, len(names), 2):
            key = names[i]
            value = names[i + 1]

            if any(
                variant in removed_names for variant in destination_name_variants(key)
            ):
                continue

            kept_names.append(key)
            kept_names.append(value)

        if kept_names:
            node["/Names"] = kept_names
        else:
            del node["/Names"]

    return ("/Kids" in node and len(node["/Kids"]) > 0) or (
        "/Names" in node and len(node["/Names"]) > 0
    )


def prune_named_destinations(pdf: pikepdf.Pdf, removed_names: set[str]) -> None:
    if not removed_names:
        return

    root = pdf.Root

    if "/Names" in root and "/Dests" in root["/Names"]:
        names_root = root["/Names"]
        if not prune_name_tree(names_root["/Dests"], removed_names):
            del names_root["/Dests"]
        if len(names_root) == 0:
            del root["/Names"]

    if "/Dests" in root and isinstance(root["/Dests"], pikepdf.Dictionary):
        dests = root["/Dests"]
        for key in list(dests.keys()):
            if any(
                variant in removed_names for variant in destination_name_variants(key)
            ):
                del dests[key]
        if len(dests) == 0:
            del root["/Dests"]


def prune_outline(pdf: pikepdf.Pdf, removed: "RemovedTargets") -> None:
    with pdf.open_outline() as outline:

        def prune(items) -> None:
            kept = []
            for item in items:
                if removed.outline_item_removed(item):
                    continue
                prune(item.children)
                kept.append(item)
            items[:] = kept

        prune(outline.root)


def prune_internal_links(pdf: pikepdf.Pdf, removed: "RemovedTargets") -> None:
    for page in pdf.pages:
        annots = page.obj.get("/Annots")
        if not annots:
            continue

        kept = pikepdf.Array()
        changed = False

        for annot in annots:
            if str(annot.get("/Subtype", "")) == "/Link" and removed.annotation_removed(
                annot
            ):
                changed = True
                continue
            kept.append(annot)

        if not changed:
            continue

        if kept:
            page.obj["/Annots"] = kept
        elif "/Annots" in page.obj:
            del page.obj["/Annots"]


def prune_open_action(pdf: pikepdf.Pdf, removed: "RemovedTargets") -> None:
    open_action = pdf.Root.get("/OpenAction")
    if open_action is None:
        return

    if removed.destination_removed(open_action) or removed.action_removed(open_action):
        del pdf.Root["/OpenAction"]


def remove_targets_that_would_dangle(pdf: pikepdf.Pdf, pages_to_remove: int) -> None:
    """Remove outlines, named destinations, internal links, and the open
    action that would point to removed pages."""
    removed_pages = {pdf.pages[i].obj.objgen for i in range(pages_to_remove)}
    removed_names = collect_removed_named_destinations(pdf, removed_pages)
    removed = RemovedTargets(removed_pages, removed_names)

    prune_outline(pdf, removed)
    prune_internal_links(pdf, removed)
    prune_open_action(pdf, removed)
    prune_named_destinations(pdf, removed_names)


@dataclass(frozen=True)
class RemovedTargets:
    page_objgens: set[tuple[int, int]]
    named_destinations: set[str]

    def destination_removed(self, dest) -> bool:
        if dest is None:
            return False

        page_objgen = page_objgen_from_destination(dest)
        if page_objgen is not None:
            return page_objgen in self.page_objgens

        if isinstance(dest, pikepdf.Dictionary) and "/D" in dest:
            return self.destination_removed(dest["/D"])

        if is_text_destination(dest):
            return any(
                variant in self.named_destinations
                for variant in destination_name_variants(dest)
            )

        return False

    def action_removed(self, action) -> bool:
        if not isinstance(action, pikepdf.Dictionary):
            return False
        if str(action.get("/S", "")) != "/GoTo":
            return False
        if "/D" not in action:
            return False
        return self.destination_removed(action["/D"])

    def annotation_removed(self, annot) -> bool:
        if not isinstance(annot, pikepdf.Dictionary):
            return False

        if "/Dest" in annot and self.destination_removed(annot["/Dest"]):
            return True

        if "/A" in annot and self.action_removed(annot["/A"]):
            return True

        return False

    def outline_item_removed(self, item) -> bool:
        raw = getattr(item, "obj", None)

        if isinstance(raw, pikepdf.Dictionary):
            if "/Dest" in raw and self.destination_removed(raw["/Dest"]):
                return True
            if "/A" in raw and self.action_removed(raw["/A"]):
                return True
            return False

        dest = getattr(item, "destination", None)
        return self.destination_removed(dest)
