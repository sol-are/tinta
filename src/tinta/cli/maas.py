"""MaaS (API) mode subcommand."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import typer

from tinta.cli import app


@app.command()
def maas(
    pdf: Annotated[
        Path,
        typer.Argument(help="Path to the PDF file.", exists=True, readable=True),
    ],
    out_dir: Annotated[
        Path,
        typer.Option("--out-dir", "-o", help="Output directory."),
    ] = Path("./out"),
    md_only: Annotated[
        bool,
        typer.Option("--md-only", help="Output Markdown files only (skip meta.json)."),
    ] = False,
    api_key: Annotated[
        Optional[str],
        typer.Option("--api-key", help="API key for MaaS mode (or set GLMOCR_API_KEY)."),
    ] = None,
) -> None:
    """MaaS (API) モードで変換."""
    from tinta.core.pipeline import run

    run(pdf, out_dir, md_only, mode="maas", api_key=api_key)
