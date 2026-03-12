from __future__ import annotations

import fitz


def extract_pdf_text_pages(file_path: str) -> list[str]:
    pages: list[str] = []
    with fitz.open(file_path) as pdf:
        for page in pdf:
            pages.append(page.get_text("text").strip() or "(no extractable text)")
    return pages