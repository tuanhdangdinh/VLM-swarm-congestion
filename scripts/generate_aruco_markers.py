#!/usr/bin/env python3
"""Generate ArUco marker PNGs for the simulated robots.

Run in the project venv (needs cv2.aruco; NOT Isaac's embedded python):
    python -m scripts.generate_aruco_markers

The dictionary is read from M1's aruco.yaml so the simulator and M1 cannot
desync. Output goes to isaac/assets/markers/<slug>/marker_<id>.png.
"""
from __future__ import annotations

import argparse
from collections.abc import Iterable
from pathlib import Path

import cv2

from isaac.vgu_sim.paths import aruco_dict_name, marker_assets_dir


def _dict_const(dictionary_name: str) -> int:
    const = getattr(cv2.aruco, dictionary_name, None)
    if not isinstance(const, int):
        raise ValueError(f"Unsupported ArUco dictionary name: {dictionary_name!r}")
    return const


def generate_markers(
    dictionary_name: str,
    out_dir: Path,
    *,
    ids: Iterable[int] = range(1, 50),
    side_px: int = 512,
    quiet_px: int = 64,
) -> None:
    """Write deterministic marker PNGs (black marker + white quiet zone)."""
    aruco_dict = cv2.aruco.getPredefinedDictionary(_dict_const(dictionary_name))
    out_dir.mkdir(parents=True, exist_ok=True)
    for marker_id in ids:
        marker = cv2.aruco.generateImageMarker(aruco_dict, marker_id, side_px)
        bordered = cv2.copyMakeBorder(
            marker, quiet_px, quiet_px, quiet_px, quiet_px,
            cv2.BORDER_CONSTANT, value=255,  # white quiet zone for detection
        )
        cv2.imwrite(str(out_dir / f"marker_{marker_id}.png"), bordered)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate ArUco marker PNGs")
    parser.add_argument("--side-px", type=int, default=512)
    args = parser.parse_args()
    name = aruco_dict_name()
    out = marker_assets_dir(name)
    generate_markers(name, out, side_px=args.side_px)
    print(f"Wrote markers for {name} to {out}")


if __name__ == "__main__":
    main()
