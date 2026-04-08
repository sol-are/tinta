"""Main conversion pipeline (orchestrator)."""

from __future__ import annotations

import sys
from pathlib import Path

from tinta.core.converter import convert_pdf
from tinta.core.output import ExtractionMeta, _sha256, write_outputs
from tinta.core.postprocess import build_focused, check_quality


def run(
    pdf: Path,
    out_dir: Path,
    md_only: bool,
    mode: str,
    api_key: str | None = None,
    api_url: str | None = None,
    model: str | None = None,
) -> None:
    """Execute the full PDF-to-Markdown conversion pipeline."""
    pdf = pdf.resolve()
    if not pdf.is_file():
        raise FileNotFoundError(f"{pdf} is not a file.")

    stem = pdf.stem
    dest = out_dir / stem

    print(f"Converting {pdf.name} ...")

    # 1. PDF -> raw Markdown
    raw_md, pages_processed = convert_pdf(
        pdf, mode=mode, api_key=api_key, api_url=api_url, model=model,
    )

    # 2. Extract images from bbox references
    from glmocr.utils.markdown_utils import crop_and_replace_images

    imgs_dir = dest / "imgs"
    raw_md, _ = crop_and_replace_images(
        raw_md, [str(pdf)], imgs_dir, image_prefix="figure"
    )

    # 3. Build focused version
    focused_md = build_focused(raw_md)

    # 4. Quality check
    suspicious, reasons = check_quality(raw_md, focused_md)

    # 5. Build meta
    meta = ExtractionMeta(
        source_pdf=str(pdf),
        raw_md_sha256=_sha256(raw_md),
        focused_md_sha256=_sha256(focused_md),
        raw_bytes=len(raw_md.encode()),
        focused_bytes=len(focused_md.encode()),
        suspicious=suspicious,
        suspicion_reasons=reasons,
        pages_processed=pages_processed,
    )

    # 6. Write outputs
    write_outputs(
        out_dir=dest,
        raw_md=raw_md,
        focused_md=focused_md,
        meta=meta,
        md_only=md_only,
    )

    print(f"Done -> {dest}/")
    if suspicious:
        print(f"Warning: Suspicious: {'; '.join(reasons)}", file=sys.stderr)
