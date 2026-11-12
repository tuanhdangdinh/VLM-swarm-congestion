"""Dependency direction: nothing under `reasoning/` imports the bench or the M5 package.

Shared bench/live code (per-cluster grouping, options, contract, joint check)
lives under `reasoning/`, so it must not reach back into `benchmarks` or
`swarm_orchestrator`. The check walks every import statement in the AST,
function-level ones included; docstrings and comments that merely mention
those names do not count.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REASONING = Path(__file__).resolve().parents[2] / "reasoning"
FORBIDDEN = frozenset({"benchmarks", "swarm_orchestrator"})
# The M2 contract modules the shared per-cluster path added; they stay
# importable without M3 so the M3 -> M2 direction is one-way.
M2_CONTRACT_MODULES = ("executable_options.py", "per_cluster_choice.py", "per_cluster_runner.py")


def _imported_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.append(node.module)
    return found


def _sources() -> list[Path]:
    return sorted(REASONING.rglob("*.py"))


def test_reasoning_tree_has_sources():
    assert any(p.name == "cluster_options.py" for p in _sources())


@pytest.mark.parametrize("path", _sources(), ids=lambda p: str(p.relative_to(REASONING)))
def test_reasoning_module_imports_neither_bench_nor_orchestrator(path: Path):
    bad = [m for m in _imported_modules(path) if m.split(".")[0] in FORBIDDEN]
    assert bad == []


@pytest.mark.parametrize("name", M2_CONTRACT_MODULES)
def test_shared_m2_contract_imports_no_m3(name: str):
    modules = _imported_modules(REASONING / "vlm" / name)
    assert not [m for m in modules if m.startswith("reasoning.rag")]
