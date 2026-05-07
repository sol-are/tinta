"""Post-processing: focused extraction and quality checks."""

from __future__ import annotations

import re

# Optional label prefix on a section heading: "A ", "A.", "A1.", "1 ", "1." etc.
_LABEL_PREFIX = r"(?:[A-Z]\d*\.?\s+|\d+\.?\s+)?"

# Headings that start an end-matter region to drop from the focused output.
_DROP_SECTION_RE = re.compile(
    rf"^#{{1,3}}\s+{_LABEL_PREFIX}"
    r"(References|Bibliography|Works\s+Cited|Acknowledgments?|Acknowledgements?|Funding)\b",
    re.IGNORECASE,
)

# Headings that re-enter body content (papers commonly place these after refs).
_RESUME_SECTION_RE = re.compile(
    rf"^#{{1,3}}\s+{_LABEL_PREFIX}"
    r"(Appendix|Supplementary|Supplemental)\b",
    re.IGNORECASE,
)

# Bare appendix-style labels common in ML papers (e.g. "## A METHOD",
# "## C.1 ABLATION", "## H.2.1 NORMALIZATION") — single uppercase letter,
# optional dot-separated digit groups, then a section title. Case-sensitive
# so body prose like "## a few notes" does not trigger.
_RESUME_BARE_LABEL_RE = re.compile(r"^#{1,3}\s+[A-Z](?:\.\d+)*\.?\s+\S")

# Lines that look like page numbers or running headers/footers
_PAGE_NUM_RE = re.compile(r"^\s*\d+\s*$")
_HEADER_FOOTER_RE = re.compile(
    r"^\s*(Page\s+\d+|Running\s+Head:|©|\d{4}\s+\w+.{0,60}$)", re.IGNORECASE
)

_MIN_FOCUSED_CHARS = 200
_MIN_RATIO = 0.10


def build_focused(raw_md: str) -> str:
    """Strip references/acknowledgments tail and noisy header/footer lines.

    A heading matched by ``_DROP_SECTION_RE`` (refs/bib/acks/funding) starts a
    skip region; the next heading matched by ``_RESUME_SECTION_RE``
    (appendix/supplementary) ends it. This keeps appendix and supplementary
    content even when authors place those sections after references.
    """
    body_lines: list[str] = []
    skipping = False
    for line in raw_md.splitlines():
        if skipping:
            if _RESUME_SECTION_RE.match(line) or _RESUME_BARE_LABEL_RE.match(line):
                skipping = False
            else:
                continue
        elif _DROP_SECTION_RE.match(line):
            skipping = True
            continue
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
