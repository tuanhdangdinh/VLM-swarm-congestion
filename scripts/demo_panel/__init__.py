"""Offline demo-video renderer for archived run bundles.

Left pane: the scene (a camera recording when one exists, otherwise a
top-down reconstruction from ground-truth poses, labelled as such). Right
pane: a terminal replaying the bundle's own log lines in sync with sim time,
selected by one fixed filter command, plus real read-only `jq`/`grep` commands
on the bundle's decision artifacts and cost log with their actual output.
"""

from scripts.demo_panel.models import TerminalItem, TimeMapInfo, Transcript

__all__ = ["TerminalItem", "TimeMapInfo", "Transcript"]
