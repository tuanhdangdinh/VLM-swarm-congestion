# Local Llama Server Setup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a repeatable foreground command that starts the existing Cosmos Reason2 GGUF model with its multimodal projector through `llama-server` on Apple Silicon.

**Architecture:** Keep `config/models.yaml` as the source of local model and endpoint defaults. A focused Python helper will parse YAML, expand paths, apply environment overrides, and expose resolved values to two thin shell entry points: one starts `llama-server`, and one checks `/health`. Pytest subprocess tests will use temporary project fixtures and fake executables so verification never loads the 7.4 GB model.

**Tech Stack:** Bash 3.2-compatible shell, Python 3.10+, PyYAML, pytest, llama.cpp `llama-server`, Make

---

## File Structure

| File | Responsibility |
|---|---|
| `config/models.yaml` | Portable default endpoint, model path, and projector path |
| `scripts/llama_server_config.py` | Parse and validate Llama server configuration; emit shell assignments or health URL |
| `scripts/start_llama_server_apple_silicon.sh` | Validate Apple Silicon/runtime prerequisites and `exec` the foreground server |
| `scripts/check_llama_server.sh` | Resolve the configured endpoint and query `/health` |
| `tests/unit/test_llama_server_scripts.py` | Unit and subprocess coverage for configuration, launch arguments, and health behavior |
| `Makefile` | Stable developer commands for starting and checking the server |
| `docs/guides/run_local_llama_server.md` | Installation, startup, override, backend activation, and smoke-test guide |
| `README.md` | Link the local Llama workflow from Quick Start |
| `docs/guides/hardware_setup.md` | Clarify Apple Silicon as the local development VLM host option |

## Task 1: Make Model Configuration Portable

**Files:**
- Modify: `config/models.yaml:10-14`
- Create: `tests/unit/test_llama_server_scripts.py`

- [ ] **Step 1: Write the failing portable-configuration test**

Create `tests/unit/test_llama_server_scripts.py`:

```python
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
MODELS_CONFIG = ROOT / "config" / "models.yaml"


def test_llama_paths_are_home_relative_and_vision_is_configured():
    raw = yaml.safe_load(MODELS_CONFIG.read_text(encoding="utf-8"))
    config = raw["vlm"]["llama_server"]

    assert config["base_url"] == "http://127.0.0.1:8080/v1"
    assert config["model_id"] == "cosmos-reason2-8b"
    assert config["model_path"].startswith("$HOME/")
    assert config["mmproj_path"].startswith("$HOME/")
    assert "tuanhdangdinh" not in config["model_path"]
    assert "tuanhdangdinh" not in config["mmproj_path"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
pytest tests/unit/test_llama_server_scripts.py::test_llama_paths_are_home_relative_and_vision_is_configured -v
```

Expected: FAIL because both checked-in paths start with `/Users/tuanhdangdinh`.

- [ ] **Step 3: Replace username-specific paths**

Change `config/models.yaml` to:

```yaml
  llama_server:
    base_url: "http://127.0.0.1:8080/v1"
    model_id: cosmos-reason2-8b
    model_path: "$HOME/.cache/lm-studio/models/DevQuasar/nvidia.Cosmos-Reason2-8B-GGUF/nvidia.Cosmos-Reason2-8B.f16.gguf.Q6_K.gguf"
    mmproj_path: "$HOME/.cache/lm-studio/models/DevQuasar/nvidia.Cosmos-Reason2-8B-GGUF/mmproj-nvidia.Cosmos-Reason2-8B.f16.gguf"
```

Keep `vlm.reasoner.backend_id` set to `mock`.

- [ ] **Step 4: Run the test to verify it passes**

Run:

```bash
pytest tests/unit/test_llama_server_scripts.py::test_llama_paths_are_home_relative_and_vision_is_configured -v
```

Expected: PASS.

- [ ] **Step 5: Commit the portable configuration**

```bash
git add config/models.yaml tests/unit/test_llama_server_scripts.py
git commit -m "config: make llama model paths portable"
```

## Task 2: Add the Shared Configuration Resolver

**Files:**
- Create: `scripts/llama_server_config.py`
- Modify: `tests/unit/test_llama_server_scripts.py`

