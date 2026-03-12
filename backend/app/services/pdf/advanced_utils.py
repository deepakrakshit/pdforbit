from __future__ import annotations

from io import BytesIO
from pathlib import Path
import zipfile

import fitz
from PIL import Image, ImageDraw, ImageFont

A4_PAGE_SIZE = (595, 842)
IMAGE_FORMAT_TO_CONTENT_TYPE = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
}
HTML_PAGE_SIZES = {
    "A4": (595, 842),
    "A3": (842, 1191),
    "Letter": (612, 792),
    "Legal": (612, 1008),
}


def pdf_page_count(file_path: Path) -> int:
    with fitz.open(file_path) as doc:
        return doc.page_count


def hex_to_rgb(value: str) -> tuple[float, float, float]:
    hex_value = value.lstrip("#")
    if len(hex_value) != 6:
        raise ValueError("Color values must be 6-digit hex strings.")
    return tuple(int(hex_value[index:index + 2], 16) / 255 for index in (0, 2, 4))


def resolve_position_rect(*, page_rect: fitz.Rect, position: str, width: float, height: float) -> fitz.Rect:
    margin = 24
    if position in {"center", "diagonal"}:
        x0 = (page_rect.width - width) / 2
        y0 = (page_rect.height - height) / 2
        return fitz.Rect(x0, y0, x0 + width, y0 + height)
    if position == "top_left":
        return fitz.Rect(margin, margin, margin + width, margin + height)
    if position == "top_right":
        return fitz.Rect(page_rect.width - width - margin, margin, page_rect.width - margin, margin + height)
    if position == "bottom_left":
        return fitz.Rect(margin, page_rect.height - height - margin, margin + width, page_rect.height - margin)
    if position == "bottom_right":
        return fitz.Rect(
            page_rect.width - width - margin,
            page_rect.height - height - margin,
            page_rect.width - margin,
            page_rect.height - margin,
        )
    if position == "bottom_center":
        x0 = (page_rect.width - width) / 2
        return fitz.Rect(x0, page_rect.height - height - margin, x0 + width, page_rect.height - margin)
    if position == "top_center":
        x0 = (page_rect.width - width) / 2
        return fitz.Rect(x0, margin, x0 + width, margin + height)
    return fitz.Rect(margin, margin, margin + width, margin + height)


def alignment_for_position(position: str) -> int:
    if position.endswith("right"):
        return 2
    if position.endswith("center"):
        return 1
    return 0


def load_font(font_size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype("DejaVuSans.ttf", font_size)
    except OSError:
        return ImageFont.load_default()


def watermark_anchor(*, position: str, page_width: int, page_height: int, text_width: int, text_height: int) -> tuple[int, int]:
    margin = 24
    if position in {"center", "diagonal"}:
        return ((page_width - text_width) // 2, (page_height - text_height) // 2)
    if position == "top_left":
        return (margin, margin)
    if position == "top_right":
        return (page_width - text_width - margin, margin)
    if position == "bottom_left":
        return (margin, page_height - text_height - margin)
    if position == "bottom_right":
        return (page_width - text_width - margin, page_height - text_height - margin)
    return ((page_width - text_width) // 2, (page_height - text_height) // 2)


def create_text_overlay_image(
    *,
    text: str,
    page_width: int,
    page_height: int,
    font_size: int,
    opacity: float,
    rotation: int,
    position: str,
) -> BytesIO:
    image = Image.new("RGBA", (max(page_width, 1), max(page_height, 1)), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    font = load_font(font_size)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x, y = watermark_anchor(
        position=position,
        page_width=page_width,
        page_height=page_height,
        text_width=text_width,
        text_height=text_height,
    )
    alpha = max(0, min(255, int(opacity * 255)))
    draw.text((x, y), text, fill=(0, 0, 0, alpha), font=font)
    if rotation:
        image = image.rotate(rotation, expand=False, resample=Image.Resampling.BICUBIC)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def render_page_to_image(page: fitz.Page, image_path: Path, *, dpi: int) -> None:
    pixmap = page.get_pixmap(dpi=dpi, alpha=False)
    pixmap.save(image_path)


def render_page_to_pil(page: fitz.Page, *, dpi: int) -> Image.Image:
    pixmap = page.get_pixmap(dpi=dpi, alpha=False)
    return Image.open(BytesIO(pixmap.tobytes("png")))


def write_image_to_archive(archive: zipfile.ZipFile, name: str, image: Image.Image) -> None:
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    archive.writestr(name, buffer.getvalue())


def write_text_pdf(
    *,
    page_texts: list[str],
    output_path: Path,
    page_size: tuple[int, int] = A4_PAGE_SIZE,
) -> None:
    width, height = page_size
    margin = 48
    line_height = 15
    font_size = 11
    document = fitz.open()

    for page_text in page_texts or [""]:
        lines = page_text.splitlines() or [""]
        page = document.new_page(width=width, height=height)
        y = margin
        for line in lines:
            if y > height - margin:
                page = document.new_page(width=width, height=height)
                y = margin
            page.insert_text((margin, y), line[:4000], fontsize=font_size, fontname="helv")
            y += line_height

    if document.page_count == 0:
        document.new_page(width=width, height=height)
    document.save(output_path)
