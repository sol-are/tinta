"""GLM-OCR PDF conversion."""

from __future__ import annotations

import os
from pathlib import Path


def convert_pdf(
    pdf_path: Path,
    *,
    mode: str = "maas",
    api_key: str | None = None,
    api_url: str | None = None,
    model: str | None = None,
) -> tuple[str, int]:
    """Convert a PDF to Markdown using GLM-OCR SDK.

    Passes the PDF directly to GlmOcr.parse(), which internally handles
    PDF-to-page expansion via PageLoader and runs OCR + ResultFormatter.

    Returns:
        Tuple of (markdown_text, pages_processed).
    """
    from glmocr import GlmOcr

    # For selfhosted mode, the SDK reads OCR API settings from env vars
    # (see _ENV_MAP in glmocr/config.py)
    if api_url is not None:
        os.environ["GLMOCR_OCR_API_URL"] = api_url
    if model is not None:
        os.environ["GLMOCR_OCR_MODEL"] = model

    ocr_kwargs: dict[str, object] = {"mode": mode}
    if mode == "selfhosted":
        # Layout detection config with id2label, label_task_mapping, etc.
        ocr_kwargs["config_path"] = str(
            Path(__file__).parent.parent / "glmocr_layout_config.yaml"
        )
    if api_key is not None:
        ocr_kwargs["api_key"] = api_key

    with GlmOcr(**ocr_kwargs) as parser:
        result = parser.parse(str(pdf_path), save_layout_visualization=False)

    # mlx-vlm decodes BPE token 0 as \x00; strip these null bytes.
    raw_md = (result.markdown_result or "").replace("\x00", "")

    # Count pages from json_result (list of per-page results)
    if isinstance(result.json_result, list):
        pages_processed = len(result.json_result)
    else:
        pages_processed = 1

    return raw_md, pages_processed
