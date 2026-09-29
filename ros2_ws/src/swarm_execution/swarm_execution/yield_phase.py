"""The yield's phase vocabulary shared by the command bus and the safety monitor.

A yield publishes ACTIVE statuses in order: the backup leg (from
`Nav2Adapter.backup`), the pull-off sidestep, then the hold during which the
passers cross. The safety monitor reads the status `detail` as the yield's
phase (`safety.CoordinationTracker`), so the publishers and the reader import
the same constants.
"""
from __future__ import annotations

BACKUP_STARTED_DETAIL = "backup started"
PULL_OFF_DETAIL = "pulling off aisle centerline"
HOLD_STARTED_DETAIL = "holding for passing robot"
# The details before the hold: the yielder is still backing away.
YIELD_BACKUP_PHASE_DETAILS: frozenset[str] = frozenset({BACKUP_STARTED_DETAIL, PULL_OFF_DETAIL})
