"""Post-processing: focused extraction and quality checks."""

from __future__ import annotations

import re

# Section headers that mark the end of main body content
_END_SECTION_RE = re.compile(
    r"^#{1,3}\s+"
    r"(References|Bibliography|Works\s+Cited|Acknowledgments?|Acknowledgements?"
    r"|Appendix|Supplementary|Funding)",
    re.IGNORECASE,
)

# Lines that look like page numbers or running headers/footers
_PAGE_NUM_RE = re.compile(r"^\s*\d+\s*$")
_HEADER_FOOTER_RE = re.compile(
    r"^\s*(Page\s+\d+|Running\s+Head:|©|\d{4}\s+\w+.{0,60}$)", re.IGNORECASE
)

_MIN_FOCUSED_CHARS = 200
_MIN_RATIO = 0.10


def build_focused(raw_md: str) -> str:
    """Strip references/acknowledgments tail and noisy header/footer lines."""
    lines = raw_md.splitlines()

    # Find where end-matter begins
    cut_index = len(lines)
    for i, line in enumerate(lines):
        if _END_SECTION_RE.match(line):
            cut_index = i
            break

    body_lines: list[str] = []
    for line in lines[:cut_index]:
        if _PAGE_NUM_RE.match(line):
            continue
        if _HEADER_FOOTER_RE.match(line):
            continue
        body_lines.append(line)

    return "\n".join(body_lines).strip() + "\n"


def check_quality(raw: str, focused: str) -> tuple[bool, list[str]]:
    """Return (suspicious, reasons)."""
    reasons: list[str] = []
    if len(focused) < _MIN_FOCUSED_CHARS:
        reasons.append(f"focused text too short ({len(focused)} chars)")
    if len(raw) > 0 and len(focused) / len(raw) < _MIN_RATIO:
        reasons.append(
            f"focused/raw ratio too low ({len(focused)/len(raw):.2%})"
        )
    return bool(reasons), reasons