- [ ] **Step 1: Add failing resolver tests**

Replace the test file's import block with the following ordered imports, then
append the resolver helpers and tests after
`test_llama_paths_are_home_relative_and_vision_is_configured`:

```python
import os
import subprocess
import sys
from pathlib import Path

import yaml
```

```python
CONFIG_HELPER = ROOT / "scripts" / "llama_server_config.py"


def _run_config_helper(
    config_path: Path,
    command: str = "shell",
    *,
    env_overrides: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["HOME"] = "/tmp/test-home"
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        [sys.executable, str(CONFIG_HELPER), command, "--config", str(config_path)],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )


def _write_models_config(path: Path) -> None:
    path.write_text(
        """
vlm:
  llama_server:
    base_url: "http://127.0.0.1:8080/v1"
    model_id: cosmos-reason2-8b
    model_path: "$HOME/models/cosmos model.gguf"
    mmproj_path: "$HOME/models/mmproj.gguf"
""".lstrip(),
        encoding="utf-8",
    )


def test_config_helper_expands_home_and_emits_shell_assignments(tmp_path):
    config_path = tmp_path / "models.yaml"
    _write_models_config(config_path)

    result = _run_config_helper(config_path)

    assert result.returncode == 0
    assert "LLAMA_MODEL_PATH='/tmp/test-home/models/cosmos model.gguf'" in result.stdout
    assert "LLAMA_MMPROJ_PATH=/tmp/test-home/models/mmproj.gguf" in result.stdout
    assert "LLAMA_HOST=127.0.0.1" in result.stdout
    assert "LLAMA_PORT=8080" in result.stdout
    assert "LLAMA_CTX_SIZE=4096" in result.stdout
    assert "LLAMA_GPU_LAYERS=99" in result.stdout


def test_config_helper_applies_environment_overrides(tmp_path):
    config_path = tmp_path / "models.yaml"
    _write_models_config(config_path)

    result = _run_config_helper(
        config_path,
        env_overrides={
            "LLAMA_MODEL_PATH": "/override/model.gguf",
            "LLAMA_MMPROJ_PATH": "/override/mmproj.gguf",
            "LLAMA_HOST": "0.0.0.0",
            "LLAMA_PORT": "9090",
            "LLAMA_CTX_SIZE": "8192",
            "LLAMA_GPU_LAYERS": "42",
        },
    )

    assert result.returncode == 0
    assert "LLAMA_MODEL_PATH=/override/model.gguf" in result.stdout
    assert "LLAMA_MMPROJ_PATH=/override/mmproj.gguf" in result.stdout
    assert "LLAMA_HOST=0.0.0.0" in result.stdout
    assert "LLAMA_PORT=9090" in result.stdout
    assert "LLAMA_CTX_SIZE=8192" in result.stdout
    assert "LLAMA_GPU_LAYERS=42" in result.stdout


def test_config_helper_builds_health_url_from_effective_endpoint(tmp_path):
    config_path = tmp_path / "models.yaml"
    _write_models_config(config_path)

    result = _run_config_helper(
        config_path,
        command="health-url",
        env_overrides={"LLAMA_HOST": "localhost", "LLAMA_PORT": "9090"},
    )

    assert result.returncode == 0
    assert result.stdout.strip() == "http://localhost:9090/health"


def test_config_helper_reports_missing_required_key(tmp_path):
    config_path = tmp_path / "models.yaml"
    config_path.write_text("vlm: {llama_server: {base_url: http://localhost:8080/v1}}")

    result = _run_config_helper(config_path)

    assert result.returncode == 2
    assert "vlm.llama_server.model_path" in result.stderr


def test_config_helper_rejects_invalid_numeric_override(tmp_path):
    config_path = tmp_path / "models.yaml"
    _write_models_config(config_path)

    result = _run_config_helper(
        config_path,
        env_overrides={"LLAMA_PORT": "not-a-port"},
    )

    assert result.returncode == 2
    assert "LLAMA_PORT must be an integer" in result.stderr
```

- [ ] **Step 2: Run resolver tests to verify they fail**

Run:

