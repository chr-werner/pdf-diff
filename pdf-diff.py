#!/usr/bin/env python3
"""
pdf_diff.py - Diff two PDF files in git-style unified diff format.

Usage:
    python pdf_diff.py [options] file_a.pdf file_b.pdf

Requires:
    pip install pypdf
"""

import sys
import argparse
import difflib
from pathlib import Path

try:
    from pypdf import PdfReader
except ImportError:
    print("Error: pypdf is required. Install it with: pip install pypdf", file=sys.stderr)
    sys.exit(1)

# ANSI color codes
RED = "\033[31m"
GREEN = "\033[32m"
CYAN = "\033[36m"
BOLD = "\033[1m"
RESET = "\033[0m"


def extract_text_by_page(pdf_path: str) -> list[str]:
    """
    Extract text from each page of a PDF.

    Args:
        pdf_path: Path to the PDF file to read.

    Returns:
        A list of strings, one per page, containing the extracted text.
        Pages with no extractable text return an empty string.
    """
    reader = PdfReader(pdf_path)
    pages = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text)
    return pages


def pages_to_lines(pages: list[str]) -> list[str]:
    """
    Convert a list of page strings into a flat list of lines with page markers.

    Args:
        pages: List of page text strings, as returned by extract_text_by_page.

    Returns:
        A flat list of lines with a "[Page N]" header inserted before each
        page's content. All lines are guaranteed to end with a newline.
    """
    lines = []
    for i, page_text in enumerate(pages, start=1):
        lines.append(f"[Page {i}]\n")
        for line in page_text.splitlines(keepends=True):
            if not line.endswith("\n"):
                line += "\n"
            lines.append(line)
    return lines


def colorize_diff(diff_lines: list[str], use_color: bool) -> str:
    """
    Apply git-style ANSI colors to unified diff output.

    Args:
        diff_lines: Lines of a unified diff, as produced by difflib.unified_diff.
        use_color: If True, wrap lines in ANSI escape codes; if False, return
            lines unchanged.

    Returns:
        A single string with all lines joined, optionally colorized:
        bold for file headers (---/+++), cyan for hunk headers (@@),
        red for removed lines (-), and green for added lines (+).
    """
    output = []
    for line in diff_lines:
        if not use_color:
            output.append(line)
            continue

        if line.startswith("---") or line.startswith("+++"):
            output.append(BOLD + line + RESET)
        elif line.startswith("@@"):
            output.append(CYAN + line + RESET)
        elif line.startswith("-"):
            output.append(RED + line + RESET)
        elif line.startswith("+"):
            output.append(GREEN + line + RESET)
        else:
            output.append(line)

    return "".join(output)


def diff_pdfs(
    path_a: str,
    path_b: str,
    context: int = 3,
    use_color: bool = True,
    word_diff: bool = False,
) -> str:
    """
    Generate a unified diff between two PDF files.

    Args:
        path_a: Path to the original PDF.
        path_b: Path to the modified PDF.
        context: Number of context lines around changes.
        use_color: Whether to colorize output.
        word_diff: If True, show word-level diffs within changed lines.

    Returns:
        The diff as a string.
    """
    pages_a = extract_text_by_page(path_a)
    pages_b = extract_text_by_page(path_b)

    lines_a = pages_to_lines(pages_a)
    lines_b = pages_to_lines(pages_b)

    if word_diff:
        lines_a, lines_b = _expand_word_diff(lines_a, lines_b)

    diff = list(
        difflib.unified_diff(
            lines_a,
            lines_b,
            fromfile=f"a/{Path(path_a).name}",
            tofile=f"b/{Path(path_b).name}",
            n=context,
        )
    )

    if not diff:
        return ""

    return colorize_diff(diff, use_color)


def _expand_word_diff(
    lines_a: list[str], lines_b: list[str]
) -> tuple[list[str], list[str]]:
    """
    Expand lines so that each word is on its own line.

    This makes the diff show word-level changes instead of line-level changes.
    Page marker lines (e.g. "[Page N]") are passed through unchanged.

    Args:
        lines_a: Lines from the original document.
        lines_b: Lines from the modified document.

    Returns:
        A tuple of (expanded_lines_a, expanded_lines_b) where each word
        occupies its own line ending with a newline character.
    """
    def split_words(lines):
        result = []
        for line in lines:
            if line.startswith("[Page "):
                result.append(line)
            else:
                words = line.split()
                for w in words:
                    result.append(w + "\n")
                if not words:
                    result.append("\n")
        return result

    return split_words(lines_a), split_words(lines_b)


def supports_color() -> bool:
    """
    Check if the current stdout supports color output.

    Returns:
        True if stdout is a TTY (i.e. an interactive terminal), False otherwise.
        Returns False when output is piped or redirected to a file.
    """
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def main():
    parser = argparse.ArgumentParser(
        description="Diff two PDF files in git-style unified diff format.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python pdf_diff.py old.pdf new.pdf
  python pdf_diff.py --context 5 old.pdf new.pdf
  python pdf_diff.py --word-diff old.pdf new.pdf
  python pdf_diff.py --no-color old.pdf new.pdf > diff.txt
        """,
    )
    parser.add_argument("file_a", help="Original PDF file")
    parser.add_argument("file_b", help="Modified PDF file")
    parser.add_argument(
        "-U", "--context",
        type=int,
        default=3,
        metavar="N",
        help="Number of context lines (default: 3)",
    )
    parser.add_argument(
        "--word-diff",
        action="store_true",
        help="Show word-level differences instead of line-level",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output",
    )

    args = parser.parse_args()

    for path in (args.file_a, args.file_b):
        if not Path(path).exists():
            print(f"Error: file not found: {path}", file=sys.stderr)
            sys.exit(1)
        if not path.lower().endswith(".pdf"):
            print(f"Warning: {path} does not have a .pdf extension", file=sys.stderr)

    use_color = supports_color() and not args.no_color

    result = diff_pdfs(
        args.file_a,
        args.file_b,
        context=args.context,
        use_color=use_color,
        word_diff=args.word_diff,
    )

    if result:
        print(result, end="")
        sys.exit(1)  # Exit 1 means differences found, like git diff
    else:
        print("No differences found.")
        sys.exit(0)


if __name__ == "__main__":
    main()
