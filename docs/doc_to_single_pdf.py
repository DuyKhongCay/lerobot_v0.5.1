from pathlib import Path
import re
import shutil
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright
from pypdf import PdfWriter

base_url = "http://localhost:5173/"
docs_dir = Path(__file__).resolve().parent
toc = (docs_dir / "source" / "_toctree.yml").read_text()
pages = re.findall(r"local:\s*([^\s#]+)", toc)

pages_dir = docs_dir / "pdf_pages"
# output_pdf = docs_dir / "lerobot-docs-webview.pdf"

if pages_dir.exists():
    shutil.rmtree(pages_dir)
pages_dir.mkdir(parents=True)

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 1600})
    page.emulate_media(media="screen")

    for i, name in enumerate(pages):
        url = urljoin(base_url.rstrip("/") + "/", name)
        pdf_path = pages_dir / f"{i:03d}-{name}.pdf"
        page.goto(url, wait_until="networkidle", timeout=60000)
        page.pdf(
            path=str(pdf_path),
            format="A4",
            print_background=True,
            margin={"top": "16mm", "right": "14mm", "bottom": "16mm", "left": "14mm"},
        )

    browser.close()

# writer = PdfWriter()
# for pdf in sorted(pages_dir.glob("*.pdf")):
#     writer.append(str(pdf))

# writer.write(str(output_pdf))
# writer.close()