```bash
pytest tests/unit/test_llama_server_scripts.py -k "config_helper" -v
```

Expected: five FAIL results because `scripts/llama_server_config.py` does not exist.

- [ ] **Step 3: Implement the configuration resolver**

Create `scripts/llama_server_config.py`:

```python
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
        return f"http://{self.host}:{self.port}/health"


def _required_string(config: dict, key: str) -> str:
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


def load_settings(config_path: Path, environ: dict[str, str]) -> LlamaServerSettings:
    """Load YAML defaults and apply supported environment overrides."""
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
    if (
        parsed_url.scheme != "http"
        or parsed_url.hostname is None
        or parsed_url.port is None
    ):
        raise ValueError("vlm.llama_server.base_url must include http host and port")

    home = environ.get("HOME")
    if not home:
        raise ValueError("HOME must be set to expand model paths")

    model_path = environ.get("LLAMA_MODEL_PATH") or _required_string(
        config,
        "model_path",
    )
    mmproj_path = environ.get("LLAMA_MMPROJ_PATH") or _required_string(
        config,
        "mmproj_path",
    )
    model_path = model_path.replace("$HOME", home)
    mmproj_path = mmproj_path.replace("$HOME", home)

    host = environ.get("LLAMA_HOST", parsed_url.hostname)
    port = _positive_int("LLAMA_PORT", environ.get("LLAMA_PORT", str(parsed_url.port)))
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
    """Run the configuration helper CLI."""
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
```

- [ ] **Step 4: Run resolver tests to verify they pass**

Run:

```bash
pytest tests/unit/test_llama_server_scripts.py -k "config_helper" -v
```

Expected: five PASS results.

- [ ] **Step 5: Lint the helper and tests**

Run:

```bash
ruff check scripts/llama_server_config.py tests/unit/test_llama_server_scripts.py
```

Expected: PASS with no diagnostics.

- [ ] **Step 6: Commit the shared resolver**

```bash
git add scripts/llama_server_config.py tests/unit/test_llama_server_scripts.py
git commit -m "feat: resolve llama server configuration"
```

## Task 3: Build the Apple Silicon Foreground Launcher

**Files:**
- Modify: `scripts/start_llama_server_apple_silicon.sh:1-56`
- Modify: `tests/unit/test_llama_server_scripts.py`

- [ ] **Step 1: Add subprocess fixture helpers and failing launcher tests**

Add `shutil` to the existing standard-library import block:

```python
import os
import shutil
import subprocess
import sys
from pathlib import Path

import yaml
```

Then append the fixture helpers and launcher tests:

