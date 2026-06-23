from pathlib import Path

import yaml

_ISAAC_ROOT = Path("isaac")
_ASSETS = _ISAAC_ROOT / "assets"
_SCENARIOS_OUT = _ISAAC_ROOT / "scenarios"
_CONFIG = _ISAAC_ROOT / "config"

_COMPONENT_NAMES = frozenset(
    {"rack_block", "loading_zone", "aisle_barrier", "dynamic_obstacle"}
)


def isaac_root() -> Path:
    return _ISAAC_ROOT


def robot_asset_path() -> Path:
    return _ASSETS / "robots" / "turtlebot3_burger" / "turtlebot3_burger.usda"


def warehouse_asset_path() -> Path:
    return _ASSETS / "warehouse" / "warehouse_base.usd"


def component_asset_path(name: str) -> Path:
    # Raises ValueError if name not in: rack_block, loading_zone, aisle_barrier, dynamic_obstacle
    if name not in _COMPONENT_NAMES:
        raise ValueError(f"Unknown component asset {name!r}; known: {sorted(_COMPONENT_NAMES)}")
    return _ASSETS / "warehouse" / f"{name}.usd"


def obstacle_asset_path(asset_filename: str) -> Path:
    """Resolve a `timed_obstacles[].asset` filename to its USD file.

    Args:
        asset_filename: The `asset` field from a scenario YAML's
            `timed_obstacles` entry, e.g. `"dynamic_obstacle.usd"`.

    Returns:
        Path to the asset under `isaac/assets/obstacles/`.
    """
    return _ASSETS / "obstacles" / asset_filename


def scenario_config_path(name: str) -> Path:
    return _CONFIG / "scenarios" / f"{name}.yaml"


def scenario_output_path(name: str) -> Path:
    return _SCENARIOS_OUT / f"{name}.usd"


def run_output_dir(output_root: Path, scenario_name: str, seed: int, rep: int) -> Path:
    return output_root / f"{scenario_name}-seed{seed}-rep{rep:03d}"


# Single source of truth for the ArUco dictionary: M1's perception config. Both
# the generator and the scenario authoring resolve the dictionary from here.
ARUCO_CONFIG_PATH = Path("ros2_ws/src/swarm_perception/config/aruco.yaml")


def aruco_dict_name(config_path: Path = ARUCO_CONFIG_PATH) -> str:
    cfg = yaml.safe_load(config_path.read_text())
    return cfg["aruco"]["dictionary"]


def marker_dict_slug(dictionary_name: str) -> str:
    return "aruco_" + dictionary_name.removeprefix("DICT_").lower()


def marker_assets_dir(dictionary_name: str) -> Path:
    return _ASSETS / "markers" / marker_dict_slug(dictionary_name)


def marker_png_path(dictionary_name: str, marker_id: int) -> Path:
    return marker_assets_dir(dictionary_name) / f"marker_{marker_id}.png"
