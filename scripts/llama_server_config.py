#!/usr/bin/env python3
"""Resolve llama-server settings from project YAML and environment overrides."""

from __future__ import annotations

import argparse
import os
import shlex
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import yaml


@dataclass(frozen=True)
class LlamaServerSettings:
    """Effective settings shared by startup and health-check scripts."""

    model_path: str
    mmproj_path: str
    host: str
    port: int
    ctx_size: int
    gpu_layers: int

    @property
    def health_url(self) -> str:
        """Return the llama-server health endpoint."""
        host = self.host
        if host == "0.0.0.0":
            host = "127.0.0.1"
        elif host in {"::", "[::]"}:
            host = "[::1]"
        if ":" in host and not host.startswith("["):
            host = f"[{host}]"
        return f"http://{host}:{self.port}/health"


def _required_string(config: dict[str, object], key: str) -> str:
    value = config.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"missing required config key: vlm.llama_server.{key}")
    return value


def _positive_int(name: str, value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if parsed <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return parsed


def _port(value: str) -> int:
    try:
        port = int(value)
    except ValueError as exc:
        raise ValueError("LLAMA_PORT must be an integer") from exc
    if not 1 <= port <= 65535:
        raise ValueError("LLAMA_PORT must be between 1 and 65535")
    return port


def load_settings(config_path: Path, environ: dict[str, str]) -> LlamaServerSettings:
    """Load YAML defaults and apply supported environment overrides.

    Args:
        config_path: Path to the project model configuration.
        environ: Environment variables used for expansion and overrides.

    Returns:
        Validated effective llama-server settings.

    Raises:
        ValueError: If the configuration or an override is invalid.
    """
    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"cannot read configuration {config_path}: {exc}") from exc

    try:
        config = raw["vlm"]["llama_server"]
    except (KeyError, TypeError) as exc:
        raise ValueError("missing required config section: vlm.llama_server") from exc
    if not isinstance(config, dict):
        raise ValueError("config section vlm.llama_server must be a mapping")

    base_url = _required_string(config, "base_url")
    parsed_url = urlparse(base_url)
    try:
        base_port = parsed_url.port
    except ValueError as exc:
        raise ValueError(
            "vlm.llama_server.base_url must include http host and port"
        ) from exc
    if parsed_url.scheme != "http" or parsed_url.hostname is None or base_port is None:
        raise ValueError("vlm.llama_server.base_url must include http host and port")

    home = environ.get("HOME")
    if not home:
        raise ValueError("HOME must be set to expand model paths")

    model_path = environ.get("LLAMA_MODEL_PATH") or _required_string(config, "model_path")
    mmproj_path = environ.get("LLAMA_MMPROJ_PATH") or _required_string(config, "mmproj_path")
    model_path = model_path.replace("$HOME", home)
    mmproj_path = mmproj_path.replace("$HOME", home)

    host = environ.get("LLAMA_HOST", parsed_url.hostname)
    if not host:
        raise ValueError("LLAMA_HOST must not be empty")
    port = _port(environ.get("LLAMA_PORT", str(base_port)))
    ctx_size = _positive_int("LLAMA_CTX_SIZE", environ.get("LLAMA_CTX_SIZE", "4096"))
    gpu_layers = _positive_int(
        "LLAMA_GPU_LAYERS",
        environ.get("LLAMA_GPU_LAYERS", "99"),
    )

    return LlamaServerSettings(
        model_path=model_path,
        mmproj_path=mmproj_path,
        host=host,
        port=port,
        ctx_size=ctx_size,
        gpu_layers=gpu_layers,
    )


def _shell_assignments(settings: LlamaServerSettings) -> str:
    values = {
        "LLAMA_MODEL_PATH": settings.model_path,
        "LLAMA_MMPROJ_PATH": settings.mmproj_path,
        "LLAMA_HOST": settings.host,
        "LLAMA_PORT": str(settings.port),
        "LLAMA_CTX_SIZE": str(settings.ctx_size),
        "LLAMA_GPU_LAYERS": str(settings.gpu_layers),
    }
    return "\n".join(f"{key}={shlex.quote(value)}" for key, value in values.items())


def main() -> int:
    """Run the configuration helper CLI.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("shell", "health-url"))
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args()

    try:
        settings = load_settings(args.config, dict(os.environ))
    except ValueError as exc:
        print(f"llama-server configuration error: {exc}", file=sys.stderr)
        return 2

    if args.command == "shell":
        print(_shell_assignments(settings))
    else:
        print(settings.health_url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