```python

START_SCRIPT = ROOT / "scripts" / "start_llama_server_apple_silicon.sh"


def _make_script_project(tmp_path: Path) -> tuple[Path, Path, Path]:
    project = tmp_path / "project"
    scripts_dir = project / "scripts"
    config_dir = project / "config"
    bin_dir = tmp_path / "bin"
    scripts_dir.mkdir(parents=True)
    config_dir.mkdir()
    bin_dir.mkdir()
    (bin_dir / "dirname").symlink_to("/usr/bin/dirname")
    (bin_dir / "python3").symlink_to(sys.executable)

    shutil.copy2(START_SCRIPT, scripts_dir / START_SCRIPT.name)
    shutil.copy2(CONFIG_HELPER, scripts_dir / CONFIG_HELPER.name)
    config_path = config_dir / "models.yaml"
    _write_models_config(config_path)

    model_path = tmp_path / "home" / "models" / "cosmos model.gguf"
    mmproj_path = tmp_path / "home" / "models" / "mmproj.gguf"
    model_path.parent.mkdir(parents=True)
    model_path.touch()
    mmproj_path.touch()

    return project, bin_dir, tmp_path / "home"


def _write_executable(path: Path, body: str) -> None:
    path.write_text(f"#!/bin/bash\nset -e\n{body}\n", encoding="utf-8")
    path.chmod(0o755)


def _run_start_script(
    project: Path,
    bin_dir: Path,
    home: Path,
    *,
    env_overrides: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        {
            "HOME": str(home),
            "PATH": f"{bin_dir}:{os.environ['PATH']}",
            "LLAMA_DRY_RUN": "1",
        }
    )
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        ["/bin/bash", str(project / "scripts" / START_SCRIPT.name)],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )


def test_start_script_dry_run_contains_vision_and_metal_arguments(tmp_path):
    project, bin_dir, home = _make_script_project(tmp_path)
    _write_executable(
        bin_dir / "uname",
        'if [ "${1:-}" = "-s" ]; then echo Darwin; else echo arm64; fi',
    )
    _write_executable(
        bin_dir / "llama-server",
        'echo "server must not run in dry-run mode"',
    )

    result = _run_start_script(project, bin_dir, home)

    assert result.returncode == 0
    assert "llama-server" in result.stdout
    assert f"-m {home}/models/cosmos\\ model.gguf" in result.stdout
    assert f"--mmproj {home}/models/mmproj.gguf" in result.stdout
    assert "--host 127.0.0.1" in result.stdout
    assert "--port 8080" in result.stdout
    assert "--ctx-size 4096" in result.stdout
    assert "-ngl 99" in result.stdout
    assert "--log-format text" in result.stdout
    assert "server must not run" not in result.stdout


def test_start_script_honors_launch_overrides(tmp_path):
    project, bin_dir, home = _make_script_project(tmp_path)
    _write_executable(
        bin_dir / "uname",
        'if [ "${1:-}" = "-s" ]; then echo Darwin; else echo arm64; fi',
    )
    _write_executable(bin_dir / "llama-server", "exit 99")

    result = _run_start_script(
        project,
        bin_dir,
        home,
        env_overrides={
            "LLAMA_HOST": "0.0.0.0",
            "LLAMA_PORT": "9090",
            "LLAMA_CTX_SIZE": "8192",
            "LLAMA_GPU_LAYERS": "42",
        },
    )

    assert result.returncode == 0
    assert "--host 0.0.0.0" in result.stdout
    assert "--port 9090" in result.stdout
    assert "--ctx-size 8192" in result.stdout
    assert "-ngl 42" in result.stdout


def test_start_script_rejects_non_apple_silicon(tmp_path):
    project, bin_dir, home = _make_script_project(tmp_path)
    _write_executable(
        bin_dir / "uname",
        'if [ "${1:-}" = "-s" ]; then echo Linux; else echo x86_64; fi',
    )
    _write_executable(bin_dir / "llama-server", "exit 99")

    result = _run_start_script(project, bin_dir, home)

    assert result.returncode == 1
    assert "requires macOS on Apple Silicon" in result.stderr


def test_start_script_reports_missing_llama_server(tmp_path):
    project, bin_dir, home = _make_script_project(tmp_path)
    _write_executable(
        bin_dir / "uname",
        'if [ "${1:-}" = "-s" ]; then echo Darwin; else echo arm64; fi',
    )

    result = _run_start_script(
        project,
        bin_dir,
        home,
        env_overrides={"PATH": str(bin_dir)},
    )

    assert result.returncode == 1
    assert "brew install llama.cpp" in result.stderr


def test_start_script_reports_missing_python(tmp_path):
    project, bin_dir, home = _make_script_project(tmp_path)
    (bin_dir / "python3").unlink()
    _write_executable(
        bin_dir / "uname",
        'if [ "${1:-}" = "-s" ]; then echo Darwin; else echo arm64; fi',
    )
    _write_executable(bin_dir / "llama-server", "exit 99")

    result = _run_start_script(
        project,
        bin_dir,
        home,
        env_overrides={"PATH": str(bin_dir)},
    )

    assert result.returncode == 1
    assert "Python 3 is required" in result.stderr


def test_start_script_reports_missing_pyyaml(tmp_path):
    project, bin_dir, home = _make_script_project(tmp_path)
    (bin_dir / "python3").unlink()
    _write_executable(bin_dir / "python3", 'exit 1')
    _write_executable(
        bin_dir / "uname",
        'if [ "${1:-}" = "-s" ]; then echo Darwin; else echo arm64; fi',
    )
    _write_executable(bin_dir / "llama-server", "exit 99")

    result = _run_start_script(project, bin_dir, home)

    assert result.returncode == 1
    assert "PyYAML is required" in result.stderr


def test_start_script_requires_model_file(tmp_path):
    project, bin_dir, home = _make_script_project(tmp_path)
    (home / "models" / "cosmos model.gguf").unlink()
    _write_executable(
        bin_dir / "uname",
        'if [ "${1:-}" = "-s" ]; then echo Darwin; else echo arm64; fi',
    )
    _write_executable(bin_dir / "llama-server", "exit 99")

    result = _run_start_script(project, bin_dir, home)

    assert result.returncode == 1
    assert f"model not found: {home}/models/cosmos model.gguf" in result.stderr


def test_start_script_requires_mmproj_for_vision(tmp_path):
    project, bin_dir, home = _make_script_project(tmp_path)
    (home / "models" / "mmproj.gguf").unlink()
    _write_executable(
        bin_dir / "uname",
        'if [ "${1:-}" = "-s" ]; then echo Darwin; else echo arm64; fi',
    )
    _write_executable(bin_dir / "llama-server", "exit 99")

    result = _run_start_script(project, bin_dir, home)

    assert result.returncode == 1
    assert (
        f"multimodal projector not found: {home}/models/mmproj.gguf"
        in result.stderr
    )
```

