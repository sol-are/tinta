"""Data model and file output."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class ExtractionMeta:
    source_pdf: str
    raw_md_sha256: str = ""
    focused_md_sha256: str = ""
    raw_bytes: int = 0
    focused_bytes: int = 0
    suspicious: bool = False
    suspicion_reasons: list[str] = field(default_factory=list)
    pages_processed: int = 0


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def write_outputs(
    *,
    out_dir: Path,
    raw_md: str,
    focused_md: str,
    meta: ExtractionMeta,
    md_only: bool,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "raw.md").write_text(raw_md, encoding="utf-8")
    (out_dir / "focused.md").write_text(focused_md, encoding="utf-8")
    if not md_only:
        (out_dir / "meta.json").write_text(
            json.dumps(asdict(meta), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
