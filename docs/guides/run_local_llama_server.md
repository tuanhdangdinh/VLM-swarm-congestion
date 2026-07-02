# Run Cosmos Reason2 Locally on Apple Silicon

This guide runs the local vision backend as a foreground `llama.cpp`
`llama-server` process with the OpenAI-compatible `/v1` API. For this
documented launcher, the multimodal projector is mandatory and must be
readable: there is no text-only fallback in this workflow because
`config/models.yaml` and the launcher expect a matching `mmproj` whenever live
inference is enabled. That is a scope choice for this guide and launcher, not a
statement about the backend in general.

## Prerequisites

- Apple Silicon Mac running macOS.
- Homebrew installed.
- Project Python environment created and populated with `requirements-dev.txt`.
- Cosmos Reason2 GGUF model and matching `mmproj` configured in
  `config/models.yaml`.

The checked-in defaults currently point at:

```text
$HOME/.cache/lm-studio/models/DevQuasar/nvidia.Cosmos-Reason2-8B-GGUF/nvidia.Cosmos-Reason2-8B.f16.gguf.Q6_K.gguf
$HOME/.cache/lm-studio/models/DevQuasar/nvidia.Cosmos-Reason2-8B-GGUF/mmproj-nvidia.Cosmos-Reason2-8B.f16.gguf
```

That directory contains the model and projector paths configured in
`config/models.yaml`.

## Setup

Create the project virtual environment and install the development requirements:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

Install the server binary with Homebrew:

```bash
brew install llama.cpp
```

## Start the server

The normal entry point is the Make target:

```bash
make run-llama-server
```

It starts `llama-server` in the foreground and serves the OpenAI-compatible
endpoint at `http://127.0.0.1:8080/v1`.

Stop it with `Ctrl-C`.

In a second terminal, confirm the server is reachable:

```bash
make check-llama-server
```

## Configuration and overrides

The launcher reads defaults from `config/models.yaml` and applies environment
overrides before starting `llama-server`.

| Setting | Environment override | Default |
|---|---|---|
| model path | `LLAMA_MODEL_PATH` | `$HOME/.cache/lm-studio/models/DevQuasar/nvidia.Cosmos-Reason2-8B-GGUF/nvidia.Cosmos-Reason2-8B.f16.gguf.Q6_K.gguf` |
| mmproj path | `LLAMA_MMPROJ_PATH` | `$HOME/.cache/lm-studio/models/DevQuasar/nvidia.Cosmos-Reason2-8B-GGUF/mmproj-nvidia.Cosmos-Reason2-8B.f16.gguf` |
| host | `LLAMA_HOST` | `127.0.0.1` |
| port | `LLAMA_PORT` | `8080` |
| context size | `LLAMA_CTX_SIZE` | `4096` |
| GPU layers | `LLAMA_GPU_LAYERS` | `99` |

Example dry run:

```bash
LLAMA_DRY_RUN=1 make run-llama-server
```

The dry run prints the resolved command and endpoint, then exits without
starting the server.

If you need to bind to a wildcard address for a local test, the health helper
still checks readiness through loopback:

- `0.0.0.0` maps to `127.0.0.1`
- `::` maps to `::1`

## Live inference switch

Live inference is controlled in `config/models.yaml`:

- set `vlm.reasoner.backend_id: llama_server` to use the local server;
- switch to `mock` for offline tests and CI-friendly runs.
- the repository default is `openai`, so set `OPENAI_API_KEY` before running the app if you do not override the backend.

Keep the `mmproj` path aligned with the model path. The backend expects the
projector file to exist and be readable when vision mode is active.

## Smoke test

Run a manual health probe from another shell:

```bash
health_url="$(./.venv/bin/python scripts/llama_server_config.py health-url --config config/models.yaml)"
curl "$health_url"
```

Expected response: JSON with `"status":"ok"`.

The code path used by the application should also report ready:

```python
from reasoning.vlm.llama_server_backend import LlamaServerBackend

assert LlamaServerBackend().is_ready() is True
```

## Troubleshooting

- Missing model file: the launcher exits before `llama-server` starts.
- Missing `mmproj`: the launcher exits before `llama-server` starts.
- No text-only fallback in this launcher: it is documented and wired for
  paired model + projector usage, not for projector-free operation. If you run
  `LlamaServerBackend` against a separately started server without `mmproj`,
  that backend can be configured text-only, but that mode is outside this guide
  and launcher.
- Wrong backend mode: if the app still uses the OpenAI backend, switch
  `backend_id` to `llama_server` or `mock` in `config/models.yaml`.

## Reference

- `Makefile`
- `scripts/start_llama_server_apple_silicon.sh`
- `scripts/check_llama_server.sh`
- `scripts/llama_server_config.py`
- `config/models.yaml`
