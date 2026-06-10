from pathlib import Path

_ISAAC_ROOT = Path("isaac")
_ASSETS = _ISAAC_ROOT / "assets"
_SCENARIOS_OUT = _ISAAC_ROOT / "scenarios"
_CONFIG = _ISAAC_ROOT / "config"

_COMPONENT_NAMES = frozenset(
    {"rack_block", "loading_zone", "aisle_barrier", "dynamic_obstacle"}
)


def isaac_root() -> Path:
    """Return the root path of the Isaac Sim package directory.

    Returns:
        Relative path to isaac root.
    """
    return _ISAAC_ROOT


def robot_asset_path() -> Path:
    """Return the path to the TurtleBot3 Burger USD asset.

    Returns:
        Relative path to robot USDA file.
    """
    return _ASSETS / "robots" / "turtlebot3_burger" / "turtlebot3_burger.usda"


def warehouse_asset_path() -> Path:
    """Return the path to the warehouse base USD asset.

    Returns:
        Relative path to warehouse USD file.
    """
    return _ASSETS / "warehouse" / "warehouse_base.usd"


def component_asset_path(name: str) -> Path:
    """Return the path to a warehouse component asset.

    Known components: rack_block, loading_zone, aisle_barrier, dynamic_obstacle.

    Args:
        name: Component name (must be in known set).

    Returns:
        Relative path to component USD file.

    Raises:
        ValueError: If component name is not recognized.
    """
    if name not in _COMPONENT_NAMES:
        raise ValueError(f"Unknown component asset {name!r}; known: {sorted(_COMPONENT_NAMES)}")
    return _ASSETS / "warehouse" / f"{name}.usd"


def scenario_config_path(name: str) -> Path:
    """Return the path to a scenario YAML config.

    Args:
        name: Scenario name (e.g. 'head_on_deadlock').

    Returns:
        Relative path to scenario YAML config.
    """
    return _CONFIG / "scenarios" / f"{name}.yaml"


def scenario_output_path(name: str) -> Path:
    """Return the path to a scenario's generated USD output.

    Args:
        name: Scenario name (e.g. 'head_on_deadlock').

    Returns:
        Relative path to scenario USD file.
    """
    return _SCENARIOS_OUT / f"{name}.usd"


def run_output_dir(output_root: Path, scenario_name: str, seed: int, rep: int) -> Path:
    """Return the output directory for a single run.

    Naming convention: `<scenario_name>-seed<seed>-rep<rep:03d>`.

    Args:
        output_root: Root directory for all run outputs (e.g. `data/logs/simulation`).
        scenario_name: Name of the scenario.
        seed: Random seed for the run.
        rep: Replication index (0, 1, 2, ...).

    Returns:
        Path to run output directory.
    """
    return output_root / f"{scenario_name}-seed{seed}-rep{rep:03d}"
