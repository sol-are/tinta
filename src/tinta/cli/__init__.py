"""CLI application definition."""

from typer import Typer

app = Typer(help="Convert PDF files to clean Markdown using GLM-OCR.")

from tinta.cli import maas, selfhosted  # noqa: E402, F401  register subcommands
