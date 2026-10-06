#!/usr/bin/env bash
# Serve Qwen3-VL-8B-Instruct (Q4_K_M + F16 mmproj) with llama-server on the
# Isaac Sim VM, behind a VRAM headroom gate (model-wiring ruling 2026-10-06,
# prereg-v2 design spec: "L4 VRAM co-residency with Isaac verified by
# nvidia-smi headroom before any joint run").
#
# Usage (VM host, user ubuntu; docker runs without sudo):
#   scripts/vm/qwen_serve.sh fetch    # download + sha256-verify the pinned GGUFs
#   scripts/vm/qwen_serve.sh verify   # re-check the cached files' sha256
#   scripts/vm/qwen_serve.sh gate     # VRAM headroom gate only (exit 3 = refuse)
#   scripts/vm/qwen_serve.sh start    # verify + gate + launch + wait for /health
#   scripts/vm/qwen_serve.sh status   # container, /health, /props, VRAM
#   scripts/vm/qwen_serve.sh stop     # stop and remove the server container
#
# Serving: the official llama.cpp `server-cuda` image pinned by digest (the
# host has no CUDA toolkit; the nvidia container runtime is configured), host
# network, bound to 127.0.0.1:${QWEN_PORT}, so M5 inside `vgu_ros` (host
# network) reaches it at the `llama_server_qwen3vl` base_url in
# config/models.yaml. `--alias` makes the OpenAI-compatible `model` field echo
# that arm's model_id, so `served_model` is meaningful per call. `-np 1` keeps
# the whole context on one slot (newer builds split -c across slots).
#
# VRAM gate (REGISTERED before its first run, 2026-10-06 -- not tuned to any
# observed number):
#   need    QWEN_NEED_MIB    = 9216  weights 4795 MiB (5,027,784,800 B) + mmproj
#                                    1105 MiB (1,159,029,824 B) + f16 KV cache at
#                                    -c 8192 (36 layers x 8 KV heads x 128 dim x
#                                    2 x 2 B = 144 KiB/token -> 1152 MiB) + CUDA
#                                    context/compute buffers (~2 GiB allowance)
#   margin  QWEN_MARGIN_MIB  = 2048  fixed safety margin
#   reserve ISAAC_RESERVE_MIB= 3072  Isaac Sim's peak, applied only when Isaac is
#                                    NOT running at gate time (the server starts
#                                    before each episode's Isaac); historical
#                                    full-episode peak 2378 MiB
#                                    (data/logs/vm_runs/t2b_*/load.txt), rounded up
#   REFUSE to start if nvidia-smi memory.free < need + margin (+ reserve).
set -euo pipefail

QWEN_MODEL_DIR="${QWEN_MODEL_DIR:-$HOME/models/qwen3vl}"
QWEN_PORT="${QWEN_PORT:-8080}"
QWEN_CTX="${QWEN_CTX:-8192}"
QWEN_ALIAS="${QWEN_ALIAS:-qwen3-vl-8b-instruct-q4_k_m}"
QWEN_CONTAINER="${QWEN_CONTAINER:-vgu_qwen}"
QWEN_NEED_MIB="${QWEN_NEED_MIB:-9216}"
QWEN_MARGIN_MIB="${QWEN_MARGIN_MIB:-2048}"
ISAAC_RESERVE_MIB="${ISAAC_RESERVE_MIB:-3072}"
QWEN_HEALTH_TIMEOUT_SEC="${QWEN_HEALTH_TIMEOUT_SEC:-300}"

# llama.cpp server-cuda, resolved 2026-10-06 from ghcr.io/ggml-org/llama.cpp:server-cuda.
LLAMA_IMAGE="ghcr.io/ggml-org/llama.cpp@sha256:c6fd6053d3b6a1a54849ab5468971cf3ae03fbf3d72fdfb25a1f862e320cace3"

# Official Qwen GGUF repo, pinned revision (HF API `sha`, lastModified 2025-11-01).
HF_REPO="Qwen/Qwen3-VL-8B-Instruct-GGUF"
HF_REV="f982a07559d4a2f6c8744d840bf6fccab30eea96"
MODEL_FILE="Qwen3VL-8B-Instruct-Q4_K_M.gguf"
MODEL_SHA256="67d1659bfe71b89d50b45a4ad1a9e5b997e5bb16ce5da66a6a6167abd569e9e2"
MODEL_BYTES=5027784800
MMPROJ_FILE="mmproj-Qwen3VL-8B-Instruct-F16.gguf"
MMPROJ_SHA256="ca524100ebf825c9a870db1c580d03879e0da0ab2541697e2458e64891cf9d38"
MMPROJ_BYTES=1159029824

log() { printf '[qwen-serve %s] %s\n' "$(date -u +%H:%M:%S)" "$*"; }

isaac_running() {
  # Bracketed patterns so the match never hits this script's own command line.
  pgrep -f '[r]un_simulation|[i]saac\.scripts' >/dev/null 2>&1
}

