#!/usr/bin/env bash
# Serve allenai/Molmo2-ER (4.85B, Apache-2.0; Qwen3-4B + SigLIP2) with vLLM's
# OpenAI-compatible server on the Isaac Sim VM, behind a VRAM headroom gate
# (WIRE-NEXT ruling 2026-10-06, prereg-v2 design spec: the cross-lab
# specialist-replication arm; mirrors scripts/vm/qwen_serve.sh).
#
# Usage (VM host, user ubuntu; docker runs without sudo):
#   scripts/vm/molmo_serve.sh fetch    # download + sha256-verify every pinned file
#   scripts/vm/molmo_serve.sh verify   # re-check the cached files' sha256
#   scripts/vm/molmo_serve.sh pull     # pull the pinned vLLM image by digest
#   scripts/vm/molmo_serve.sh gate     # VRAM headroom gate only (exit 3 = refuse)
#   scripts/vm/molmo_serve.sh start    # verify + gate + launch + wait for /v1/models
#   scripts/vm/molmo_serve.sh status   # container, served models, VRAM
#   scripts/vm/molmo_serve.sh stop     # stop and remove the server container
#
# Serving: the official vLLM OpenAI-compatible image (vllm/vllm-openai v0.31.0,
# linux/amd64 manifest pinned by digest; Molmo2ForConditionalGeneration is a
# natively supported architecture since vLLM 0.15.0 per github.com/allenai/molmo2,
# listed in v0.31.0 docs/models/supported_models.md). A container, not a host
# venv: the host has no CUDA toolkit and the nvidia container runtime is
# already configured (Qwen precedent). Host network, bound to
# 127.0.0.1:${MOLMO_PORT}, so M5 inside `vgu_ros` (host network) reaches it at
# the `llama_server_molmo2er` base_url in config/models.yaml.
# `--served-model-name` makes the OpenAI `model` field echo that arm's
# model_id, so `served_model` is meaningful per call.
#
# Weights: every file of the HF repo at the pinned revision, each sha256-pinned
# -- not only the LFS shards: `--trust-remote-code` executes the repo's
# processing/configuration .py files, so those are pinned too. The server
# reads ONLY the verified local directory (HF_HUB_OFFLINE=1,
# TRANSFORMERS_OFFLINE=1; no hub access at serve time). The shards are fp32
# (19,403,476,800 B for 4,850,869,200 params); `--dtype bfloat16` matches the
# model card's own inference example (torch.autocast bfloat16).
#
# Server flags: --max-model-len 16384 (the model's max_position_embeddings;
# a stage-1 call is ~2k text tokens + up to 2 images + max_tokens 2048),
# --max-num-seqs 1 (one caller), --limit-mm-per-prompt image<=2, video=0 (the
# frame + optional zoom tile; video 0 stops the profiler sizing encoder
# memory for a max-size dummy video).
#
# VRAM gate (REGISTERED before its first run, 2026-10-06 -- not tuned to any
# observed number). vLLM PRE-ALLOCATES gpu_memory_utilization x total VRAM at
# startup (weights + KV cache + activations live inside that budget), so the
# server's footprint is fixed by the flag, not by load:
#   util    MOLMO_GPU_UTIL   = 0.60  -> need = 0.60 x total (24570 MiB on the L4
#                                    = 14742 MiB); bf16 weights 9251 MiB
#                                    (4,850,869,200 x 2 B), the rest is KV cache
#                                    (36 layers x 8 KV heads x 128 x 2 x 2 B =
#                                    144 KiB/token -> 2304 MiB at 16384) + vision
#                                    encoder activations + CUDA graphs
#   margin  MOLMO_MARGIN_MIB = 2048  fixed safety margin
#   reserve ISAAC_RESERVE_MIB= 3072  Isaac Sim's peak, applied only when Isaac is
#                                    NOT running at gate time (the server starts
#                                    before each episode's Isaac); historical
#                                    full-episode peak 2378 MiB, rounded up
#   REFUSE to start if nvidia-smi memory.free < need + margin (+ reserve).
set -euo pipefail

MOLMO_MODEL_DIR="${MOLMO_MODEL_DIR:-$HOME/models/molmo2er}"
MOLMO_PORT="${MOLMO_PORT:-8090}"
MOLMO_SERVED_NAME="${MOLMO_SERVED_NAME:-molmo2-er}"
MOLMO_CONTAINER="${MOLMO_CONTAINER:-vgu_molmo}"
MOLMO_MAX_MODEL_LEN="${MOLMO_MAX_MODEL_LEN:-16384}"
MOLMO_GPU_UTIL="${MOLMO_GPU_UTIL:-0.60}"
MOLMO_MARGIN_MIB="${MOLMO_MARGIN_MIB:-2048}"
ISAAC_RESERVE_MIB="${ISAAC_RESERVE_MIB:-3072}"
MOLMO_READY_TIMEOUT_SEC="${MOLMO_READY_TIMEOUT_SEC:-900}"

