from pathlib import Path

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


def scenario_config_path(name: str) -> Path:
    return _CONFIG / "scenarios" / f"{name}.yaml"


def scenario_output_path(name: str) -> Path:
    return _SCENARIOS_OUT / f"{name}.usd"


def run_output_dir(output_root: Path, scenario_name: str, seed: int, rep: int) -> Path:
    return output_root / f"{scenario_name}-seed{seed}-rep{rep:03d}"