- [ ] **Step 2: Run launcher tests to verify they fail**

Run:

```bash
pytest tests/unit/test_llama_server_scripts.py -k "start_script" -v
```

Expected: FAIL because the existing script ignores project YAML and dry-run mode, uses different paths, and falls back to text-only mode.

- [ ] **Step 3: Replace the launcher with strict foreground behavior**

Replace `scripts/start_llama_server_apple_silicon.sh` with:

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG_PATH="$ROOT_DIR/config/models.yaml"

if [ "$(uname -s)" != "Darwin" ] || [ "$(uname -m)" != "arm64" ]; then
    echo "error: this launcher requires macOS on Apple Silicon" >&2
    exit 1
fi

if [ -x "$ROOT_DIR/.venv/bin/python" ]; then
    PYTHON="$ROOT_DIR/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON="$(command -v python3)"
else
    echo "error: Python 3 is required; run scripts/setup_codespace.sh" >&2
    exit 1
fi

if ! "$PYTHON" -c "import yaml" >/dev/null 2>&1; then
    echo "error: PyYAML is required; run scripts/setup_codespace.sh" >&2
    exit 1
fi

if ! command -v llama-server >/dev/null 2>&1; then
    echo "error: llama-server is not installed; run: brew install llama.cpp" >&2
    exit 1
fi

if ! RESOLVED_CONFIG="$(
    "$PYTHON" "$SCRIPT_DIR/llama_server_config.py" shell --config "$CONFIG_PATH"
)"; then
    exit 1
fi
eval "$RESOLVED_CONFIG"

if [ ! -r "$LLAMA_MODEL_PATH" ]; then
    echo "error: model not found: $LLAMA_MODEL_PATH" >&2
    exit 1
fi
if [ ! -r "$LLAMA_MMPROJ_PATH" ]; then
    echo "error: multimodal projector not found: $LLAMA_MMPROJ_PATH" >&2
    exit 1
fi

COMMAND=(
    llama-server
    -m "$LLAMA_MODEL_PATH"
    --mmproj "$LLAMA_MMPROJ_PATH"
    --host "$LLAMA_HOST"
    --port "$LLAMA_PORT"
    --ctx-size "$LLAMA_CTX_SIZE"
    -ngl "$LLAMA_GPU_LAYERS"
    --log-format text
)

echo "Starting Cosmos Reason2 with vision on http://$LLAMA_HOST:$LLAMA_PORT/v1"
printf 'Command:'
printf ' %q' "${COMMAND[@]}"
printf '\n'

if [ "${LLAMA_DRY_RUN:-0}" = "1" ]; then
    exit 0
fi

exec "${COMMAND[@]}"
```

Use ASCII-only output and retain `#!/usr/bin/env bash` plus `set -euo pipefail`.

- [ ] **Step 4: Run launcher tests to verify they pass**

Run:

