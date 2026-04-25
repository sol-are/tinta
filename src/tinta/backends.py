"""Backend presets for the OCR API endpoint.

Ports/paths are based on upstream defaults of each project:
  - Ollama 11434  (https://docs.ollama.com/faq)
  - vLLM 8000     (https://docs.vllm.ai/en/stable/cli/serve/)
  - SGLang 30000  (https://docs.sglang.io/advanced_features/server_arguments.html)
  - mlx_lm/mlx-vlm 8080 (mlx-lm SERVER.md)
  - llama.cpp 8080
  - LM Studio 1234
  - GLM-OCR upstream client port 8080 (api_port in glmocr/config.yaml)
  - MaaS https://open.bigmodel.cn

max_workers tuned per backend's concurrency model: Ollama / MLX serialize on
one model; vLLM / SGLang batch efficiently.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Optional
from urllib.parse import urlparse


def base_url(api_url: str) -> str:
    parsed = urlparse(api_url)
    return f"{parsed.scheme}://{parsed.netloc}"


@dataclass(frozen=True)
class BackendPreset:
    name: str
    api_url: str
    api_mode: str
    api_path: str
    model: Optional[str]
    max_workers: int
    request_timeout: int = 300
    health_url: str = ""
    requires_api_key: bool = False
    drainer: Optional[Callable[[str, Optional[str]], "tuple[bool, str]"]] = None


def _drain_ollama(
    api_url: str, model: Optional[str], *, cap_seconds: float = 30.0
) -> "tuple[bool, str]":
    """Evict the model and poll until Ollama reports it unloaded."""
    import requests

    base = base_url(api_url)
    target = model or "glm-ocr:latest"
    try:
        requests.post(
            f"{base}/api/generate",
            json={"model": target, "keep_alive": 0},
            timeout=10,
        )
    except requests.exceptions.RequestException as e:
        return False, f"drain POST failed: {e}"

    deadline = time.time() + cap_seconds
    while time.time() < deadline:
        try:
            r = requests.get(f"{base}/api/ps", timeout=5)
            r.raise_for_status()
            running = [m.get("name", "") for m in r.json().get("models", [])]
            if target not in running:
                return True, "drained"
        except requests.exceptions.RequestException:
            pass
        time.sleep(2)
    return False, f"model {target!r} still loaded after {cap_seconds}s"


BACKENDS: dict[str, BackendPreset] = {
    "ollama": BackendPreset(
        name="ollama",
        api_url="http://localhost:11434/api/generate",
        api_mode="ollama_generate",
        api_path="/api/generate",
        model="glm-ocr:latest",
        max_workers=4,
        health_url="http://localhost:11434/api/tags",
        drainer=_drain_ollama,
    ),
    "glm-ocr": BackendPreset(
        name="glm-ocr",
        api_url="http://localhost:8080/v1/chat/completions",
        api_mode="openai",
        api_path="/v1/chat/completions",
        model=None,
        max_workers=32,
        health_url="http://localhost:8080/v1/models",
    ),
    "vllm": BackendPreset(
        name="vllm",
        api_url="http://localhost:8000/v1/chat/completions",
        api_mode="openai",
        api_path="/v1/chat/completions",
        model=None,
        max_workers=32,
        health_url="http://localhost:8000/v1/models",
    ),
    "sglang": BackendPreset(
        name="sglang",
        api_url="http://localhost:30000/v1/chat/completions",
        api_mode="openai",
        api_path="/v1/chat/completions",
        model=None,
        max_workers=32,
        health_url="http://localhost:30000/v1/models",
    ),
    "mlx": BackendPreset(
        name="mlx",
        api_url="http://localhost:8080/v1/chat/completions",
        api_mode="openai",
        api_path="/v1/chat/completions",
        model=None,
        max_workers=2,
        health_url="http://localhost:8080/v1/models",
    ),
    "llama-cpp": BackendPreset(
        name="llama-cpp",
        api_url="http://localhost:8080/v1/chat/completions",
        api_mode="openai",
        api_path="/v1/chat/completions",
        model=None,
        max_workers=4,
        health_url="http://localhost:8080/v1/models",
    ),
    "lmstudio": BackendPreset(
        name="lmstudio",
        api_url="http://localhost:1234/v1/chat/completions",
        api_mode="openai",
        api_path="/v1/chat/completions",
        model=None,
        max_workers=4,
        health_url="http://localhost:1234/v1/models",
    ),
    "maas": BackendPreset(
        name="maas",
        api_url="https://open.bigmodel.cn/api/paas/v4/layout_parsing",
        api_mode="openai",
        api_path="/api/paas/v4/layout_parsing",
        model="glm-ocr",
        max_workers=8,
        health_url="",
        requires_api_key=True,
    ),
}


def get(name: str) -> BackendPreset:
    if name not in BACKENDS:
        raise KeyError(
            f"Unknown backend {name!r}. Available: {sorted(BACKENDS)}"
        )
    return BACKENDS[name]
