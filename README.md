# pdf-diff

Diff two PDF files in git-style unified diff format.

## Requirements

- Python 3.10+
- [pypdf](https://pypdf.readthedocs.io/)

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```
python pdf_diff.py [options] file_a.pdf file_b.pdf
```

### Options

| Flag | Description |
|------|-------------|
| `-U N`, `--context N` | Number of context lines around changes (default: `3`) |
| `--word-diff` | Show word-level differences instead of line-level |
| `--no-color` | Disable colored output |

### Examples

```bash
# Basic diff
python pdf_diff.py old.pdf new.pdf

# More context lines
python pdf_diff.py -U 5 old.pdf new.pdf

# Word-level diff
python pdf_diff.py --word-diff old.pdf new.pdf

# Save to file
python pdf_diff.py --no-color old.pdf new.pdf > diff.txt
```

## Output

Output follows the unified diff format used by `git diff`:

- **Bold** — file headers (`---` / `+++`)
- **Cyan** — hunk headers (`@@`)
- **Red** — removed lines
- **Green** — added lines

Each page's content is preceded by a `[Page N]` marker so you can tell where in the document changes occur.

Color is automatically disabled when output is piped or redirected.

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | No differences found |
| `1` | Differences found |

## Limitations

PDF text extraction depends on how the PDF was created. Scanned (image-based) PDFs do not contain extractable text and will appear empty. Use an OCR tool such as [ocrmypdf](https://github.com/ocrmypdf/OCRmyPDF) to add a text layer before diffing.
