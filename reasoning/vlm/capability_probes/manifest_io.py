"""Load/save the frozen manifest and re-materialize its frames from logs.

`data/logs/vm_runs` is gitignored (CLAUDE.md, Secrets and Local Paths: no
hardcoded local absolute paths), so the manifest never stores an absolute
frame path -- only a path relative to whatever `--logs-root` the caller
points at, plus a content hash. `materialize_frame` fails loudly (never
silently skips or substitutes) when a frame is missing or has drifted from
the manifest's pinned hash.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from reasoning.vlm.capability_probes.models import ProbeItem, ProbeManifest
from reasoning.vlm.capability_probes.models_v2 import ProbeItemV2, ProbeManifestV2

_HASH_CHUNK_BYTES = 1 << 16


def sha256_file(path: Path) -> str:
    """Return the hex SHA-256 of a file's contents."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(_HASH_CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest(path: Path) -> ProbeManifest:
    """Load and validate a frozen manifest file.

    Args:
        path: Path to the manifest JSON.

    Returns:
        The validated manifest.
    """
    return ProbeManifest.model_validate_json(path.read_text(encoding="utf-8"))


def load_manifest_v2(path: Path) -> ProbeManifestV2:
    """Load and validate a frozen battery-v2 manifest file."""
    return ProbeManifestV2.model_validate_json(path.read_text(encoding="utf-8"))


def load_any_manifest(path: Path) -> ProbeManifest | ProbeManifestV2:
    """Load a v1 or v2 manifest, chosen by its `manifest_version` field."""
    text = path.read_text(encoding="utf-8")
    if '"manifest_version": 2' in text:
        return ProbeManifestV2.model_validate_json(text)
    return ProbeManifest.model_validate_json(text)


def save_manifest(manifest: ProbeManifest, path: Path) -> None:
    """Write a manifest as pretty-printed, newline-terminated JSON.

    Args:
        manifest: The manifest to write.
        path: Destination path; parent directories are not created.
    """
    path.write_text(manifest.model_dump_json(indent=2) + "\n", encoding="utf-8")


def materialize_frame(item: ProbeItem | ProbeItemV2, logs_root: Path) -> Path:
    """Resolve and content-verify one item's source frame under `logs_root`.

    Args:
        item: The manifest item.
        logs_root: Root the item's `frame_relpath` is relative to (the
            caller's `data/logs/vm_runs`, or a copy of it).

    Returns:
        The verified frame path.

    Raises:
        FileNotFoundError: `logs_root / item.frame_relpath` does not exist.
        ValueError: The file exists but its content hash no longer matches
            `item.frame_sha256` (the source run log was altered since freeze).
    """
    path = logs_root / item.frame_relpath
    if not path.is_file():
        raise FileNotFoundError(
            f"capability probe item {item.item_id!r}: frame not found at {path} "
            f"(expected sha256 {item.frame_sha256}); is --logs-root correct?"
        )
    actual = sha256_file(path)
    if actual != item.frame_sha256:
        raise ValueError(
            f"capability probe item {item.item_id!r}: frame at {path} has sha256 "
            f"{actual}, manifest expects {item.frame_sha256} -- the source run log "
            "has changed since the battery was frozen"
        )
    return path
