# Local Llama Server Setup Design

**Date:** 2026-06-12

## 1. Goal

Provide a repeatable foreground development command for running NVIDIA Cosmos
Reason2 through `llama-server` on the project's Apple Silicon host. Vision mode
must be enabled by default so M2 can send annotated camera frames to the
OpenAI-compatible endpoint.

The setup uses the existing Homebrew `llama-server`, Cosmos Reason2 GGUF model,
and multimodal projector already present in the LM Studio cache.

## 2. Scope

The implementation will:

- make `config/models.yaml` the default source for server paths and endpoint
  settings;
- permit environment variables to override local paths and launch settings;
- update the existing Apple Silicon startup script;
- add a Make target for starting the server;
- provide a lightweight health check;
- document installation, startup, configuration, and backend activation;
- test validation and command construction without loading the model.

Automatic startup, Docker deployment, model downloading, and Linux/NVIDIA
deployment are out of scope.

## 3. Configuration

The `vlm.llama_server` section in `config/models.yaml` remains the canonical
project configuration. Paths will use `$HOME` rather than a checked-in absolute
username:

```yaml
vlm:
  llama_server:
    base_url: "http://127.0.0.1:8080/v1"
    model_id: cosmos-reason2-8b
    model_path: "$HOME/.cache/lm-studio/models/DevQuasar/nvidia.Cosmos-Reason2-8B-GGUF/nvidia.Cosmos-Reason2-8B.f16.gguf.Q6_K.gguf"
    mmproj_path: "$HOME/.cache/lm-studio/models/DevQuasar/nvidia.Cosmos-Reason2-8B-GGUF/mmproj-nvidia.Cosmos-Reason2-8B.f16.gguf"
```

The startup script will expand `$HOME` after parsing the YAML. The following
environment variables may override defaults:

- `LLAMA_MODEL_PATH`
- `LLAMA_MMPROJ_PATH`
- `LLAMA_HOST`
- `LLAMA_PORT`
- `LLAMA_CTX_SIZE`
- `LLAMA_GPU_LAYERS`

Defaults are host `127.0.0.1`, port `8080`, context size `4096`, and GPU layers
`99`.

YAML parsing will use `.venv/bin/python` when available and otherwise
`python3`. The selected interpreter must be able to import PyYAML, which is
already a project dependency. A missing interpreter or PyYAML installation is a
startup error with the corresponding project setup command.

## 4. Startup Script

`scripts/start_llama_server_apple_silicon.sh` remains the user-facing entry
point. It will:

1. locate the repository root relative to the script;
2. read `model_path`, `mmproj_path`, and `base_url` from
   `config/models.yaml`;
3. apply environment overrides;
4. verify the host is macOS on ARM64;
5. verify `llama-server` is available;
6. verify both GGUF files exist and are readable;
7. derive host and port from `base_url`, then apply explicit host or port
   overrides;
8. print the effective endpoint and model paths;
9. replace the shell process with `llama-server` using `exec`.

The launch command will include:

```text
llama-server
  -m <model_path>
  --mmproj <mmproj_path>
  --host 127.0.0.1
  --port 8080
  --ctx-size 4096
  -ngl 99
  --log-format text
```

Vision mode is mandatory for this project setup. A missing projector is a
startup error rather than a fallback to text-only mode.

Using `exec` keeps logs in the foreground and ensures terminal signals reach
`llama-server` directly.

## 5. Developer Commands

The Makefile will expose:

```text
make run-llama-server
make check-llama-server
```

`run-llama-server` starts the foreground process. `check-llama-server` derives
the health URL from the same configuration and environment overrides, requests
`/health`, fails on a non-successful response, and prints a short
ready/not-ready result.

The application continues to default to the mock backend. Live inference is
enabled deliberately by changing:

```yaml
vlm:
  reasoner:
    backend_id: llama_server
```

This avoids making unit tests or normal development depend on a running model.

## 6. Error Handling

Startup errors will be concise and actionable:

- unsupported host: state that the script targets Apple Silicon;
- missing Python or PyYAML: show the normal project environment setup command;
- missing executable: show `brew install llama.cpp`;
- missing model or projector: print the resolved missing path;
- invalid YAML or absent required keys: identify the configuration key;
- occupied port or model load failure: allow `llama-server` to report the
  runtime error and preserve its exit status.

No script output will contain base64 image data, request payloads, or secrets.

## 7. Testing

`tests/unit/test_llama_server_script.py` will execute the shell entry points in
isolated temporary environments. The startup script's dry-run mode validates
configuration and prints the final command without starting `llama-server`.

Tests will cover:

- values loaded from `config/models.yaml`;
- `$HOME` expansion;
- environment variable precedence;
- required `mmproj` enforcement;
- missing `llama-server` handling;
- expected Metal, context, endpoint, model, and projector arguments;
- health-check success and failure using a local stub or mocked `curl`.

Existing Python VLM unit tests remain offline. A real model inference smoke test
is documented as a manual verification because loading the model is expensive
and hardware-dependent.

## 8. Acceptance Criteria

The setup is complete when:

1. `make run-llama-server` starts the existing Cosmos model in vision mode on
   Apple Silicon.
2. `make check-llama-server` reports the server ready.
3. `LlamaServerBackend.is_ready()` returns true for the same endpoint.
4. The launch script contains no username-specific absolute path.
5. Dry-run tests verify the launch command without loading the model.
6. The README or a focused guide explains how to start the server and enable
   the live backend.
