from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path

import fitz
import pytest
from PIL import Image

from app.core.config import AppSettings
from app.schemas.editor_operations_schema import EditorApplyJobRequest
from app.schemas.job import TOOL_PAYLOAD_MODELS
from app.services.pdf.common import JobInputFile, PdfProcessingError, ProcessorContext
from app.services.pdf.editor_apply import ApplyPdfEditorChangesProcessor
from app.services.pdf.processor import PdfJobProcessor



def _tiny_png_base64() -> str:
    buffer = BytesIO()
    Image.new("RGBA", (12, 12), (220, 20, 60, 255)).save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _create_pdf(path: Path, *, pages: int) -> Path:
    document = fitz.open()
    for page_number in range(1, pages + 1):
        page = document.new_page(width=595, height=842)
        page.insert_text(
            fitz.Point(72, 96),
            f"Page {page_number}",
            fontname="helv",
            fontsize=18,
            color=(0, 0, 0),
        )
    document.save(path)
    document.close()
    return path


def _build_context(
    tmp_path: Path,
    *,
    payload: dict,
    pages: int = 2,
) -> ProcessorContext:
    source_path = _create_pdf(tmp_path / "source.pdf", pages=pages)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return ProcessorContext(
        job_id="job_editor_test",
        tool_id="editor_apply",
        payload=payload,
        inputs=[
            JobInputFile(
                public_id="file_editor_test",
                role="source",
                original_filename="source.pdf",
                storage_path=source_path,
                page_count=pages,
                is_encrypted=False,
                size_bytes=source_path.stat().st_size,
            )
        ],
        workspace=workspace,
    )


def _run_processor(tmp_path: Path, *, payload: dict, pages: int = 2):
    context = _build_context(tmp_path, payload=payload, pages=pages)
    processor = ApplyPdfEditorChangesProcessor()
    result = processor.process(context)
    assert result.artifact.local_path.exists()
    assert result.artifact.local_path.parent == context.workspace
    return context, result


def _editor_payload(*, operations: list[dict], output_filename: str = "edited.pdf") -> dict:
    return EditorApplyJobRequest(
        file_id="file_editor_test",
        output_filename=output_filename,
        operations=operations,
        canvas_width=800,
        canvas_height=1100,
    ).model_dump(mode="json")


def test_text_insert_writes_text_to_pdf(tmp_path: Path) -> None:
    payload = _editor_payload(
        operations=[
            {
                "type": "text_insert",
                "page": 1,
                "x": 72,
                "y": 140,
                "width": 220,
                "height": 80,
                "text": "Editor note",
                "font_size": 16,
                "font_name": "helv",
                "color": "#111111",
                "opacity": 1,
                "align": "left",
                "rotation": 0,
                "line_height": 1.2,
            }
        ]
    )

    _, result = _run_processor(tmp_path, payload=payload)

    with fitz.open(result.artifact.local_path) as document:
        text = document[0].get_text("text")

    assert "Editor note" in text
    assert result.artifact.metadata["operations_applied"] == 1


def test_text_replace_writes_replacement_text_to_pdf(tmp_path: Path) -> None:
    payload = _editor_payload(
        operations=[
            {
                "type": "text_replace",
                "page": 1,
                "original_text": "Page 1",
                "replacement_text": "Updated Page 1",
                "original_x": 72,
                "original_y": 78,
                "original_width": 90,
                "original_height": 26,
                "x": 72,
                "y": 78,
                "width": 140,
                "height": 28,
                "font_size": 18,
                "font_name": "helv",
                "color": "#111111",
                "opacity": 1,
                "align": "left",
                "rotation": 0,
                "line_height": 1.2,
            }
        ]
    )

    _, result = _run_processor(tmp_path, payload=payload)

    with fitz.open(result.artifact.local_path) as document:
        text = document[0].get_text("text")

    assert "Updated Page 1" in text
    assert result.artifact.metadata["operations_applied"] == 1


