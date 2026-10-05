import pdfplumber
from .common import rows_to_items, fix_positions

def parse_pdf(file, pages=None):
    items = []
    state = {}
    with pdfplumber.open(file) as pdf:
        for n, page in enumerate(pdf.pages, 1):
            if pages and n not in pages:
                continue
            for settings in (None, {"vertical_strategy": "text", "horizontal_strategy": "text"}):
                tables = page.extract_tables(settings) if settings else page.extract_tables()
                found = []
                for t in tables:
                    found += rows_to_items(t, source=f"PDF стр. {n}", state=state)
                if found:
                    items += found
                    break
    return fix_positions(items)
