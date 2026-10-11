"""prereg-v3 A26(ii), B3: fail a clearing backup fast on a fresh safety latch.

The A25 no-admit diagnosis (mechanism B): a bystander walked into a yield's
retreat, the safety monitor latched it with the backing yielder, and since
both members of a latch are held and it only releases at `min_distance_m`
separation, both robots froze until M4's motion deadline (148-211 s). The
A19 command-start waiver means a clearing robot is never held by a latch it
STARTED in, so the clearing robot showing up in `/safety/holds` after its
command started is a latch formed during the maneuver.

`FreshLatchWatch` turns `/safety/holds` into that verdict, ROS2-free: the
command bus feeds it every holds message, arms it when a flagged clearing
command starts its backup, and the backup/pull-off primitives poll `check`
on their own 20 Hz tick (`Nav2Adapter.backup(abort_check=...)`).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable

FRESH_LATCH_DETAIL_PREFIX = "fresh latch fast-fail"
# prereg-v3 A27(iii): the command bus's one structured log line per firing,
# so a live B3 is measured, not inferred from the step's timing.
FAST_FAIL_LOG_EVENT = "b3_fast_fail"
# How long the clearing robot must stay held before the step fails: long
# enough to ride out a one-scene flicker, far below the 148-211 s deadline.
DEFAULT_DEBOUNCE_SEC = 2.0


def fast_fail_log_line(
    command_id: str,
    robot_id: str,
    phase: str,
    elapsed_s: float,
    deadline_s: float,
    sim_t: float,
    detail: str,
) -> str:
    """The structured key-value log line for one B3 firing (A27(iii)).

    Args:
        command_id: The clearing command.
        robot_id: The clearing robot.
        phase: `backup` or `pull_off`.
        elapsed_s: Wall seconds from the step's start to the firing.
        deadline_s: The step's own motion deadline, wall seconds after its
            start (`nav2_adapter.backup_deadline_sec` / `sidestep_deadline_sec`).
        sim_t: Sim time of the firing.
        detail: `FreshLatchWatch.check`'s FAILED detail.

    Returns:
        `b3_fast_fail command=... robot=... phase=... elapsed_s=...
        deadline_s=... saved_s=... sim_t=... detail="..."`.
    """
    return (
        f"{FAST_FAIL_LOG_EVENT} command={command_id} robot={robot_id} phase={phase} "
        f"elapsed_s={elapsed_s:.1f} deadline_s={deadline_s:.1f} "
        f"saved_s={deadline_s - elapsed_s:.1f} sim_t={sim_t:.3f} detail=\"{detail}\""
    )


class FreshLatchWatch:
    """Track which robots the safety monitor holds, and since when.

    Times are caller-supplied (the command bus passes `time.monotonic()`),
    so tests drive it with plain floats.
    """

    def __init__(self, debounce_sec: float = DEFAULT_DEBOUNCE_SEC) -> None:
        if debounce_sec < 0.0:
            raise ValueError(f"debounce_sec must be >= 0, got {debounce_sec}")
        self._debounce = debounce_sec
        # robot -> time it entered the current continuous hold
        self._held_since: dict[str, float] = {}
        # robot -> (command_id, arm time, robots already held at arm time)
        self._armed: dict[str, tuple[str, float, frozenset[str]]] = {}

    def on_holds(self, held: Iterable[str], now: float) -> None:
        """Record one `/safety/holds` payload.

        Args:
            held: Robot ids the safety monitor currently holds.
            now: Receipt time.
        """
        current = set(held)
        for robot_id in list(self._held_since):
            if robot_id not in current:
                del self._held_since[robot_id]
        for robot_id in current:
            self._held_since.setdefault(robot_id, now)

    def arm(self, robot_id: str, command_id: str, now: float) -> None:
        """Start watching a clearing robot at its command's motion start.

        Args:
            robot_id: The clearing robot.
            command_id: Its command.
            now: Arm time.
        """
        self._armed[robot_id] = (command_id, now, frozenset(self._held_since))

    def disarm(self, robot_id: str, command_id: str | None = None) -> None:
        """Stop watching `robot_id` (only for `command_id`, when given)."""
        armed = self._armed.get(robot_id)
        if armed is not None and (command_id is None or armed[0] == command_id):
            del self._armed[robot_id]

    def check(self, robot_id: str, now: float, phase: str) -> str | None:
        """Return a FAILED detail when the clearing robot is freshly latched.

        Args:
            robot_id: The clearing robot.
            now: Current time.
            phase: The primitive being run (`backup` or `pull_off`), for the
                detail text.

        Returns:
            None unless the robot is armed, is held, entered that hold after
            the arm time, and has stayed held for the debounce. The detail
            names the other robots that entered a hold since the arm time
            (`co_held`, the likely partner; the monitor publishes no pairs).
        """
        armed = self._armed.get(robot_id)
        since = self._held_since.get(robot_id)
        if armed is None or since is None:
            return None
        _command_id, armed_at, held_at_arm = armed
        if robot_id in held_at_arm or since < armed_at:
            return None
        held_for = now - since
        if held_for < self._debounce:
            return None
        co_held = sorted(
            other
            for other, other_since in self._held_since.items()
            if other != robot_id and other not in held_at_arm and other_since >= armed_at
        )
        return (
            f"{FRESH_LATCH_DETAIL_PREFIX}: {robot_id} latched during {phase} "
            f"held_for={held_for:.1f}s co_held={','.join(co_held) or '-'}"
        )

    def checker(
        self, robot_id: str, phase: str, clock: Callable[[], float]
    ) -> Callable[[], str | None]:
        """A zero-argument abort check for one primitive (`Nav2Adapter` ticks it).

        Args:
            robot_id: The clearing robot.
            phase: `backup` or `pull_off`.
            clock: The time source `on_holds`/`arm` were fed with.

        Returns:
            A callable returning `check(robot_id, clock(), phase)`.
        """
        return lambda: self.check(robot_id, clock(), phase)