def test_editor_payload_and_processor_are_registered() -> None:
    assert TOOL_PAYLOAD_MODELS["editor_apply"] is EditorApplyJobRequest

    processor = PdfJobProcessor(AppSettings())
    resolved = processor._get_processor("editor_apply")

    assert isinstance(resolved, ApplyPdfEditorChangesProcessor)


@pytest.mark.parametrize(
    ("name", "operation"),
    [
        (
            "highlight",
            {
                "type": "highlight",
                "page": 1,
                "rects": [(72, 130, 180, 160)],
                "color": "#FFE066",
                "opacity": 0.5,
            },
        ),
        (
            "draw",
            {
                "type": "draw",
                "page": 1,
                "path_data": "M 80 180 L 220 220",
                "color": "#CC0000",
                "width": 3,
                "opacity": 1,
                "cap_style": "round",
                "join_style": "round",
            },
        ),
        (
            "image_insert",
            {
                "type": "image_insert",
                "page": 1,
                "x": 72,
                "y": 200,
                "width": 80,
                "height": 80,
                "image_data": _tiny_png_base64(),
                "opacity": 1,
                "rotation": 0,
            },
        ),
        (
            "signature_insert",
            {
                "type": "signature_insert",
                "page": 1,
                "x": 72,
                "y": 300,
                "width": 90,
                "height": 45,
                "image_data": _tiny_png_base64(),
                "opacity": 1,
            },
        ),
        (
            "shape_insert",
            {
                "type": "shape_insert",
                "page": 1,
                "x": 72,
                "y": 360,
                "width": 120,
                "height": 60,
                "shape_type": "rect",
                "fill_color": "#FFFFFF",
                "stroke_color": "#0044CC",
                "stroke_width": 2,
                "fill_opacity": 0.2,
                "stroke_opacity": 1,
                "rotation": 0,
            },
        ),
    ],
)
def test_overlay_operations_generate_modified_pdf(tmp_path: Path, name: str, operation: dict) -> None:
    payload = _editor_payload(operations=[operation], output_filename=f"{name}.pdf")
    context, result = _run_processor(tmp_path, payload=payload)

    assert result.artifact.local_path.stat().st_size > 0
    assert result.artifact.local_path.stat().st_size != context.inputs[0].storage_path.stat().st_size
    with fitz.open(result.artifact.local_path) as document:
        assert document.page_count == 2


def test_page_rotate_updates_output_rotation(tmp_path: Path) -> None:
    payload = _editor_payload(
        operations=[
            {"type": "page_rotate", "page": 1, "angle": 90}
        ]
    )

    _, result = _run_processor(tmp_path, payload=payload)

    with fitz.open(result.artifact.local_path) as document:
        assert document[0].rotation == 90
        assert document.page_count == 2


def test_page_delete_removes_selected_page(tmp_path: Path) -> None:
    payload = _editor_payload(
        operations=[
            {"type": "page_delete", "page": 2}
        ]
    )

    _, result = _run_processor(tmp_path, payload=payload, pages=3)

    with fitz.open(result.artifact.local_path) as document:
        page_texts = [document[index].get_text("text") for index in range(document.page_count)]

    assert len(page_texts) == 2
    assert "Page 1" in page_texts[0]
    assert "Page 3" in page_texts[1]


