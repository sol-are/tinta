"""GLM-OCR PDF conversion."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Optional

import yaml

from tinta.settings import Settings


_BASE_CONFIG_PATH = Path(__file__).parent.parent / "glmocr_layout_config.yaml"


def _build_config(*, settings: Settings) -> str:
    """Load the base YAML config, overlay settings, write to a tempfile.

    Returns the path to the temporary config file. Caller is responsible
    for deleting it after use.
    """
    data = yaml.safe_load(_BASE_CONFIG_PATH.read_text(encoding="utf-8")) or {}
    pipeline = data.setdefault("pipeline", {})
    ocr_api = pipeline.setdefault("ocr_api", {})

    if settings.api_url is not None:
        ocr_api["api_url"] = settings.api_url
    if settings.api_path is not None:
        ocr_api["api_path"] = settings.api_path
    if settings.model is not None:
        ocr_api["model"] = settings.model
    if settings.api_mode:
        ocr_api["api_mode"] = settings.api_mode
    if settings.request_timeout is not None:
        ocr_api["request_timeout"] = settings.request_timeout
    if settings.connect_timeout is not None:
        ocr_api["connect_timeout"] = settings.connect_timeout
    if settings.retry_max_attempts is not None:
        ocr_api["retry_max_attempts"] = settings.retry_max_attempts

    if settings.max_workers is not None:
        pipeline["max_workers"] = settings.max_workers

    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, prefix="tinta_",
    )
    yaml.dump(data, tmp, default_flow_style=False)
    tmp.close()
    return tmp.name


def render_config(settings: Settings) -> str:
    """Return the YAML the converter would feed to glmocr (for --print-config)."""
    path = _build_config(settings=settings)
    try:
        return Path(path).read_text(encoding="utf-8")
    finally:
        os.unlink(path)


def convert_pdf(
    pdf_path: Path,
    *,
    settings: Settings,
) -> tuple[str, int, int]:
    """Convert a PDF to Markdown using GLM-OCR SDK.

    Returns:
        (markdown_text, pages_processed, degraded_pages)
        ``degraded_pages`` counts pages where every region returned empty
        content from the OCR backend.
    """
    from glmocr import GlmOcr

    if settings.api_key:
        # MaaS path: GlmOcr ctor kwargs map directly to pipeline.maas.*
        with GlmOcr(
            api_key=settings.api_key,
            api_url=settings.api_url,
            model=settings.model,
        ) as parser:
            result = parser.parse(str(pdf_path), save_layout_visualization=False)
    else:
        config_path = _build_config(settings=settings)
        try:
            with GlmOcr(mode="selfhosted", config_path=config_path) as parser:
                result = parser.parse(str(pdf_path), save_layout_visualization=False)
        finally:
            os.unlink(config_path)

    # mlx-vlm decodes BPE token 0 as \x00; strip these null bytes.
    raw_md = (result.markdown_result or "").replace("\x00", "")

    pages_processed, degraded_pages = _count_pages(result.json_result)
    return raw_md, pages_processed, degraded_pages


def _count_pages(json_result) -> tuple[int, int]:
    if not isinstance(json_result, list):
        return 1, 0
    degraded = 0
    for page in json_result:
        regions = []
        if isinstance(page, dict):
            regions = page.get("regions") or page.get("results") or []
        if regions and all(
            (r.get("content") or "").strip() == "" for r in regions if isinstance(r, dict)
        ):
            degraded += 1
    return len(json_result), degraded
