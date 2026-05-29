from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

EXCLUDED_PREFIXES = (
    set(range(0, 3))
    | set(range(14, 32))
    | set(range(49, 55))
    | set(range(56, 58))
    | set(range(59, 67))
    | {70, 71, 72}
)


def pdf_prefix(path: Path) -> int | None:
    match = re.match(r"^(\d{3})-", path.name)
    if match is None:
        return None
    return int(match.group(1))


def selected_pdf_files(pages_dir: Path) -> list[Path]:
    pdfs = []
    for path in pages_dir.glob("*.pdf"):
        prefix = pdf_prefix(path)
        if prefix is None or prefix in EXCLUDED_PREFIXES:
            continue
        pdfs.append(path)
    return sorted(pdfs, key=lambda path: (pdf_prefix(path), path.name))


def merge_pdfs(pdf_files: list[Path], output_pdf: Path) -> None:
    try:
        from pypdf import PdfWriter
    except ModuleNotFoundError:
        sys.exit(
            "Missing dependency: install pypdf with `python3 -m pip install pypdf`."
        )

    writer = PdfWriter()
    for pdf in pdf_files:
        writer.append(str(pdf))

    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    writer.write(str(output_pdf))
    writer.close()


def main() -> None:
    docs_dir = Path(__file__).resolve().parent

    parser = argparse.ArgumentParser()
    parser.add_argument("--pages-dir", type=Path, default=docs_dir / "pdf_pages")
    parser.add_argument("--output", type=Path, default=docs_dir / "lerobot-ml-docs.pdf")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    pages_dir = args.pages_dir.resolve()
    output_pdf = args.output.resolve()

    if not pages_dir.exists():
        sys.exit(f"PDF pages directory does not exist: {pages_dir}")

    pdf_files = selected_pdf_files(pages_dir)
    if not pdf_files:
        sys.exit(f"No PDF files selected from: {pages_dir}")

    if args.dry_run:
        for pdf in pdf_files:
            print(pdf.name)
        print(f"\nSelected {len(pdf_files)} files")
        print(f"Output: {output_pdf}")
        return

    merge_pdfs(pdf_files, output_pdf)
    print(f"Wrote {output_pdf}")


if __name__ == "__main__":
    main()
