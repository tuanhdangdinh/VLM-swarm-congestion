import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
MODELS_CONFIG = ROOT / "config" / "models.yaml"
CONFIG_HELPER = ROOT / "scripts" / "llama_server_config.py"
START_SCRIPT = ROOT / "scripts" / "start_llama_server_apple_silicon.sh"


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


def _write_executable(path: Path, contents: str) -> None:
    path.write_text(contents, encoding="utf-8")
    path.chmod(0o755)


@pytest.fixture
def llama_start_project(tmp_path: Path) -> dict[str, Path | dict[str, str]]:
    project = tmp_path / "project"
    scripts = project / "scripts"
    config = project / "config"
    fake_bin = tmp_path / "bin"
    home = tmp_path / "home"
    scripts.mkdir(parents=True)
    config.mkdir()
    fake_bin.mkdir()
    home.mkdir()

    shutil.copy2(CONFIG_HELPER, scripts / CONFIG_HELPER.name)
    if START_SCRIPT.exists():
        shutil.copy2(START_SCRIPT, scripts / START_SCRIPT.name)

    model_path = home / "models" / "model file.gguf"
    mmproj_path = home / "models" / "mmproj.gguf"
    model_path.parent.mkdir()
    model_path.write_bytes(b"model")
    mmproj_path.write_bytes(b"projector")
    (config / "models.yaml").write_text(
        yaml.safe_dump(
            {
                "vlm": {
                    "llama_server": {
                        "base_url": "http://127.0.0.1:8080/v1",
                        "model_path": "$HOME/models/model file.gguf",
                        "mmproj_path": "$HOME/models/mmproj.gguf",
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    dirname = shutil.which("dirname")
    assert dirname is not None
    (fake_bin / "dirname").symlink_to(dirname)
    (fake_bin / "python3").symlink_to(sys.executable)
    _write_executable(
        fake_bin / "uname",
        """#!/bin/bash
case "$1" in
  -s) printf '%s\n' "${FAKE_UNAME_S:-Darwin}" ;;
  -m) printf '%s\n' "${FAKE_UNAME_M:-arm64}" ;;
  *) exit 2 ;;
esac
""",
    )
    server_marker = tmp_path / "llama-server-ran"
    _write_executable(
        fake_bin / "llama-server",
        f"""#!/bin/bash
touch {shlex.quote(str(server_marker))}
""",
    )

    env = {
        "HOME": str(home),
        "PATH": str(fake_bin),
        "LLAMA_DRY_RUN": "1",
    }
    return {
        "project": project,
        "script": scripts / START_SCRIPT.name,
        "fake_bin": fake_bin,
        "model_path": model_path,
        "mmproj_path": mmproj_path,
        "server_marker": server_marker,
        "env": env,
    }


def _run_start_script(
    fixture: dict[str, Path | dict[str, str]],
    *,
    environment: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = dict(fixture["env"])
    env.update(environment or {})
    return subprocess.run(
        ["/bin/bash", str(fixture["script"])],
        check=False,
        capture_output=True,
        cwd=fixture["project"],
        env=env,
        text=True,
    )


def _printed_command(stdout: str) -> list[str]:
    command_line = next(
        line.removeprefix("Command: ")
        for line in stdout.splitlines()
        if line.startswith("Command: ")
    )
    return shlex.split(command_line)


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


def test_config_helper_shell_output_round_trips_adversarial_values(tmp_path):
    marker_path = tmp_path / "command-substitution-ran"
    model_path = (
        f"/models/space ' quote $(touch {marker_path}) ; semicolon\n"
        "& ampersand.gguf"
    )
    mmproj_path = (
        f"/models/projector ' $(touch {marker_path}) ; semicolon * wildcard.gguf"
    )
    config = _valid_llama_server_config()
    config["model_path"] = model_path
    config["mmproj_path"] = mmproj_path
    config_path = _write_config(tmp_path, config)

    helper_result = _run_config_helper(config_path, "shell")

    assert helper_result.returncode == 0
    shell_result = subprocess.run(
        [
            "/bin/bash",
            "-c",
            (
                f"{helper_result.stdout}\n"
                "printf '%s\\0%s\\0' \"$LLAMA_MODEL_PATH\" \"$LLAMA_MMPROJ_PATH\""
            ),
        ],
        check=False,
        capture_output=True,
        cwd=tmp_path,
        env={"HOME": str(tmp_path), "PATH": "/usr/bin:/bin"},
    )
    assert shell_result.returncode == 0
    assert shell_result.stdout.split(b"\0") == [
        model_path.encode(),
        mmproj_path.encode(),
        b"",
    ]
    assert not marker_path.exists()


def test_config_helper_builds_health_url_from_effective_endpoint(tmp_path):
    config = _valid_llama_server_config()
    config["base_url"] = "http://localhost:9090/v1"
    config_path = _write_config(tmp_path, config)

    result = _run_config_helper(config_path, "health-url")

    assert result.returncode == 0
    assert result.stdout == "http://localhost:9090/health\n"


def test_config_helper_brackets_ipv6_health_host(tmp_path):
    config = _valid_llama_server_config()
    config["base_url"] = "http://[::1]:8080/v1"
    config_path = _write_config(tmp_path, config)

    result = _run_config_helper(
        config_path,
        "health-url",
        environment={"LLAMA_HOST": "::1"},
    )

    assert result.returncode == 0
    assert result.stdout == "http://[::1]:8080/health\n"


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


def test_config_helper_rejects_port_outside_tcp_range(tmp_path):
    config_path = _write_config(tmp_path, _valid_llama_server_config())

    result = _run_config_helper(
        config_path,
        "shell",
        environment={"LLAMA_PORT": "65536"},
    )

    assert result.returncode == 2
    assert "LLAMA_PORT must be between 1 and 65535" in result.stderr


def test_start_script_dry_run_prints_vision_server_command(llama_start_project):
    result = _run_start_script(llama_start_project)

    assert result.returncode == 0, result.stderr
    assert _printed_command(result.stdout) == [
        "llama-server",
        "-m",
        str(llama_start_project["model_path"]),
        "--mmproj",
        str(llama_start_project["mmproj_path"]),
        "--host",
        "127.0.0.1",
        "--port",
        "8080",
        "--ctx-size",
        "4096",
        "-ngl",
        "99",
        "--log-format",
        "text",
    ]
    assert "127.0.0.1:8080" in result.stdout
    assert not llama_start_project["server_marker"].exists()


def test_start_script_applies_runtime_overrides(llama_start_project):
    result = _run_start_script(
        llama_start_project,
        environment={
            "LLAMA_HOST": "0.0.0.0",
            "LLAMA_PORT": "8181",
            "LLAMA_CTX_SIZE": "8192",
            "LLAMA_GPU_LAYERS": "42",
        },
    )

    assert result.returncode == 0, result.stderr
    command = _printed_command(result.stdout)
    assert command[command.index("--host") + 1] == "0.0.0.0"
    assert command[command.index("--port") + 1] == "8181"
    assert command[command.index("--ctx-size") + 1] == "8192"
    assert command[command.index("-ngl") + 1] == "42"


@pytest.mark.parametrize(
    ("environment", "expected"),
    [
        ({"FAKE_UNAME_S": "Linux"}, "requires macOS on Apple Silicon"),
        ({"FAKE_UNAME_M": "x86_64"}, "requires macOS on Apple Silicon"),
    ],
)
def test_start_script_rejects_unsupported_platform(
    llama_start_project,
    environment,
    expected,
):
    result = _run_start_script(llama_start_project, environment=environment)

    assert result.returncode != 0
    assert expected in result.stderr


def test_start_script_reports_missing_llama_server(llama_start_project):
    Path(llama_start_project["fake_bin"], "llama-server").unlink()

    result = _run_start_script(llama_start_project)

    assert result.returncode != 0
    assert "brew install llama.cpp" in result.stderr


def test_start_script_reports_missing_python(llama_start_project):
    Path(llama_start_project["fake_bin"], "python3").unlink()

    result = _run_start_script(llama_start_project)

    assert result.returncode != 0
    assert "Python 3" in result.stderr
    assert "project setup" in result.stderr


def test_start_script_reports_missing_pyyaml(llama_start_project):
    python = Path(llama_start_project["fake_bin"], "python3")
    python.unlink()
    _write_executable(
        python,
        """#!/bin/bash
if [[ "$1" == "-c" ]]; then
  exit 1
fi
exit 99
""",
    )

    result = _run_start_script(llama_start_project)

    assert result.returncode != 0
    assert "PyYAML" in result.stderr
    assert "project setup" in result.stderr


def test_start_script_reports_resolved_missing_model(llama_start_project):
    llama_start_project["model_path"].unlink()

    result = _run_start_script(llama_start_project)

    assert result.returncode != 0
    assert str(llama_start_project["model_path"]) in result.stderr


def test_start_script_requires_mmproj_and_never_falls_back(llama_start_project):
    llama_start_project["mmproj_path"].unlink()

    result = _run_start_script(llama_start_project)

    assert result.returncode != 0
    assert str(llama_start_project["mmproj_path"]) in result.stderr
    assert not llama_start_project["server_marker"].exists()
