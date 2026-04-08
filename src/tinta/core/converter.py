"""GLM-OCR PDF conversion."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import yaml


_BASE_CONFIG_PATH = Path(__file__).parent.parent / "glmocr_layout_config.yaml"


def _build_config(
    *,
    api_url: str | None = None,
    model: str | None = None,
    api_mode: str | None = None,
) -> str:
    """Load the base YAML config, overlay CLI overrides, write to a tempfile.

    Returns the path to the temporary config file.  Caller is responsible
    for deleting it after use.
    """
    data = yaml.safe_load(_BASE_CONFIG_PATH.read_text(encoding="utf-8")) or {}
    ocr_api = data.setdefault("pipeline", {}).setdefault("ocr_api", {})

    if api_url is not None:
        ocr_api["api_url"] = api_url
    if model is not None:
        ocr_api["model"] = model
    if api_mode is not None:
        ocr_api["api_mode"] = api_mode

    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, prefix="tinta_",
    )
    yaml.dump(data, tmp, default_flow_style=False)
    tmp.close()
    return tmp.name


def convert_pdf(
    pdf_path: Path,
    *,
    mode: str = "maas",
    api_key: str | None = None,
    api_url: str | None = None,
    model: str | None = None,
    api_mode: str | None = None,
) -> tuple[str, int]:
    """Convert a PDF to Markdown using GLM-OCR SDK.

    Returns:
        Tuple of (markdown_text, pages_processed).
    """
    from glmocr import GlmOcr

    ocr_kwargs: dict[str, object] = {"mode": mode}

    if mode == "selfhosted":
        config_path = _build_config(
            api_url=api_url, model=model, api_mode=api_mode,
        )
        ocr_kwargs["config_path"] = config_path

    if api_key is not None:
        ocr_kwargs["api_key"] = api_key

    try:
        with GlmOcr(**ocr_kwargs) as parser:
            result = parser.parse(str(pdf_path), save_layout_visualization=False)
    finally:
        if mode == "selfhosted":
            os.unlink(config_path)

    # mlx-vlm decodes BPE token 0 as \x00; strip these null bytes.
    raw_md = (result.markdown_result or "").replace("\x00", "")

    # Count pages from json_result (list of per-page results)
    if isinstance(result.json_result, list):
        pages_processed = len(result.json_result)
    else:
        pages_processed = 1

    return raw_md, pages_processed
