from pathlib import Path

import pikepdf

from calpdf.prune import (
    RemovedTargets,
    destination_name_variants,
    is_text_destination,
    page_objgen_from_destination,
    remove_targets_that_would_dangle,
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

    def test_destination_removed_by_name(self):
        removed = RemovedTargets(set(), {"ch2"})
        assert removed.destination_removed(pikepdf.Name("/ch2")) is True

    def test_destination_removed_by_string(self):
        removed = RemovedTargets(set(), {"ch2"})
        assert removed.destination_removed(pikepdf.String("/ch2")) is True

    def test_outline_item_removed_by_action(self, sample_pdf: Path):
        with pikepdf.open(sample_pdf) as pdf:
            objgen = pdf.pages[0].obj.objgen
            removed = RemovedTargets({objgen}, set())
            action = pikepdf.Dictionary(
                {
                    "/S": pikepdf.Name("/GoTo"),
                    "/D": pikepdf.Array([pdf.pages[0].obj, pikepdf.Name("/Fit")]),
                }
            )
            with pdf.open_outline() as outline:
                item = pikepdf.OutlineItem("Gone", action=action)
                outline.root.append(item)
            assert removed.outline_item_removed(item) is True

    def test_outline_item_kept(self, sample_pdf: Path):
        with pikepdf.open(sample_pdf) as pdf:
            removed = RemovedTargets(set(), set())
            with pdf.open_outline() as outline:
                item = pikepdf.OutlineItem("Kept", pdf.pages[0].obj)
                outline.root.append(item)
            assert removed.outline_item_removed(item) is False


class TestPageObjgenFromDestination:
    def test_array(self, sample_pdf: Path):
        with pikepdf.open(sample_pdf) as pdf:
            dest = pikepdf.Array([pdf.pages[0].obj, pikepdf.Name("/Fit")])
            assert page_objgen_from_destination(dest) == pdf.pages[0].obj.objgen

    def test_named_dest_returns_none(self):
        assert page_objgen_from_destination(pikepdf.Name("/ch2")) is None


class TestRemoveTargetsEndToEnd:
    def test_prunes_outline(self, sample_pdf: Path):
        with pikepdf.open(sample_pdf) as pdf:
            with pdf.open_outline() as outline:
                outline.root.append(
                    pikepdf.OutlineItem(
                        "Gone", pikepdf.Array([pdf.pages[0].obj, pikepdf.Name("/Fit")])
                    )
                )
            remove_targets_that_would_dangle(pdf, 1)
            with pdf.open_outline() as outline:
                assert len(outline.root) == 0

    def test_keeps_valid_outline_targets(self, sample_pdf: Path):
        with pikepdf.open(sample_pdf) as pdf:
            with pdf.open_outline() as outline:
                outline.root.append(
                    pikepdf.OutlineItem(
                        "Kept", pikepdf.Array([pdf.pages[2].obj, pikepdf.Name("/Fit")])
                    )
                )
            remove_targets_that_would_dangle(pdf, 1)
            with pdf.open_outline() as outline:
                assert len(outline.root) == 1
                assert outline.root[0].title == "Kept"

    def test_removes_internal_links(self, sample_pdf: Path):
        with pikepdf.open(sample_pdf) as pdf:
            annot = pikepdf.Dictionary(
                {
                    "/Type": pikepdf.Name("/Annot"),
                    "/Subtype": pikepdf.Name("/Link"),
                    "/Rect": pikepdf.Array([0, 0, 10, 10]),
                    "/Dest": pikepdf.Array([pdf.pages[0].obj, pikepdf.Name("/Fit")]),
                }
            )
            pdf.pages[1].obj["/Annots"] = pikepdf.Array([annot])
            remove_targets_that_would_dangle(pdf, 1)
            assert "/Annots" not in pdf.pages[1].obj

    def test_keeps_unrelated_annotations(self, sample_pdf: Path):
        with pikepdf.open(sample_pdf) as pdf:
            annot = pikepdf.Dictionary(
                {
                    "/Type": pikepdf.Name("/Annot"),
                    "/Subtype": pikepdf.Name("/Link"),
                    "/Rect": pikepdf.Array([0, 0, 10, 10]),
                    "/Dest": pikepdf.Array([pdf.pages[2].obj, pikepdf.Name("/Fit")]),
                }
            )
            pdf.pages[1].obj["/Annots"] = pikepdf.Array([annot])
            remove_targets_that_would_dangle(pdf, 1)
            assert len(pdf.pages[1].obj["/Annots"]) == 1

    def test_removes_open_action(self, sample_pdf: Path):
        with pikepdf.open(sample_pdf) as pdf:
            pdf.Root["/OpenAction"] = pikepdf.Array(
                [pdf.pages[0].obj, pikepdf.Name("/Fit")]
            )
            remove_targets_that_would_dangle(pdf, 1)
            assert "/OpenAction" not in pdf.Root

    def test_keeps_valid_open_action(self, sample_pdf: Path):
        with pikepdf.open(sample_pdf) as pdf:
            pdf.Root["/OpenAction"] = pikepdf.Array(
                [pdf.pages[2].obj, pikepdf.Name("/Fit")]
            )
            remove_targets_that_would_dangle(pdf, 1)
            assert "/OpenAction" in pdf.Root

    def test_prunes_named_destinations(self, sample_pdf: Path):
        with pikepdf.open(sample_pdf) as pdf:
            pdf.Root["/Dests"] = pikepdf.Dictionary(
                {
                    "/gone": pikepdf.Array([pdf.pages[0].obj, pikepdf.Name("/Fit")]),
                    "/kept": pikepdf.Array([pdf.pages[2].obj, pikepdf.Name("/Fit")]),
                }
            )
            remove_targets_that_would_dangle(pdf, 1)
            dests = pdf.Root["/Dests"]
            assert "/gone" not in dests
            assert "/kept" in dests

    def test_prunes_names_tree(self, sample_pdf: Path):
        with pikepdf.open(sample_pdf) as pdf:
            pdf.Root["/Names"] = pikepdf.Dictionary(
                {
                    "/Dests": pikepdf.Dictionary(
                        {
                            "/Names": pikepdf.Array(
                                [
                                    pikepdf.Name("/gone"),
                                    pikepdf.Array(
                                        [pdf.pages[0].obj, pikepdf.Name("/Fit")]
                                    ),
                                    pikepdf.Name("/kept"),
                                    pikepdf.Array(
                                        [pdf.pages[2].obj, pikepdf.Name("/Fit")]
                                    ),
                                ]
                            )
                        }
                    )
                }
            )
            remove_targets_that_would_dangle(pdf, 1)
            dests = pdf.Root["/Names"]["/Dests"]
            assert len(dests["/Names"]) == 2
            assert str(dests["/Names"][0]) == "/kept"