```bash
pytest tests/unit/test_llama_server_scripts.py -k "start_script" -v
```

Expected: eight PASS results.

- [ ] **Step 5: Check shell syntax**

Run:

```bash
bash -n scripts/start_llama_server_apple_silicon.sh
```

Expected: exit code 0 with no output.

- [ ] **Step 6: Verify the real configured launch command without loading the model**

Run:

```bash
LLAMA_DRY_RUN=1 ./scripts/start_llama_server_apple_silicon.sh
```

Expected: exit code 0; output includes the existing LM Studio model, the existing `mmproj`, `--host 127.0.0.1`, `--port 8080`, `--ctx-size 4096`, and `-ngl 99`.

- [ ] **Step 7: Commit the launcher**

```bash
git add scripts/start_llama_server_apple_silicon.sh tests/unit/test_llama_server_scripts.py
git commit -m "feat: add apple silicon llama launcher"
```

## Task 4: Add Health Check and Make Targets

**Files:**
- Create: `scripts/check_llama_server.sh`
- Modify: `Makefile:1-25`
- Modify: `tests/unit/test_llama_server_scripts.py`

- [ ] **Step 1: Add failing health-check tests**

Append to `tests/unit/test_llama_server_scripts.py`:

```python
CHECK_SCRIPT = ROOT / "scripts" / "check_llama_server.sh"


def _prepare_check_script(project: Path) -> None:
    shutil.copy2(CHECK_SCRIPT, project / "scripts" / CHECK_SCRIPT.name)


def _run_check_script(
    project: Path,
    bin_dir: Path,
    home: Path,
    *,
    env_overrides: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update({"HOME": str(home), "PATH": f"{bin_dir}:{os.environ['PATH']}"})
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        ["/bin/bash", str(project / "scripts" / CHECK_SCRIPT.name)],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )


def test_check_script_reports_ready_and_uses_effective_url(tmp_path):
    project, bin_dir, home = _make_script_project(tmp_path)
    _prepare_check_script(project)
    _write_executable(
        bin_dir / "curl",
        """
printf '%s' "$*" > "$CURL_ARGS_FILE"
printf '{"status":"ok"}'
""".strip(),
    )
    args_file = tmp_path / "curl-args.txt"

    result = _run_check_script(
        project,
        bin_dir,
        home,
        env_overrides={
            "CURL_ARGS_FILE": str(args_file),
            "LLAMA_HOST": "localhost",
            "LLAMA_PORT": "9090",
        },
    )

    assert result.returncode == 0
    assert "llama-server ready: http://localhost:9090/health" in result.stdout
    assert "http://localhost:9090/health" in args_file.read_text(encoding="utf-8")


def test_check_script_reports_not_ready_when_curl_fails(tmp_path):
    project, bin_dir, home = _make_script_project(tmp_path)
    _prepare_check_script(project)
    _write_executable(bin_dir / "curl", "exit 7")

    result = _run_check_script(project, bin_dir, home)

    assert result.returncode == 1
    assert "llama-server not ready: http://127.0.0.1:8080/health" in result.stderr
```

- [ ] **Step 2: Run health-check tests to verify they fail**

Run:

```bash
pytest tests/unit/test_llama_server_scripts.py -k "check_script" -v
```

Expected: two FAIL results because `scripts/check_llama_server.sh` does not exist.

- [ ] **Step 3: Implement the health-check script**

Create `scripts/check_llama_server.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG_PATH="$ROOT_DIR/config/models.yaml"

if [ -x "$ROOT_DIR/.venv/bin/python" ]; then
    PYTHON="$ROOT_DIR/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON="$(command -v python3)"
else
    echo "error: Python 3 is required; run scripts/setup_codespace.sh" >&2
    exit 1
fi

if ! "$PYTHON" -c "import yaml" >/dev/null 2>&1; then
    echo "error: PyYAML is required; run scripts/setup_codespace.sh" >&2
    exit 1
fi

HEALTH_URL="$("$PYTHON" "$SCRIPT_DIR/llama_server_config.py" health-url --config "$CONFIG_PATH")"

if curl --fail --silent --show-error --max-time 5 "$HEALTH_URL" >/dev/null; then
    echo "llama-server ready: $HEALTH_URL"
    exit 0
fi

echo "llama-server not ready: $HEALTH_URL" >&2
exit 1
```

