"""Tests for calpdf.output."""

from calpdf import output


class TestQuietMode:
    def test_suppresses_info(self, capsys):
        output.configure(quiet=True)
        output.info("hello")
        captured = capsys.readouterr()
        assert "hello" not in captured.out

    def test_suppresses_success(self, capsys):
        output.configure(quiet=True)
        output.success("done")
        captured = capsys.readouterr()
        assert "done" not in captured.out

    def test_keeps_warnings_and_errors(self, capsys):
        output.configure(quiet=True)
        output.warning("careful")
        output.error("boom")
        captured = capsys.readouterr()
        assert "careful" in captured.err
        assert "boom" in captured.err


class TestErrorAndWarningGoToStderr:
    def test_error_writes_to_stderr(self, capsys):
        output.error("boom")
        captured = capsys.readouterr()
        assert "boom" in captured.err
        assert "boom" not in captured.out

    def test_warning_writes_to_stderr(self, capsys):
        output.warning("careful")
        captured = capsys.readouterr()
        assert "careful" in captured.err
        assert "careful" not in captured.out


class TestRenderTocTree:
    def test_renders_entries(self, capsys):
        output.render_toc_tree(
            [
                {"title": "Ch 1", "pageNumber": 1, "children": []},
                {
                    "title": "Ch 2",
                    "pageNumber": 3,
                    "children": [
                        {"title": "Sec 2.1", "pageNumber": 4, "children": []}
                    ],
                },
            ]
        )
        captured = capsys.readouterr()
        assert "Ch 1" in captured.out
        assert "Ch 2" in captured.out
        assert "Sec 2.1" in captured.out
        assert "(p. 1)" in captured.out

    def test_empty_tree_prints_note(self, capsys):
        output.render_toc_tree([])
        captured = capsys.readouterr()
        assert "no bookmarks" in captured.out.lower()
