"""Preflight health check for OCR backend endpoints."""

from __future__ import annotations

from dataclasses import dataclass

import requests

from tinta.backends import base_url


@dataclass(frozen=True)
class HealthResult:
    ok: bool
    message: str
    models: tuple[str, ...] = ()
    model_warning: str | None = None


def _health_url(api_url: str, api_mode: str) -> str:
    suffix = "/api/tags" if api_mode == "ollama_generate" else "/v1/models"
    return base_url(api_url) + suffix


def _parse_models(body: dict, api_mode: str) -> list[str]:
    if api_mode == "ollama_generate":
        return [m.get("name", "") for m in body.get("models", []) if m.get("name")]
    return [m.get("id", "") for m in body.get("data", []) if m.get("id")]


def preflight(
    *,
    api_url: str,
    api_mode: str,
    api_key: str | None = None,
    model: str | None = None,
    timeout: float = 5.0,
) -> HealthResult:
    """Verify the backend endpoint is reachable.

    Tiered semantics:
      - Reachability: failure -> ok=False (caller should abort).
      - Model presence: failure -> ok=True, model_warning set (caller proceeds).

    Skipped for MaaS (api_key set) since probing a public HTTPS endpoint
    is not meaningful.
    """
    if api_key:
        return HealthResult(ok=True, message="MaaS mode — skipping local probe")

    url = _health_url(api_url, api_mode)
    try:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
    except requests.exceptions.ConnectionError:
        hint = (
            "Start Ollama? Run 'ollama serve'."
            if api_mode == "ollama_generate"
            else "Is the inference server running?"
        )
        return HealthResult(ok=False, message=f"Cannot reach {url}. {hint}")
    except requests.exceptions.Timeout:
        return HealthResult(ok=False, message=f"Timeout reaching {url} after {timeout}s")
    except requests.exceptions.RequestException as e:
        return HealthResult(ok=False, message=f"{url} returned error: {e}")

    try:
        body = r.json()
    except ValueError:
        return HealthResult(
            ok=True,
            message=f"{url} reachable (non-JSON response, model list unavailable)",
        )

    models = _parse_models(body, api_mode)
    if model and models and model not in models:
        warning = (
            f"Model {model!r} not in advertised list {models}. "
            "Proceeding — server may be aliased or use --served-model-name."
        )
        return HealthResult(
            ok=True,
            message=f"{url} reachable ({len(models)} models)",
            models=tuple(models),
            model_warning=warning,
        )

    return HealthResult(
        ok=True,
        message=f"{url} reachable ({len(models)} models)",
        models=tuple(models),
    )
