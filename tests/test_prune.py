from pathlib import Path

import pikepdf

from calpdf.prune import (
    RemovedTargets,
    destination_name_variants,
    is_text_destination,
)


class TestDestinationNameVariants:
    def test_without_slash(self):
        assert destination_name_variants("foo") == {"foo", "/foo"}

    def test_with_slash(self):
        assert destination_name_variants("/foo") == {"/foo", "foo"}


class TestIsTextDestination:
    def test_string(self):
        assert is_text_destination("hello") is True

    def test_non_string(self):
        assert is_text_destination(42) is False


class TestRemovedTargets:
    def test_destination_removed_by_page(self, sample_pdf: Path):
        with pikepdf.open(sample_pdf) as pdf:
            objgen = pdf.pages[0].obj.objgen
            removed = RemovedTargets({objgen}, set())
            dest = pikepdf.Array([pdf.pages[0].obj, pikepdf.Name("/Fit")])
            assert removed.destination_removed(dest) is True

    def test_destination_not_removed(self, sample_pdf: Path):
        with pikepdf.open(sample_pdf) as pdf:
            objgen = pdf.pages[0].obj.objgen
            removed = RemovedTargets({objgen}, set())
            dest = pikepdf.Array([pdf.pages[1].obj, pikepdf.Name("/Fit")])
            assert removed.destination_removed(dest) is False

    def test_destination_removed_none(self):
        removed = RemovedTargets(set(), set())
        assert removed.destination_removed(None) is False

    def test_action_removed_goto(self, sample_pdf: Path):
        with pikepdf.open(sample_pdf) as pdf:
            objgen = pdf.pages[0].obj.objgen
            removed = RemovedTargets({objgen}, set())
            action = pikepdf.Dictionary(
                {
                    "/S": pikepdf.Name("/GoTo"),
                    "/D": pikepdf.Array([pdf.pages[0].obj, pikepdf.Name("/Fit")]),
                }
            )
            assert removed.action_removed(action) is True

    def test_action_not_goto(self):
        removed = RemovedTargets(set(), set())
        action = pikepdf.Dictionary({"/S": pikepdf.Name("/URI")})
        assert removed.action_removed(action) is False

    def test_annotation_removed_by_dest(self, sample_pdf: Path):
        with pikepdf.open(sample_pdf) as pdf:
            objgen = pdf.pages[0].obj.objgen
            removed = RemovedTargets({objgen}, set())
            annot = pikepdf.Dictionary(
                {
                    "/Subtype": pikepdf.Name("/Link"),
                    "/Dest": pikepdf.Array([pdf.pages[0].obj, pikepdf.Name("/Fit")]),
                }
            )
            assert removed.annotation_removed(annot) is True