fetch_one() {
  local name="$1" sha="$2" bytes="$3" dest="$QWEN_MODEL_DIR/$1"
  if [ -f "$dest" ] && [ "$(stat -c %s "$dest")" = "$bytes" ] \
      && [ "$(sha256sum "$dest" | awk '{print $1}')" = "$sha" ]; then
    log "cached and verified: $name"
    return 0
  fi
  log "downloading $name ($bytes bytes) at $HF_REV"
  curl -fL --retry 3 -o "$dest.part" \
    "https://huggingface.co/${HF_REPO}/resolve/${HF_REV}/${name}"
  local got
  got="$(sha256sum "$dest.part" | awk '{print $1}')"
  if [ "$got" != "$sha" ]; then
    log "REFUSING: $name sha256 $got != pinned $sha"
    rm -f "$dest.part"
    return 1
  fi
  mv "$dest.part" "$dest"
  log "verified: $name sha256 $sha"
}

verify_files() {
  local ok=0
  for pair in "$MODEL_FILE:$MODEL_SHA256" "$MMPROJ_FILE:$MMPROJ_SHA256"; do
    local name="${pair%%:*}" sha="${pair##*:}"
    local got
    got="$(sha256sum "$QWEN_MODEL_DIR/$name" 2>/dev/null | awk '{print $1}')"
    if [ "$got" = "$sha" ]; then
      log "sha256 OK $name"
    else
      log "sha256 MISMATCH $name (got ${got:-missing})"
      ok=1
    fi
  done
  return "$ok"
}

gate() {
  local free used total required reserve=0 state="running"
  read -r free used total < <(nvidia-smi --query-gpu=memory.free,memory.used,memory.total \
    --format=csv,noheader,nounits | head -1 | tr -d ',')
  if ! isaac_running; then
    reserve="$ISAAC_RESERVE_MIB"
    state="not running"
  fi
  required=$((QWEN_NEED_MIB + QWEN_MARGIN_MIB + reserve))
  log "VRAM gate: free=${free} used=${used} total=${total} MiB; Isaac ${state}; required=${required} (need ${QWEN_NEED_MIB} + margin ${QWEN_MARGIN_MIB} + Isaac reserve ${reserve})"
  if [ "$free" -lt "$required" ]; then
    log "GATE REFUSED: free ${free} MiB < required ${required} MiB"
    return 3
  fi
  log "GATE OK"
}

start() {
  if docker ps -a --format '{{.Names}}' | grep -qx "$QWEN_CONTAINER"; then
    log "REFUSING: container $QWEN_CONTAINER already exists (run stop first)"
    return 1
  fi
  verify_files
  gate
  log "starting $QWEN_CONTAINER from $LLAMA_IMAGE (alias $QWEN_ALIAS, -c $QWEN_CTX, port $QWEN_PORT)"
  docker run -d --name "$QWEN_CONTAINER" --gpus all --network host \
    -v "$QWEN_MODEL_DIR:/models:ro" "$LLAMA_IMAGE" \
    -m "/models/$MODEL_FILE" --mmproj "/models/$MMPROJ_FILE" \
    --alias "$QWEN_ALIAS" --host 127.0.0.1 --port "$QWEN_PORT" \
    -c "$QWEN_CTX" -np 1 -ngl 99 --jinja >/dev/null
  local waited=0
  until curl -fs "http://127.0.0.1:${QWEN_PORT}/health" 2>/dev/null | grep -q '"ok"'; do
    if ! docker ps --format '{{.Names}}' | grep -qx "$QWEN_CONTAINER"; then
      log "ERROR: server container exited during startup"
      docker logs --tail 40 "$QWEN_CONTAINER" 2>&1 || true
      return 1
    fi
    if [ "$waited" -ge "$QWEN_HEALTH_TIMEOUT_SEC" ]; then
      log "ERROR: /health not ok after ${waited}s"
      return 1
    fi
    sleep 5
    waited=$((waited + 5))
  done
  log "healthy after ${waited}s"
  status
}

status() {
  docker ps -a --filter "name=^${QWEN_CONTAINER}$" --format '{{.Names}} {{.Status}} {{.Image}}'
  curl -fs "http://127.0.0.1:${QWEN_PORT}/health" 2>/dev/null && echo || echo "health: unreachable"
  curl -fs "http://127.0.0.1:${QWEN_PORT}/v1/models" 2>/dev/null && echo || true
  curl -fs "http://127.0.0.1:${QWEN_PORT}/props" 2>/dev/null \
    | python3 -c 'import json,sys; d=json.load(sys.stdin); print("props:", json.dumps({k: d.get(k) for k in ("build_info","model_path","modalities","total_slots")}))' \
    2>/dev/null || true
  nvidia-smi --query-gpu=memory.used,memory.free,utilization.gpu --format=csv,noheader
}

stop() {
  if docker ps -a --format '{{.Names}}' | grep -qx "$QWEN_CONTAINER"; then
    docker stop "$QWEN_CONTAINER" >/dev/null && docker rm "$QWEN_CONTAINER" >/dev/null
    log "stopped and removed $QWEN_CONTAINER"
  else
    log "no $QWEN_CONTAINER container"
  fi
}

case "${1:-}" in
  fetch)
    mkdir -p "$QWEN_MODEL_DIR"
    fetch_one "$MODEL_FILE" "$MODEL_SHA256" "$MODEL_BYTES"
    fetch_one "$MMPROJ_FILE" "$MMPROJ_SHA256" "$MMPROJ_BYTES"
    du -sh "$QWEN_MODEL_DIR"
    ;;
  verify) verify_files ;;
  gate) gate ;;
  start) start ;;
  status) status ;;
  stop) stop ;;
  *)
    echo "usage: $0 {fetch|verify|gate|start|status|stop}" >&2
    exit 2
    ;;
esac
