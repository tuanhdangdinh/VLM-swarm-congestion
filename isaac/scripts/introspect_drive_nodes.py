"""Headless OmniGraph node-interface capture for M4 Phase 1 (plan Task 1).

Runs inside Isaac Sim's Python (``python.sh``). For each drive/TF/odometry node
type the Phase 1 graph needs, it creates one instance in a throwaway graph and
prints the exact ``inputs:``/``outputs:`` attribute names, so the wiring in
``ros_graphs.py`` transcribes verified keys instead of guesses
(CLAUDE.md external-library-verification). Headless replacement for the GUI
"ROS 2 OmniGraphs" wizard the plan originally assumed.

Usage on the host:
    $ISAAC_SIM_ROOT/python.sh isaac/scripts/introspect_drive_nodes.py
"""
from __future__ import annotations

from isaacsim import SimulationApp

_app = SimulationApp({"headless": True})

import omni.graph.core as og  # noqa: E402
from isaacsim.core.utils.extensions import enable_extension  # noqa: E402

for _ext in (
    "isaacsim.core.nodes",
    "isaacsim.ros2.bridge",
    "isaacsim.robot.wheeled_robots",
):
    try:
        enable_extension(_ext)
    except Exception as exc:  # pragma: no cover - host diagnostics
        print(f"[ext] FAILED to enable {_ext}: {exc}")

# Candidate node types the Phase 1 drive+sense+TF graph needs.
CANDIDATES = [
    "isaacsim.ros2.bridge.ROS2SubscribeTwist",
    "isaacsim.robot.wheeled_robots.DifferentialController",
    "isaacsim.core.nodes.IsaacArticulationController",
    "isaacsim.core.nodes.IsaacComputeOdometry",
    "isaacsim.ros2.bridge.ROS2PublishOdometry",
    "isaacsim.ros2.bridge.ROS2PublishTransformTree",
    "isaacsim.ros2.bridge.ROS2PublishRawTransformTree",
]

# Keywords to search the registry with when a candidate type name is wrong.
SEARCH_HINTS = ["Twist", "Differential", "ArticulationController", "Odometry", "Transform"]


def _all_registered_type_names() -> list[str]:
    """Best-effort enumeration of registered OmniGraph node type names."""
    for getter in ("get_node_type_names", "get_registered_nodes"):
        fn = getattr(og, getter, None)
        if fn is None:
            continue
        try:
            return list(fn())
        except Exception:
            continue
    # Fallback: walk the registry object if present.
    reg = getattr(og, "get_node_registry", None)
    if reg is not None:
        try:
            return list(reg().get_node_type_names())
        except Exception:
            pass
    return []


def _dump_node_type(type_name: str, idx: int) -> bool:
    """Create one node of ``type_name`` and print its attributes. Return success."""
    graph_path = f"/World/Introspect_{idx}"
    try:
        og.Controller.edit(
            {"graph_path": graph_path, "evaluator_name": "execution"},
            {og.Controller.Keys.CREATE_NODES: [("n", type_name)]},
        )
    except Exception as exc:
        print(f"\n### {type_name}\n  CREATE FAILED: {exc}")
        return False

    graph = og.get_graph_by_path(graph_path)
    node = graph.get_node(f"{graph_path}/n")
    print(f"\n### {type_name}")
    inputs, outputs, state = [], [], []
    for attr in node.get_attributes():
        name = attr.get_name()
        try:
            tname = attr.get_resolved_type().get_type_name()
        except Exception:
            tname = "?"
        entry = f"    {name}  ({tname})"
        if name.startswith("inputs:"):
            inputs.append(entry)
        elif name.startswith("outputs:"):
            outputs.append(entry)
        else:
            state.append(entry)
    print("  inputs:")
    print("\n".join(inputs) or "    (none)")
    print("  outputs:")
    print("\n".join(outputs) or "    (none)")
    if state:
        print("  state/other:")
        print("\n".join(state))
    return True


def main() -> None:
    print("=" * 70)
    print("M4 PHASE 1 — VERIFIED OMNIGRAPH NODE INTERFACE")
    print("=" * 70)

    failed: list[str] = []
    for idx, type_name in enumerate(CANDIDATES):
        if not _dump_node_type(type_name, idx):
            failed.append(type_name)

    if failed:
        registered = _all_registered_type_names()
        print("\n" + "=" * 70)
        print(f"REGISTRY SEARCH (for {len(failed)} failed candidate(s))")
        print(f"  total registered types discovered: {len(registered)}")
        for hint in SEARCH_HINTS:
            hits = sorted(t for t in registered if hint.lower() in t.lower())
            print(f"\n  matches for '{hint}':")
            for h in hits:
                print(f"    {h}")

    print("\n" + "=" * 70)
    print("DONE")


main()
_app.close()