# vllm/vllm-openai:v0.31.0 (pushed 2026-10-04), linux/amd64 manifest digest
# (the multi-arch index is sha256:c1c9f6fd5c109ba7f0546a59f5b2f15fb87f64c77782e90a27b648b42a8e67c3),
# resolved 2026-10-06 from the Docker Hub tag API.
VLLM_IMAGE="vllm/vllm-openai@sha256:a4a4c0437bf7240089da5f08aa370c4aee17ae5290f7a3b468825ee26c4c3a6b"

# Official Ai2 repo, pinned revision (HF API `sha`, lastModified 2026-05-21).
HF_REPO="allenai/Molmo2-ER"
HF_REV="dab22564403d2607855bb1fffb0721285b445081"
# name bytes sha256 -- every file vLLM or the remote code reads (README and
# the logo svg are not read and not fetched).
PINNED_FILES="
added_tokens.json 10024 885f778b4536d06e9244872c4c9c87d5e45595c574912dc423d52b7a017182ab
chat_template.jinja 3169 ec66862fda57dc1aef90a21b2a0f64c18a280e2483206449bd251a73b8993101
config.json 2538 0030efa549538d7eb29db139aba773417f330a0d2ecacc8dad2b85d72e963391
configuration_molmo2.py 13905 1405b6760579de537521829b9641c8362d5d50e7ef2bdbe3434d2de4a2fc6416
generation_config.json 117 579e8533dfe5b30886c92979c5dd33afbbdfe6ce58c1a70f733aad839511304e
image_processing_molmo2.py 22169 22fcc160210a3a648b6d618171686c40b900f512107f532c266af7792ac00511
merges.txt 1671853 8831e4f1a044471340f7c0a83d7bd71306a5b867e95fd870f74d0c5308a904d5
model.safetensors.index.json 75780 bc043f680e16ecd6f936ef55bf1979781772d37005192d2f3382385f79e42045
modeling_molmo2.py 71559 d3cafcb5300dee41dc9b6d6e8b59e7d3b710bce0408672e8fd78a3bcb28669ce
preprocessor_config.json 555 026ee03897ff86cb0d3f7c638145a04a253d4c0722fc5bcc3cf996bb0ebed211
processing_molmo2.py 18224 73fee7d5cc24e64fdecff90b07e2fea1985113394ffaaf9b87f42e40f3fb4aeb
processor_config.json 347 c5d13a1d7a68cbdd4efff75680e74e4a61d8b91fb0ad80a88c0147b4f4b8d8d2
special_tokens_map.json 7989 7af6f09d819fce2662d3be59766042b6d20835104745049754cc61e1755c33fd
tokenizer.json 11477774 3ef24b8f324674c3a1163e2c205b9e2b1a230fd2d4294de7b779bb419fc23914
tokenizer_config.json 65188 0c4ba1a4c5e1c499b7c5a36145cdf6d3273d85a6870e43a1affc123e0b046031
video_preprocessor_config.json 1006 558eccd953fd79b94e7a5d222782350e9aaf2751bb18eaa95d61fbf52e9ae341
video_processing_molmo2.py 37660 aaeffabdee0b11f93fb380093df1738964340ea072ba6352bd3f371cc0df835e
vocab.json 2776833 ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910
model-00001-of-00004.safetensors 4891799000 12921633f1ff67db04516fdd37160a5b88057c1611acefb74117ea0f5dcb5773
model-00002-of-00004.safetensors 4844690992 fb09af13aaf7a5630e7d6ecec06df670494302797d46f1ba6dacae7b7b1443fe
model-00003-of-00004.safetensors 4844691024 1601349698c99636e1f6e09a0b96b1da5a891c3b7f0ab72bc6590fdf39ce7ca4
model-00004-of-00004.safetensors 4822393416 30481c43be906da15fb0d8f71b9708dd19582b380699e314323d7257014c7523
"

log() { printf '[molmo-serve %s] %s\n' "$(date -u +%H:%M:%S)" "$*"; }

isaac_running() {
  # Bracketed patterns so the match never hits this script's own command line.
  pgrep -f '[r]un_simulation|[i]saac\.scripts' >/dev/null 2>&1
}

