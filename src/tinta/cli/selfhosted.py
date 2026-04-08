"""Self-hosted mode subcommand."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import typer

from tinta.cli import app


@app.command()
def selfhosted(
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
    api_url: Annotated[
        Optional[str],
        typer.Option("--api-url", help="API URL for self-hosted mode."),
    ] = None,
    model: Annotated[
        Optional[str],
        typer.Option("--model", help="Model name for API requests."),
    ] = None,
) -> None:
    """セルフホストモードで変換."""
    from tinta.core.pipeline import run

    run(pdf, out_dir, md_only, mode="selfhosted", api_url=api_url, model=model)