Make both entry points executable:

```bash
chmod +x scripts/start_llama_server_apple_silicon.sh scripts/check_llama_server.sh
```

- [ ] **Step 4: Run health-check tests to verify they pass**

Run:

```bash
pytest tests/unit/test_llama_server_scripts.py -k "check_script" -v
```

Expected: two PASS results.

- [ ] **Step 5: Add Make targets**

Change the `.PHONY` declaration and append targets in `Makefile`:

```make
.PHONY: test lint build-ros2 run-perception run-simulation run-orchestrator index-rag run-llama-server check-llama-server

run-llama-server:
	./scripts/start_llama_server_apple_silicon.sh

check-llama-server:
	./scripts/check_llama_server.sh
```

- [ ] **Step 6: Verify Make invokes the dry-run launcher**

Run:

```bash
LLAMA_DRY_RUN=1 make run-llama-server
```

Expected: exit code 0 and the same resolved command printed by the direct dry run.

- [ ] **Step 7: Check shell syntax and Make target visibility**

Run:

```bash
bash -n scripts/check_llama_server.sh
make -n run-llama-server check-llama-server
```

Expected: shell syntax exits 0; Make prints both script commands without executing them.

- [ ] **Step 8: Commit health and Make commands**

```bash
git add scripts/check_llama_server.sh Makefile tests/unit/test_llama_server_scripts.py
git commit -m "feat: add llama server health command"
```

## Task 5: Document the Local Vision Server Workflow

**Files:**
- Create: `docs/guides/run_local_llama_server.md`
- Modify: `README.md:16-30`
- Modify: `docs/guides/hardware_setup.md:135-150`

- [ ] **Step 1: Create the focused run guide**

Create `docs/guides/run_local_llama_server.md`:

````markdown
# Run Cosmos Reason2 Locally on Apple Silicon

This guide starts the project's NVIDIA Cosmos Reason2 GGUF model through
llama.cpp's OpenAI-compatible server. The server runs in the foreground and
loads the multimodal projector so M2 can submit annotated camera frames.

## Prerequisites

- Apple Silicon Mac
- Homebrew
- Python project environment from the repository Quick Start
- Cosmos Reason2 model and matching `mmproj` at the paths configured in
  `config/models.yaml`

Install llama.cpp:

```bash
brew install llama.cpp
```

The checked-in defaults point to the existing LM Studio cache beneath
`$HOME/.cache/lm-studio/models/DevQuasar/`.

## Start the server

From the repository root:

```bash
make run-llama-server
```

The process stays in the foreground and listens at
`http://127.0.0.1:8080/v1`. Stop it with `Ctrl-C`.

In another terminal, verify readiness:

```bash
make check-llama-server
```

## Override local settings

The launcher accepts environment overrides without editing checked-in files:

```bash
LLAMA_MODEL_PATH=/path/to/model.gguf \
LLAMA_MMPROJ_PATH=/path/to/mmproj.gguf \
LLAMA_PORT=9090 \
make run-llama-server
```

Supported variables are `LLAMA_MODEL_PATH`, `LLAMA_MMPROJ_PATH`, `LLAMA_HOST`,
`LLAMA_PORT`, `LLAMA_CTX_SIZE`, and `LLAMA_GPU_LAYERS`.

Inspect the final launch command without loading the model:

```bash
LLAMA_DRY_RUN=1 make run-llama-server
```

## Enable live inference

The project defaults to the offline mock backend. For a live run, change
`config/models.yaml`:

```yaml
vlm:
  reasoner:
    backend_id: llama_server
```

Keep the server running while invoking M2 or the orchestrator. Restore
`backend_id: mock` for offline tests.

## Manual smoke test

After the model finishes loading:

```bash
curl --fail http://127.0.0.1:8080/health
python -c \
  'from reasoning.vlm import LlamaServerBackend; print(LlamaServerBackend().is_ready())'
```

Expected results are a successful health response and `True`.

