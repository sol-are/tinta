"""Single-PDF conversion orchestrator."""

from __future__ import annotations

import sys
from pathlib import Path

from tinta.core.converter import convert_pdf
from tinta.core.output import ExtractionMeta, _sha256, write_outputs
from tinta.core.postprocess import build_focused, check_quality
from tinta.settings import Settings


def run_one(
    pdf: Path,
    out_dir: Path,
    no_artifacts: bool,
    *,
    settings: Settings,
) -> ExtractionMeta:
    """Execute the conversion pipeline for a single PDF."""
    pdf = pdf.resolve()
    if not pdf.is_file():
        raise FileNotFoundError(f"{pdf} is not a file.")

    stem = pdf.stem
    dest = out_dir / stem

    print(f"Converting {pdf.name} ...", flush=True)

    raw_md, pages_processed, degraded_pages = convert_pdf(pdf, settings=settings)

    from glmocr.utils.markdown_utils import crop_and_replace_images

    imgs_dir = dest / "imgs"
    raw_md, _ = crop_and_replace_images(
        raw_md, [str(pdf)], imgs_dir, image_prefix="figure"
    )

    focused_md = build_focused(raw_md)
    suspicious, reasons = check_quality(raw_md, focused_md)

    meta = ExtractionMeta(
        source_pdf=str(pdf),
        raw_md_sha256=_sha256(raw_md),
        focused_md_sha256=_sha256(focused_md),
        raw_bytes=len(raw_md.encode()),
        focused_bytes=len(focused_md.encode()),
        suspicious=suspicious,
        suspicion_reasons=reasons,
        pages_processed=pages_processed,
        degraded_pages=degraded_pages,
        backend=settings.backend or "",
        model=settings.model or "",
    )

    write_outputs(
        out_dir=dest,
        raw_md=raw_md,
        focused_md=focused_md,
        meta=meta,
        no_artifacts=no_artifacts,
    )

    print(f"Done -> {dest}/", flush=True)
    if degraded_pages:
        print(
            f"Warning: {degraded_pages}/{pages_processed} pages had empty OCR output.",
            file=sys.stderr,
        )
    if suspicious:
        print(f"Warning: Suspicious: {'; '.join(reasons)}", file=sys.stderr)

    return meta
