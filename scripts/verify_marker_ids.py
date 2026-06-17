#!/usr/bin/env python3
"""Pre-flight for plan Task 10: assert M1 detects the CORRECT marker id per robot.

The Task-10 acceptance is id-match, not "non-empty": a mirrored UV quad still
produces a non-empty `/perception/scene_state`, but the markers decode to the
wrong ids. This script compares the robot ids in one scene_state message against
the ids the scenario config expects (derived from each robot's `marker_id`) and
exits non-zero on any missing or extra id.

Usage on the Isaac box (with perception running):
    python -m scripts.verify_marker_ids --scenario isaac/config/scenarios/head_on_deadlock.yaml

Offline (e.g. against a captured payload, no ROS2):
    ros2 topic echo /perception/scene_state --field data --once > scene.json
    python -m scripts.verify_marker_ids --scenario <cfg>.yaml --from-json scene.json
    # or pipe the JSON on stdin with --from-json -
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class IdCheck:
    """Result of comparing detected scene ids against the expected ids."""

    expected: frozenset[str]
    detected: frozenset[str]

    @property
    def matched(self) -> list[str]:
        return sorted(self.expected & self.detected)

    @property
    def missing(self) -> list[str]:
        return sorted(self.expected - self.detected)

    @property
    def extra(self) -> list[str]:
        return sorted(self.detected - self.expected)

    @property
    def ok(self) -> bool:
        # Non-empty guard: a config with no robots must not vacuously pass.
        return bool(self.expected) and not self.missing and not self.extra


def expected_robot_ids_from_config(config: dict) -> set[str]:
    """Expected scene-state robot ids for a scenario config.

    M1 names each robot `robot_<decoded_marker_id>`, so the expected identity is
    derived from `marker_id` (what the marker must decode to), not the config's
    `robot_id` field.

    Args:
        config: Parsed scenario config mapping with a `robots` list.

    Returns:
        The set of expected `robot_<marker_id>` ids.
    """
    return {f"robot_{r['marker_id']}" for r in config.get("robots", [])}


def check_scene_ids(scene_json: dict, expected: set[str]) -> IdCheck:
    """Compare the robot ids in a scene_state payload against the expected set.

    Args:
        scene_json: Parsed `SceneState` JSON (has a `robots` list of dicts).
        expected: Expected `robot_<marker_id>` ids.

    Returns:
        An `IdCheck` describing matched, missing, and extra ids.
    """
    detected = {r["robot_id"] for r in scene_json.get("robots", [])}
    return IdCheck(expected=frozenset(expected), detected=frozenset(detected))


def _load_scene_from_json(source: str) -> dict:
    text = sys.stdin.read() if source == "-" else Path(source).read_text()
    return json.loads(text)


def _grab_scene_state_via_ros(topic: str, timeout_sec: float) -> dict:
    # Imported lazily so the pure logic and its tests run without a ROS2 install.
    import rclpy
    from rclpy.node import Node
    from std_msgs.msg import String

    rclpy.init()
    try:
        node = Node("verify_marker_ids")
        received: dict = {}

        def _on_msg(msg: String) -> None:
            received["data"] = msg.data

        node.create_subscription(String, topic, _on_msg, 10)
        deadline = node.get_clock().now().nanoseconds + int(timeout_sec * 1e9)
        while "data" not in received:
            if node.get_clock().now().nanoseconds > deadline:
                raise TimeoutError(
                    f"No message on {topic} within {timeout_sec:.0f}s — is perception running?"
                )
            rclpy.spin_once(node, timeout_sec=0.1)
        node.destroy_node()
        return json.loads(received["data"])
    finally:
        rclpy.shutdown()


def _format_report(check: IdCheck) -> str:
    lines = ["per-robot marker-id check:"]
    for rid in sorted(check.expected | check.detected):
        if rid in check.expected and rid in check.detected:
            lines.append(f"  OK      {rid}")
        elif rid in check.expected:
            lines.append(f"  MISSING {rid}  (not detected — too small/occluded, or black texture)")
        else:
            lines.append(f"  EXTRA   {rid}  (wrong id — likely a mirrored/rotated UV quad)")
    lines.append("PASS" if check.ok else "FAIL")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", required=True, help="Scenario config YAML")
    parser.add_argument("--topic", default="/perception/scene_state")
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument(
        "--from-json",
        metavar="PATH",
        help="Read scene_state JSON from a file (or '-' for stdin) instead of ROS2",
    )
    args = parser.parse_args(argv)

    config = yaml.safe_load(Path(args.scenario).read_text())
    expected = expected_robot_ids_from_config(config)

    if args.from_json:
        scene = _load_scene_from_json(args.from_json)
    else:
        scene = _grab_scene_state_via_ros(args.topic, args.timeout)

    check = check_scene_ids(scene, expected)
    print(_format_report(check))
    return 0 if check.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