fetch_one() {
  local name="$1" bytes="$2" sha="$3" dest="$MOLMO_MODEL_DIR/$1"
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

fetch_all() {
  mkdir -p "$MOLMO_MODEL_DIR"
  echo "$PINNED_FILES" | while read -r name bytes sha; do
    [ -z "$name" ] && continue
    fetch_one "$name" "$bytes" "$sha"
  done
  du -sh "$MOLMO_MODEL_DIR"
}

verify_files() {
  local bad=0 name bytes sha got
  while read -r name bytes sha; do
    [ -z "$name" ] && continue
    got="$(sha256sum "$MOLMO_MODEL_DIR/$name" 2>/dev/null | awk '{print $1}')"
    if [ "$got" = "$sha" ]; then
      log "sha256 OK $name"
    else
      log "sha256 MISMATCH $name (got ${got:-missing})"
      bad=1
    fi
  done <<<"$PINNED_FILES"
  return "$bad"
}

gate() {
  local free used total need required reserve=0 state="running"
  read -r free used total < <(nvidia-smi --query-gpu=memory.free,memory.used,memory.total \
    --format=csv,noheader,nounits | head -1 | tr -d ',')
  need=$(awk -v u="$MOLMO_GPU_UTIL" -v t="$total" 'BEGIN { printf "%d", u * t + 0.5 }')
  if ! isaac_running; then
    reserve="$ISAAC_RESERVE_MIB"
    state="not running"
  fi
  required=$((need + MOLMO_MARGIN_MIB + reserve))
  log "VRAM gate: free=${free} used=${used} total=${total} MiB; Isaac ${state}; required=${required} (need ${MOLMO_GPU_UTIL}x${total}=${need} + margin ${MOLMO_MARGIN_MIB} + Isaac reserve ${reserve})"
  if [ "$free" -lt "$required" ]; then
    log "GATE REFUSED: free ${free} MiB < required ${required} MiB"
    return 3
  fi
  log "GATE OK"
}

pull() {
  docker pull "$VLLM_IMAGE"
  docker image inspect "$VLLM_IMAGE" --format '{{.Id}} {{.Size}}'
}

served() {
  curl -fs "http://127.0.0.1:${MOLMO_PORT}/v1/models" 2>/dev/null \
    | grep -q "\"${MOLMO_SERVED_NAME}\""
}

start() {
  if docker ps -a --format '{{.Names}}' | grep -qx "$MOLMO_CONTAINER"; then
    log "REFUSING: container $MOLMO_CONTAINER already exists (run stop first)"
    return 1
  fi
  verify_files
  gate
  log "starting $MOLMO_CONTAINER from $VLLM_IMAGE (served name $MOLMO_SERVED_NAME, util $MOLMO_GPU_UTIL, max-model-len $MOLMO_MAX_MODEL_LEN, port $MOLMO_PORT)"
  docker run -d --name "$MOLMO_CONTAINER" --gpus all --network host --ipc host \
    -e HF_HUB_OFFLINE=1 -e TRANSFORMERS_OFFLINE=1 \
    -v "$MOLMO_MODEL_DIR:/models/molmo2er:ro" "$VLLM_IMAGE" \
    --model /models/molmo2er --served-model-name "$MOLMO_SERVED_NAME" \
    --trust-remote-code --dtype bfloat16 \
    --max-model-len "$MOLMO_MAX_MODEL_LEN" --max-num-seqs 1 \
    --gpu-memory-utilization "$MOLMO_GPU_UTIL" \
    --limit-mm-per-prompt '{"image": 2, "video": 0}' \
    --host 127.0.0.1 --port "$MOLMO_PORT" >/dev/null
  local waited=0
  until served; do
    if ! docker ps --format '{{.Names}}' | grep -qx "$MOLMO_CONTAINER"; then
      log "ERROR: server container exited during startup"
      docker logs --tail 60 "$MOLMO_CONTAINER" 2>&1 || true
      return 1
    fi
    if [ "$waited" -ge "$MOLMO_READY_TIMEOUT_SEC" ]; then
      log "ERROR: /v1/models does not list $MOLMO_SERVED_NAME after ${waited}s"
      return 1
    fi
    sleep 5
    waited=$((waited + 5))
  done
  log "serving after ${waited}s"
  status
}

status() {
  docker ps -a --filter "name=^${MOLMO_CONTAINER}$" --format '{{.Names}} {{.Status}} {{.Image}}'
  printf 'health http=%s\n' "$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:${MOLMO_PORT}/health" 2>/dev/null || true)"
  curl -fs "http://127.0.0.1:${MOLMO_PORT}/v1/models" 2>/dev/null && echo || echo "models: unreachable"
  curl -fs "http://127.0.0.1:${MOLMO_PORT}/version" 2>/dev/null && echo || true
  nvidia-smi --query-gpu=memory.used,memory.free,utilization.gpu --format=csv,noheader
}

stop() {
  if docker ps -a --format '{{.Names}}' | grep -qx "$MOLMO_CONTAINER"; then
    docker stop "$MOLMO_CONTAINER" >/dev/null && docker rm "$MOLMO_CONTAINER" >/dev/null
    log "stopped and removed $MOLMO_CONTAINER"
  else
    log "no $MOLMO_CONTAINER container"
  fi
}

case "${1:-}" in
  fetch) fetch_all ;;
  verify) verify_files ;;
  pull) pull ;;
  gate) gate ;;
  start) start ;;
  status) status ;;
  stop) stop ;;
  *)
    echo "usage: $0 {fetch|verify|pull|gate|start|status|stop}" >&2
    exit 2
    ;;
esac
