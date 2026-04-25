"""CLI application definition."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated, Optional

import typer

from tinta.backends import BACKENDS
from tinta.settings import Settings


def _run_preflight(settings: Settings) -> None:
    """Reachability=fail (raises Exit), model-presence=warn (returns)."""
    from tinta.batch import log
    from tinta.health import preflight

    result = preflight(
        api_url=settings.api_url,
        api_mode=settings.api_mode or "openai",
        api_key=settings.api_key,
        model=settings.model,
    )
    if not result.ok:
        log("preflight", result.message)
        raise typer.Exit(code=3)
    log("preflight", result.message)
    if result.model_warning:
        log("preflight", result.model_warning)


def main(
    inputs: Annotated[
        list[Path],
        typer.Argument(
            help="One or more PDF files or directories. Directories are recursed for *.pdf.",
        ),
    ],
    out_dir: Annotated[
        Path, typer.Option("--out-dir", "-o", help="Output directory.")
    ] = Path("./out"),
    backend: Annotated[
        Optional[str],
        typer.Option(
            "--backend",
            help=f"Backend preset: {', '.join(sorted(BACKENDS))}.",
        ),
    ] = None,
    md_only: Annotated[
        bool, typer.Option("--md-only", help="Output Markdown only (skip meta.json).")
    ] = False,
    skip_existing: Annotated[
        bool,
        typer.Option(
            "--skip-existing",
            help="Skip a PDF when its output dir already has the completion marker.",
        ),
    ] = False,
    max_pdf_time: Annotated[
        Optional[int],
        typer.Option(
            "--max-pdf-time",
            help="Per-PDF watchdog (seconds). Spawns a subprocess per PDF when set.",
        ),
    ] = None,
    max_workers: Annotated[
        Optional[int],
        typer.Option("--max-workers", help="Override pipeline.max_workers."),
    ] = None,
    request_timeout: Annotated[
        Optional[int],
        typer.Option("--request-timeout", help="Override OCR API request_timeout (seconds)."),
    ] = None,
    connect_timeout: Annotated[
        Optional[int],
        typer.Option("--connect-timeout", help="Override OCR API connect_timeout (seconds)."),
    ] = None,
    retry_max_attempts: Annotated[
        Optional[int],
        typer.Option("--retry-max-attempts", help="Override OCR API retry_max_attempts."),
    ] = None,
    api_url: Annotated[
        Optional[str], typer.Option("--api-url", "-u", help="API endpoint URL.")
    ] = None,
    api_key: Annotated[
        Optional[str],
        typer.Option("--api-key", "-k", help="API key (enables MaaS mode)."),
    ] = None,
    model: Annotated[
        Optional[str], typer.Option("--model", "-m", help="Model name for API requests.")
    ] = None,
    no_health_check: Annotated[
        bool,
        typer.Option("--no-health-check", help="Skip the preflight reachability check."),
    ] = False,
    print_config: Annotated[
        bool,
        typer.Option(
            "--print-config",
            help="Print resolved settings + the YAML the converter would use, then exit.",
        ),
    ] = False,
) -> None:
    """Convert PDFs to clean Markdown using GLM-OCR."""
    settings = Settings.resolve(
        backend=backend,
        api_url=api_url,
        api_key=api_key,
        model=model,
        max_workers=max_workers,
        request_timeout=request_timeout,
        connect_timeout=connect_timeout,
        retry_max_attempts=retry_max_attempts,
    )

    if print_config:
        from tinta.core.converter import render_config

        print(json.dumps(settings.as_printable_dict(), indent=2, ensure_ascii=False))
        print("--- merged glmocr config ---")
        print(render_config(settings))
        raise typer.Exit(code=0)

    if not no_health_check and settings.api_url:
        _run_preflight(settings)

    from tinta.batch import expand_inputs, log, run_batch

    try:
        pdfs = expand_inputs(inputs)
    except FileNotFoundError as e:
        log("input", str(e))
        raise typer.Exit(code=2)

    if not pdfs:
        log("input", "no PDF files found")
        raise typer.Exit(code=2)

    if (
        len(pdfs) > 1
        and (settings.api_mode or "") == "ollama_generate"
        and max_pdf_time is None
    ):
        log(
            "hint",
            "processing >1 PDF with Ollama and no --max-pdf-time. "
            "Recommend --max-pdf-time 1800 to avoid stuck-PDF stalls.",
        )

    result = run_batch(
        pdfs=pdfs,
        out_dir=out_dir,
        md_only=md_only,
        settings=settings,
        skip_existing=skip_existing,
        max_pdf_time=max_pdf_time,
    )
    if result.fail or result.timeout:
        raise typer.Exit(code=1)


app = typer.Typer()
app.command()(main)
