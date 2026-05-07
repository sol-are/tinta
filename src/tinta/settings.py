"""Resolved settings: preset + env + CLI flags merged into one record."""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from typing import Optional

from tinta.backends import get as get_backend


_ENV_KEYS = {
    "backend": "TINTA_BACKEND",
    "max_workers": "TINTA_MAX_WORKERS",
    "request_timeout": "TINTA_REQUEST_TIMEOUT",
    "connect_timeout": "TINTA_CONNECT_TIMEOUT",
    "retry_max_attempts": "TINTA_RETRY_MAX_ATTEMPTS",
    "api_url": "TINTA_API_URL",
    "model": "TINTA_MODEL",
}


def _env_str(key: str) -> Optional[str]:
    return os.environ.get(key) or None


def _env_int(key: str) -> Optional[int]:
    v = _env_str(key)
    if v is None:
        return None
    try:
        return int(v)
    except ValueError as e:
        raise ValueError(f"{key}={v!r} is not an integer") from e


@dataclass
class Settings:
    """Merged config used to drive a single tinta invocation."""

    backend: Optional[str]
    api_url: Optional[str]
    api_mode: Optional[str]
    api_path: Optional[str]
    api_key: Optional[str]
    model: Optional[str]
    max_workers: Optional[int]
    request_timeout: Optional[int]
    connect_timeout: Optional[int]
    retry_max_attempts: Optional[int]

    @classmethod
    def resolve(
        cls,
        *,
        backend: Optional[str] = None,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_workers: Optional[int] = None,
        request_timeout: Optional[int] = None,
        connect_timeout: Optional[int] = None,
        retry_max_attempts: Optional[int] = None,
    ) -> "Settings":
        """Merge: explicit CLI flag > env var > preset default > SDK default.

        ``None`` from the caller means "not specified" — fall through.
        """
        backend_name = backend or _env_str(_ENV_KEYS["backend"])
        preset = get_backend(backend_name) if backend_name else None

        # api_key picks up legacy env vars that glmocr itself recognises
        resolved_api_key = (
            api_key
            or os.environ.get("GLMOCR_API_KEY")
            or os.environ.get("ZHIPU_API_KEY")
        )

        def pick(flag, env_key, preset_val, *, parser=None):
            if flag is not None:
                return flag
            env_val = (_env_int if parser is int else _env_str)(env_key)
            return env_val if env_val is not None else preset_val

        return cls(
            backend=backend_name,
            api_url=pick(api_url, _ENV_KEYS["api_url"], preset.api_url if preset else None),
            api_mode=preset.api_mode if preset else None,
            api_path=preset.api_path if preset else None,
            api_key=resolved_api_key,
            model=pick(model, _ENV_KEYS["model"], preset.model if preset else None),
            max_workers=pick(
                max_workers,
                _ENV_KEYS["max_workers"],
                preset.max_workers if preset else None,
                parser=int,
            ),
            request_timeout=pick(
                request_timeout,
                _ENV_KEYS["request_timeout"],
                preset.request_timeout if preset else None,
                parser=int,
            ),
            connect_timeout=pick(
                connect_timeout,
                _ENV_KEYS["connect_timeout"],
                preset.connect_timeout if preset else None,
                parser=int,
            ),
            retry_max_attempts=pick(
                retry_max_attempts, _ENV_KEYS["retry_max_attempts"], None, parser=int
            ),
        )

    def as_printable_dict(self) -> dict:
        d = asdict(self)
        if d.get("api_key"):
            d["api_key"] = "***redacted***"
        return d
