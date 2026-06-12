import os
import shlex
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
MODELS_CONFIG = ROOT / "config" / "models.yaml"
CONFIG_HELPER = ROOT / "scripts" / "llama_server_config.py"


def _write_config(tmp_path: Path, llama_server: dict[str, object]) -> Path:
    config_path = tmp_path / "models.yaml"
    config_path.write_text(
        yaml.safe_dump({"vlm": {"llama_server": llama_server}}),
        encoding="utf-8",
    )
    return config_path


def _run_config_helper(
    config_path: Path,
    command: str,
    *,
    environment: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = {key: value for key, value in os.environ.items() if not key.startswith("LLAMA_")}
    env.update({"HOME": "/tmp/test-home", **(environment or {})})
    return subprocess.run(
        [sys.executable, str(CONFIG_HELPER), command, "--config", str(config_path)],
        check=False,
        capture_output=True,
        env=env,
        text=True,
    )


def _valid_llama_server_config() -> dict[str, object]:
    return {
        "base_url": "http://127.0.0.1:8080/v1",
        "model_path": "$HOME/models/model file.gguf",
        "mmproj_path": "$HOME/models/mmproj.gguf",
    }


def _parse_shell_assignments(output: str) -> dict[str, str]:
    assignments = {}
    for line in output.splitlines():
        key, value = shlex.split(line)[0].split("=", 1)
        assignments[key] = value
    return assignments


def test_llama_paths_are_home_relative_and_vision_is_configured():
    raw = yaml.safe_load(MODELS_CONFIG.read_text(encoding="utf-8"))
    config = raw["vlm"]["llama_server"]

    assert config["base_url"] == "http://127.0.0.1:8080/v1"
    assert config["model_id"] == "cosmos-reason2-8b"
    assert config["model_path"].startswith("$HOME/")
    assert config["mmproj_path"].startswith("$HOME/")
    assert "tuanhdangdinh" not in config["model_path"]
    assert "tuanhdangdinh" not in config["mmproj_path"]


def test_config_helper_expands_home_and_emits_shell_assignments(tmp_path):
    config_path = _write_config(tmp_path, _valid_llama_server_config())

    result = _run_config_helper(config_path, "shell")

    assert result.returncode == 0
    assert _parse_shell_assignments(result.stdout) == {
        "LLAMA_MODEL_PATH": "/tmp/test-home/models/model file.gguf",
        "LLAMA_MMPROJ_PATH": "/tmp/test-home/models/mmproj.gguf",
        "LLAMA_HOST": "127.0.0.1",
        "LLAMA_PORT": "8080",
        "LLAMA_CTX_SIZE": "4096",
        "LLAMA_GPU_LAYERS": "99",
    }


def test_config_helper_applies_environment_overrides(tmp_path):
    config_path = _write_config(tmp_path, _valid_llama_server_config())
    overrides = {
        "LLAMA_MODEL_PATH": "/models/override model.gguf",
        "LLAMA_MMPROJ_PATH": "/models/override-mmproj.gguf",
        "LLAMA_HOST": "0.0.0.0",
        "LLAMA_PORT": "8181",
        "LLAMA_CTX_SIZE": "8192",
        "LLAMA_GPU_LAYERS": "42",
    }

    result = _run_config_helper(config_path, "shell", environment=overrides)

    assert result.returncode == 0
    assert _parse_shell_assignments(result.stdout) == overrides


def test_config_helper_builds_health_url_from_effective_endpoint(tmp_path):
    config = _valid_llama_server_config()
    config["base_url"] = "http://localhost:9090/v1"
    config_path = _write_config(tmp_path, config)

    result = _run_config_helper(config_path, "health-url")

    assert result.returncode == 0
    assert result.stdout == "http://localhost:9090/health\n"


def test_config_helper_reports_missing_required_key(tmp_path):
    config = _valid_llama_server_config()
    del config["model_path"]
    config_path = _write_config(tmp_path, config)

    result = _run_config_helper(config_path, "shell")

    assert result.returncode == 2
    assert "vlm.llama_server.model_path" in result.stderr


def test_config_helper_rejects_invalid_numeric_override(tmp_path):
    config_path = _write_config(tmp_path, _valid_llama_server_config())

    result = _run_config_helper(
        config_path,
        "shell",
        environment={"LLAMA_PORT": "not-a-port"},
    )

    assert result.returncode == 2
    assert "LLAMA_PORT must be an integer" in result.stderr
