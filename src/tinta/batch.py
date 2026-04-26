"""Multi-PDF batch loop, with optional per-PDF watchdog and queue drain."""

from __future__ import annotations

import multiprocessing as mp
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from tinta.backends import BACKENDS
from tinta.settings import Settings


def log(tag: str, msg: str) -> None:
    """All status/progress goes to stderr; stdout is reserved for data."""
    print(f"[{tag}] {msg}", file=sys.stderr, flush=True)


@dataclass
class BatchResult:
    total: int
    ok: int
    skip: int
    fail: int
    timeout: int


def expand_inputs(inputs: Iterable[Path]) -> list[Path]:
    """File → as-is, dir → recursive *.pdf glob (sorted)."""
    pdfs: list[Path] = []
    for p in inputs:
        if p.is_dir():
            pdfs.extend(sorted(p.rglob("*.pdf")))
        elif p.is_file():
            pdfs.append(p)
        else:
            raise FileNotFoundError(f"{p} does not exist or is not readable")
    return pdfs


def _completion_marker(out_dir: Path, stem: str, no_artifacts: bool) -> Path:
    """write_outputs writes meta.json last in the default mode; in --no-artifacts
    mode <stem>.md is the only file written. Either is a strict-superset
    predicate vs. <stem>.md alone."""
    sub = out_dir / stem
    return sub / (f"{stem}.md" if no_artifacts else "meta.json")


def run_batch(
    pdfs: list[Path],
    out_dir: Path,
    no_artifacts: bool,
    *,
    settings: Settings,
    skip_existing: bool,
    max_pdf_time: int | None,
) -> BatchResult:
    """Process each PDF sequentially. Sub-processes only when watchdog set."""
    total = len(pdfs)
    ok = skip = fail = timeout = 0

    log("batch", f"total={total}")

    for i, pdf in enumerate(pdfs, start=1):
        prefix = f"{i}/{total}"

        if skip_existing and _completion_marker(out_dir, pdf.stem, no_artifacts).exists():
            skip += 1
            log(prefix, f"SKIP {pdf}")
            continue

        try:
            if max_pdf_time:
                _run_with_watchdog(pdf, out_dir, no_artifacts, settings, max_pdf_time)
            else:
                from tinta.core.pipeline import run_one

                run_one(pdf, out_dir, no_artifacts, settings=settings)
            ok += 1
            log(prefix, f"OK   {pdf}")
        except _PdfTimeout as e:
            timeout += 1
            log(prefix, f"TIMEOUT {pdf} ({e})")
            _drain_after_timeout(settings)
        except Exception as e:
            fail += 1
            log(prefix, f"FAIL {pdf}: {e}")

    log("batch", f"done total={total} ok={ok} skip={skip} fail={fail} timeout={timeout}")
    return BatchResult(total=total, ok=ok, skip=skip, fail=fail, timeout=timeout)


class _PdfTimeout(RuntimeError):
    pass


def _run_with_watchdog(
    pdf: Path, out_dir: Path, no_artifacts: bool, settings: Settings, timeout: int
) -> None:
    ctx = mp.get_context("spawn")
    p = ctx.Process(
        target=_pdf_worker,
        args=(str(pdf), str(out_dir), no_artifacts, settings),
    )
    p.start()
    p.join(timeout)
    if p.is_alive():
        p.terminate()
        p.join(5)
        if p.is_alive():
            p.kill()
            p.join()
        raise _PdfTimeout(f"exceeded {timeout}s")
    if p.exitcode != 0:
        raise RuntimeError(f"worker exited with code {p.exitcode}")


def _pdf_worker(pdf_str: str, out_str: str, no_artifacts: bool, settings: Settings) -> None:
    """Spawned subprocess body. Errors print to stderr and re-raise so the
    parent observes a non-zero exit code."""
    try:
        from tinta.core.pipeline import run_one

        run_one(Path(pdf_str), Path(out_str), no_artifacts, settings=settings)
    except BaseException as e:
        print(
            f"[worker] {type(e).__name__}: {e}\n{traceback.format_exc()}",
            file=sys.stderr,
            flush=True,
        )
        raise


def _drain_after_timeout(settings: Settings) -> None:
    preset = BACKENDS.get(settings.backend) if settings.backend else None
    if preset is None or preset.drainer is None:
        log("drain", f"no drainer for backend={settings.backend!r}")
        return
    ok, msg = preset.drainer(settings.api_url or preset.api_url, settings.model)
    log("drain" if ok else "drain-warn", msg)