If startup reports a missing model or projector, either place the files at the
configured `$HOME`-relative paths or provide the two path overrides shown
above. Vision mode is required; the launcher does not fall back to text-only
operation.
````

- [ ] **Step 2: Link the guide from README**

Append after the Python Quick Start block in `README.md`:

````markdown
## Local VLM Server

On Apple Silicon, run Cosmos Reason2 with vision support:

```bash
make run-llama-server
```

See [Run Cosmos Reason2 Locally on Apple Silicon](docs/guides/run_local_llama_server.md)
for prerequisites, health checks, overrides, and live-backend configuration.
````

- [ ] **Step 3: Clarify the hardware guide**

Insert after `docs/guides/hardware_setup.md:150`:

```markdown
For local development, the checked-in launcher also supports an Apple Silicon
Mac through llama.cpp Metal acceleration. It loads both the Cosmos GGUF and its
multimodal projector in the foreground. See
[`run_local_llama_server.md`](run_local_llama_server.md). The NVIDIA
recommendations above remain the target for dedicated deployment hardware.
```

- [ ] **Step 4: Check documentation references**

Run:

```bash
test -f docs/guides/run_local_llama_server.md
rg -n "run_local_llama_server|run-llama-server|backend_id: llama_server" \
  README.md docs/guides/run_local_llama_server.md docs/guides/hardware_setup.md
```

Expected: references appear in all three documentation files.

- [ ] **Step 5: Commit documentation**

```bash
git add README.md docs/guides/run_local_llama_server.md docs/guides/hardware_setup.md
git commit -m "docs: explain local llama vision server"
```

## Task 6: Run Full Verification

**Files:**
- Verify: `config/models.yaml`
- Verify: `scripts/llama_server_config.py`
- Verify: `scripts/start_llama_server_apple_silicon.sh`
- Verify: `scripts/check_llama_server.sh`
- Verify: `tests/unit/test_llama_server_scripts.py`
- Verify: `Makefile`
- Verify: `README.md`
- Verify: `docs/guides/run_local_llama_server.md`
- Verify: `docs/guides/hardware_setup.md`

- [ ] **Step 1: Run focused tests**

Run:

```bash
pytest tests/unit/test_llama_server_scripts.py -v
```

Expected: all tests PASS.

- [ ] **Step 2: Run existing VLM tests**

Run:

```bash
pytest tests/unit/test_reasoner.py -v
```

Expected: all tests PASS; the mock backend remains the default and no live server is required.

- [ ] **Step 3: Run lint**

Run:

```bash
ruff check scripts/llama_server_config.py tests/unit/test_llama_server_scripts.py
```

Expected: PASS with no diagnostics.

- [ ] **Step 4: Run shell syntax checks**

Run:

```bash
bash -n scripts/start_llama_server_apple_silicon.sh
bash -n scripts/check_llama_server.sh
```

Expected: both commands exit 0 with no output.

- [ ] **Step 5: Run the real dry-run command**

Run:

```bash
LLAMA_DRY_RUN=1 make run-llama-server
```

Expected: PASS and print the installed model and projector paths plus
`--mmproj`, `--host 127.0.0.1`, `--port 8080`, `--ctx-size 4096`, and `-ngl 99`.

- [ ] **Step 6: Run the complete offline test suite**

Run:

```bash
pytest
```

Expected: all offline tests PASS. Tests explicitly requiring ROS2 or Isaac Sim may remain skipped according to their existing markers/environment checks.

- [ ] **Step 7: Confirm only intended files changed**

Run:

```bash
git status --short
git diff --check
```

Expected: no whitespace errors. Existing unrelated user changes remain untouched.

- [ ] **Step 8: Perform the optional live smoke test**

In terminal 1:

```bash
make run-llama-server
```

After model loading completes, run in terminal 2:

```bash
make check-llama-server
python -c \
  'from reasoning.vlm import LlamaServerBackend; print(LlamaServerBackend().is_ready())'
```

Expected: the Make health check succeeds and Python prints `True`. Stop the
foreground server with `Ctrl-C`. This step is optional during automated
execution because loading the model is hardware-dependent and consumes several
gigabytes of memory.
