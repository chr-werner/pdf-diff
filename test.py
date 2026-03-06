import sys
from unittest.mock import MagicMock, patch

import pytest

from pdf_diff import (
    _expand_word_diff,
    colorize_diff,
    diff_pdfs,
    pages_to_lines,
    supports_color,
)

RED = "\033[31m"
GREEN = "\033[32m"
CYAN = "\033[36m"
BOLD = "\033[1m"
RESET = "\033[0m"


# ---------------------------------------------------------------------------
# pages_to_lines
# ---------------------------------------------------------------------------

class TestPagesToLines:
    def test_single_page(self):
        lines = pages_to_lines(["hello\nworld"])
        assert lines[0] == "[Page 1]\n"
        assert "hello\n" in lines
        assert "world\n" in lines

    def test_multiple_pages(self):
        lines = pages_to_lines(["page one", "page two"])
        assert "[Page 1]\n" in lines
        assert "[Page 2]\n" in lines

    def test_empty_page(self):
        lines = pages_to_lines([""])
        assert lines == ["[Page 1]\n"]

    def test_all_lines_end_with_newline(self):
        lines = pages_to_lines(["no newline at end"])
        for line in lines:
            assert line.endswith("\n"), f"Line missing newline: {line!r}"

    def test_page_already_has_newline(self):
        lines = pages_to_lines(["line with newline\n"])
        # Should not double-add newline
        assert lines.count("line with newline\n") == 1

    def test_empty_input(self):
        assert pages_to_lines([]) == []

    def test_page_markers_are_sequential(self):
        lines = pages_to_lines(["a", "b", "c"])
        markers = [l for l in lines if l.startswith("[Page")]
        assert markers == ["[Page 1]\n", "[Page 2]\n", "[Page 3]\n"]


# ---------------------------------------------------------------------------
# colorize_diff
# ---------------------------------------------------------------------------

class TestColorizeDiff:
    def test_no_color_passthrough(self):
        lines = ["--- a\n", "+++ b\n", "@@ -1 +1 @@\n", "-old\n", "+new\n"]
        result = colorize_diff(lines, use_color=False)
        assert result == "".join(lines)

    def test_header_lines_are_bold(self):
        result = colorize_diff(["--- a/file\n", "+++ b/file\n"], use_color=True)
        assert BOLD in result
        assert RESET in result

    def test_hunk_header_is_cyan(self):
        result = colorize_diff(["@@ -1,3 +1,3 @@\n"], use_color=True)
        assert CYAN in result

    def test_removed_line_is_red(self):
        result = colorize_diff(["-removed line\n"], use_color=True)
        assert RED in result
        assert "removed line" in result

    def test_added_line_is_green(self):
        result = colorize_diff(["+added line\n"], use_color=True)
        assert GREEN in result
        assert "added line" in result

    def test_context_line_has_no_color(self):
        result = colorize_diff([" context line\n"], use_color=True)
        assert RED not in result
        assert GREEN not in result
        assert CYAN not in result
        assert BOLD not in result

    def test_empty_input(self):
        assert colorize_diff([], use_color=True) == ""
        assert colorize_diff([], use_color=False) == ""


# ---------------------------------------------------------------------------
# _expand_word_diff
# ---------------------------------------------------------------------------

class TestExpandWordDiff:
    def test_splits_words_onto_own_lines(self):
        a, b = _expand_word_diff(["hello world\n"], ["hello world\n"])
        assert "hello\n" in a
        assert "world\n" in a

    def test_page_markers_pass_through(self):
        a, b = _expand_word_diff(["[Page 1]\n", "some text\n"], ["[Page 1]\n", "other\n"])
        assert a[0] == "[Page 1]\n"
        assert b[0] == "[Page 1]\n"

    def test_empty_line_becomes_newline(self):
        a, _ = _expand_word_diff(["\n"], ["\n"])
        assert a == ["\n"]

    def test_both_sides_expanded(self):
        a, b = _expand_word_diff(["foo bar\n"], ["baz qux\n"])
        assert a == ["foo\n", "bar\n"]
        assert b == ["baz\n", "qux\n"]


# ---------------------------------------------------------------------------
# supports_color
# ---------------------------------------------------------------------------

class TestSupportsColor:
    def test_returns_false_when_not_tty(self):
        with patch.object(sys.stdout, "isatty", return_value=False):
            assert supports_color() is False

    def test_returns_true_when_tty(self):
        with patch.object(sys.stdout, "isatty", return_value=True):
            assert supports_color() is True

    def test_returns_false_when_no_isatty(self):
        mock_stdout = MagicMock(spec=[])  # no isatty attribute
        with patch("pdf_diff.sys.stdout", mock_stdout):
            assert supports_color() is False


# ---------------------------------------------------------------------------
# diff_pdfs (mocked extract_text_by_page)
# ---------------------------------------------------------------------------

class TestDiffPdfs:
    def _diff(self, text_a, text_b, **kwargs):
        """Helper: run diff_pdfs with mocked page extraction."""
        kwargs.setdefault("use_color", False)
        with patch("pdf_diff.extract_text_by_page", side_effect=[text_a, text_b]):
            return diff_pdfs("a.pdf", "b.pdf", **kwargs)

    def test_identical_content_returns_empty(self):
        pages = ["same content\nline two"]
        result = self._diff(pages, pages)
        assert result == ""

    def test_changed_line_appears_in_diff(self):
        result = self._diff(["old line\n"], ["new line\n"])
        assert "-old line" in result
        assert "+new line" in result

    def test_added_page_appears_in_diff(self):
        result = self._diff(["page one\n"], ["page one\n", "page two\n"])
        assert "[Page 2]" in result

    def test_removed_page_appears_in_diff(self):
        result = self._diff(["page one\n", "page two\n"], ["page one\n"])
        assert "-[Page 2]" in result

    def test_context_lines_respected(self):
        pages = ["\n".join(str(i) for i in range(20))]
        result_narrow = self._diff(pages, [pages[0].replace("10", "TEN")], context=1)
        result_wide = self._diff(pages, [pages[0].replace("10", "TEN")], context=5)
        assert len(result_narrow) < len(result_wide)

    def test_word_diff_mode(self):
        result = self._diff(["hello world\n"], ["hello earth\n"], word_diff=True)
        assert "-world" in result
        assert "+earth" in result

    def test_diff_includes_filenames(self):
        with patch("pdf_diff.extract_text_by_page", side_effect=[["old\n"], ["new\n"]]):
            result = diff_pdfs("original.pdf", "modified.pdf", use_color=False)
        assert "original.pdf" in result
        assert "modified.pdf" in result

    def test_color_output_contains_ansi(self):
        result = self._diff(["old\n"], ["new\n"], use_color=True)
        assert RED in result or GREEN in result
