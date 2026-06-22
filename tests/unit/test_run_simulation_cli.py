import sys
import types
from pathlib import Path

from isaac.scripts import run_simulation as cli
from isaac.vgu_sim.config import RunResult


def test_cli_passes_absolute_scenario_usd_path_to_runner(monkeypatch):
    captured = {}
    fake_runner = types.ModuleType("isaac.vgu_sim.runner")

    def fake_run_simulation(config):
        captured["scenario_path"] = config.scenario_path
        return (
            RunResult(
                run_id="fake",
                repetition=0,
                completed=True,
                elapsed_simulation_sec=0.0,
                manifest_path=Path("manifest.json"),
                failure=None,
            ),
        )

    fake_runner.run_simulation = fake_run_simulation
    monkeypatch.setitem(sys.modules, "isaac.vgu_sim.runner", fake_runner)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_simulation",
            "--scenario",
            "head_on_deadlock",
            "--headless",
            "--duration-sec",
            "1",
        ],
    )

    cli.main()

    assert captured["scenario_path"].is_absolute()