def test_page_reorder_changes_page_order(tmp_path: Path) -> None:
    payload = _editor_payload(
        operations=[
            {"type": "page_reorder", "page": 1, "new_order": [3, 1, 2]}
        ]
    )

    _, result = _run_processor(tmp_path, payload=payload, pages=3)

    with fitz.open(result.artifact.local_path) as document:
        page_texts = [document[index].get_text("text") for index in range(document.page_count)]

    assert "Page 3" in page_texts[0]
    assert "Page 1" in page_texts[1]
    assert "Page 2" in page_texts[2]


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        (
            _editor_payload(
                operations=[
                    {
                        "type": "text_insert",
                        "page": 1,
                        "x": 72,
                        "y": 100,
                        "width": 120,
                        "height": 40,
                        "text": "Angled text",
                        "font_size": 14,
                        "font_name": "helv",
                        "color": "#111111",
                        "opacity": 1,
                        "align": "left",
                        "rotation": 15,
                        "line_height": 1.2,
                    }
                ]
            ),
            "editor_rotation_unsupported",
        ),
        (
            _editor_payload(
                operations=[
                    {
                        "type": "image_insert",
                        "page": 1,
                        "x": 72,
                        "y": 200,
                        "width": 80,
                        "height": 80,
                        "image_data": _tiny_png_base64(),
                        "opacity": 1,
                        "rotation": 12,
                    }
                ]
            ),
            "editor_rotation_unsupported",
        ),
        (
            _editor_payload(
                operations=[
                    {
                        "type": "text_replace",
                        "page": 1,
                        "original_text": "Bad replace",
                        "replacement_text": "Still bad",
                        "original_x": 560,
                        "original_y": 100,
                        "original_width": 120,
                        "original_height": 40,
                        "x": 560,
                        "y": 100,
                        "width": 120,
                        "height": 40,
                        "font_size": 14,
                        "font_name": "helv",
                        "color": "#111111",
                        "opacity": 1,
                        "align": "left",
                        "rotation": 0,
                        "line_height": 1.2,
                    }
                ]
            ),
            "editor_coords_out_of_bounds",
        ),
        (
            _editor_payload(
                operations=[
                    {
                        "type": "text_insert",
                        "page": 1,
                        "x": 560,
                        "y": 100,
                        "width": 120,
                        "height": 40,
                        "text": "Out of bounds",
                        "font_size": 14,
                        "font_name": "helv",
                        "color": "#111111",
                        "opacity": 1,
                        "align": "left",
                        "rotation": 0,
                        "line_height": 1.2,
                    }
                ]
            ),
            "editor_coords_out_of_bounds",
        ),
        (
            _editor_payload(
                operations=[
                    {
                        "type": "text_insert",
                        "page": 9,
                        "x": 72,
                        "y": 100,
                        "width": 120,
                        "height": 40,
                        "text": "Bad page",
                        "font_size": 14,
                        "font_name": "helv",
                        "color": "#111111",
                        "opacity": 1,
                        "align": "left",
                        "rotation": 0,
                        "line_height": 1.2,
                    }
                ]
            ),
            "editor_invalid_page",
        ),
        (
            _editor_payload(
                operations=[
                    {
                        "type": "draw",
                        "page": 1,
                        "path_data": "M 10 10 S 20 20 30 30",
                        "color": "#CC0000",
                        "width": 2,
                        "opacity": 1,
                        "cap_style": "round",
                        "join_style": "round",
                    }
                ]
            ),
            "editor_invalid_draw_path",
        ),
        (
            _editor_payload(
                operations=[
                    {"type": "page_reorder", "page": 1, "new_order": [1, 2]}
                ]
            ),
            "editor_invalid_reorder",
        ),
    ],
)
def test_invalid_editor_payloads_raise_pdf_processing_error(
    tmp_path: Path,
    payload: dict,
    code: str,
) -> None:
    context = _build_context(tmp_path, payload=payload, pages=3 if code == "editor_invalid_reorder" else 2)

    with pytest.raises(PdfProcessingError) as exc_info:
        ApplyPdfEditorChangesProcessor().process(context)

    assert exc_info.value.code == code


def test_deleting_all_pages_raises_pdf_processing_error(tmp_path: Path) -> None:
    payload = _editor_payload(
        operations=[
            {"type": "page_delete", "page": 1}
        ]
    )
    context = _build_context(tmp_path, payload=payload, pages=1)

    with pytest.raises(PdfProcessingError) as exc_info:
        ApplyPdfEditorChangesProcessor().process(context)

    assert exc_info.value.code == "editor_cannot_delete_all_pages"
