"""Execution-side stall abort for M4's raw-cmd_vel primitives (ROS2-free).

Report: docs/reports/2026-11-15-m4-stall-abort.md.

M4's `backup`, `sidestep` (pull-off) and `drive_heading` (escort) publish raw
`Twist` on `/<robot>/cmd_vel`, which bypasses Nav2's collision monitor. They
end only on their odometry target or on an OS-monotonic deadline of
`max(15 x naive, 30 s)` wall seconds. A robot driven into an undeclared
obstacle therefore keeps its wheels commanded until that deadline: 335 wall-s
for the m5D escort into rack island `obstacle_2`, 195 wall-s for each of
seven October reverses pinned on a rack face.

`StallDetector` flags commanded motion without corresponding measured
motion. Its inputs are the command each primitive actually publishes, gated
to zero while the robot is under a safety hold (the Isaac relay then sends
zero to the wheels whatever `/cmd_vel` says), and the robot's own `/odom`.
In the Isaac setup `/odom` is `IsaacComputeOdometry` on the chassis prim, a
physics pose rather than wheel integration, so it reads "no movement" when
the chassis is pinned.

Time base: sim seconds throughout. Command samples carry the node clock
(`use_sim_time`) and odometry carries its header stamp, both Isaac sim time,
so the verdict is the same at any real-time factor. A frozen sim stays the
monotonic deadline's job.

Verdicts:

- `stall`: over the last `window_s` of odometry, in one commanded mode
  (linear or turn-in-place) held for longer than `grace_s`, the measured net
  progress fell below `min_progress_ratio` times the commanded progress.
- `input_stale`: no fresh odometry for more than `stale_input_s` (or none
  since the primitive started). A stale measurement is read neither as "no
  movement" nor as "moving"; it is its own abort reason.
"""
from __future__ import annotations

import math
from collections import deque
from collections.abc import Callable, Mapping
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

STALL_ABORT_DETAIL_PREFIX = "stall_abort:"
STALL_ABORT_LOG_EVENT = "stall abort"

Mode = Literal["linear", "angular", "idle"]


class StallAbortConfig(BaseModel):
    """Stall-abort parameters, from `safety.stall_abort` in the M4 safety file.

    Every time is in sim seconds. Derivation from recorded runs: report
    section 4.

    Attributes:
        enabled: Master switch; off by default.
        window_s: Length of the progress window.
        min_progress_ratio: Stall when measured progress is below this
            fraction of commanded progress over the window.
        grace_s: Time after a commanded mode starts (primitive start, phase
            change, safety-hold release) before the first window may begin;
            covers the drive's ramp-up.
        stale_input_s: Odometry older than this is stale.
        min_linear_mps: Below this |linear| command the sample is not linear
            motion.
        min_angular_radps: Below this |angular| command (with no linear
            command) the sample is not a turn.
        min_expected_m: A linear window commanding less net travel is not
            judged.
        min_expected_rad: A turn window commanding less net rotation is not
            judged.
    """

    # Unknown keys are rejected: a typo in the fragment must not run with
    # the defaults silently.
    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = False
    window_s: float = Field(default=3.0, gt=0.0)
    min_progress_ratio: float = Field(default=0.25, gt=0.0, lt=1.0)
    grace_s: float = Field(default=1.5, ge=0.0)
    stale_input_s: float = Field(default=1.0, gt=0.0)
    min_linear_mps: float = Field(default=0.03, gt=0.0)
    min_angular_radps: float = Field(default=0.15, gt=0.0)
    min_expected_m: float = Field(default=0.06, gt=0.0)
    min_expected_rad: float = Field(default=0.3, gt=0.0)

    @model_validator(mode="after")
    def _window_fits_stale_bound(self) -> StallAbortConfig:
        if self.stale_input_s >= self.window_s + self.grace_s:
            raise ValueError("stale_input_s must be shorter than window_s + grace_s")
        return self


class StallVerdict(BaseModel):
    """One abort decision with the numbers that justify it.

    Attributes:
        outcome: `stall` or `input_stale`.
        mode: `linear` or `angular` for a stall; the mode in force for
            `input_stale` (`idle` when nothing was commanded).
        window_s: Odometry interval the stall was judged over (0 for stale).
        commanded_rate: Mean |command| over the window, m/s or rad/s.
        commanded: Commanded net progress over the window, m or rad.
        measured: Measured net progress over the window, m or rad.
        expected_min: `min_progress_ratio * commanded`.
        odom_age_s: Sim seconds since the last odometry (None for a stall).
        stale_bound_s: The stale bound in force.
    """

    model_config = ConfigDict(frozen=True)

    outcome: Literal["stall", "input_stale"]
    mode: Mode
    window_s: float = 0.0
    commanded_rate: float = 0.0
    commanded: float = 0.0
    measured: float = 0.0
    expected_min: float = 0.0
    odom_age_s: float | None = None
    stale_bound_s: float = 0.0

    def detail(self) -> str:
        """The FAILED status detail for this verdict.

        Returns:
            E.g. `stall_abort: commanded 0.100 m/s for 3.0 s, measured 0.004 m
            (expected >= 0.075 m)`, or `stall_abort: input_stale no odometry
            for 1.05 s (bound 1.00 s)`.
        """
        if self.outcome == "input_stale":
            age = "none since start" if self.odom_age_s is None else f"{self.odom_age_s:.2f} s"
            return (
                f"{STALL_ABORT_DETAIL_PREFIX} input_stale no odometry for {age} "
                f"(bound {self.stale_bound_s:.2f} s)"
            )
        if self.mode == "angular":
            rate_unit, unit = "rad/s", "rad"
        else:
            rate_unit, unit = "m/s", "m"
        return (
            f"{STALL_ABORT_DETAIL_PREFIX} commanded {self.commanded_rate:.3f} {rate_unit} "
            f"for {self.window_s:.1f} s, measured {self.measured:.3f} {unit} "
            f"(expected >= {self.expected_min:.3f} {unit})"
        )


def _wrap(angle: float) -> float:
    return math.atan2(math.sin(angle), math.cos(angle))


class StallDetector:
    """Sliding-window stall detector over commanded and measured motion.

    Feed it every odometry sample (`on_odom`) and every primitive tick
    (`observe`, with the command about to be published). Command samples are
    piecewise constant from their tick to the next.
    """

    def __init__(self, config: StallAbortConfig) -> None:
        self._cfg = config
        # (t, v, w) of the effective command, held-gated.
        self._commands: deque[tuple[float, float, float]] = deque()
        # (stamp, x, y, unwrapped yaw).
        self._poses: deque[tuple[float, float, float, float]] = deque()
        self._mode: Mode | None = None
        self._mode_start: float | None = None
        self._first_observe: float | None = None
        self._horizon = config.window_s + config.grace_s + 1.0
        # Smallest measured/commanded progress ratio judged so far, per mode:
        # the replay's margin to firing.
        self.min_ratio_seen: dict[str, float] = {}

    @property
    def latest_odom_stamp(self) -> float | None:
        """Stamp of the newest accepted odometry sample, or None."""
        return self._poses[-1][0] if self._poses else None

    def on_odom(self, stamp_s: float, x: float, y: float, yaw: float) -> None:
        """Record one odometry sample; out-of-order or repeated stamps are ignored.

        Args:
            stamp_s: Header stamp, sim seconds.
            x: Position in the odom frame, metres.
            y: Position in the odom frame, metres.
            yaw: Heading, radians.
        """
        if self._poses and stamp_s <= self._poses[-1][0]:
            return
        if self._poses:
            unwrapped = self._poses[-1][3] + _wrap(yaw - self._poses[-1][3])
        else:
            unwrapped = yaw
        self._poses.append((stamp_s, x, y, unwrapped))
        self._prune(stamp_s)

    def _classify(self, v: float, w: float) -> Mode:
        if abs(v) >= self._cfg.min_linear_mps:
            return "linear"
        if abs(w) >= self._cfg.min_angular_radps:
            return "angular"
        return "idle"

    def _prune(self, now: float) -> None:
        cutoff = now - self._horizon
        # Keep one sample at or before the cutoff so a window start can still
        # find its pose and its piecewise-constant command.
        while len(self._poses) > 1 and self._poses[1][0] <= cutoff:
            self._poses.popleft()
        while len(self._commands) > 1 and self._commands[1][0] <= cutoff:
            self._commands.popleft()

    def _integral(self, start: float, end: float, index: int) -> float:
        total = 0.0
        commands = list(self._commands)
        for i, (t, v, w) in enumerate(commands):
            seg_start = max(t, start)
            seg_end = min(commands[i + 1][0] if i + 1 < len(commands) else end, end)
            if seg_end > seg_start:
                total += (v, w)[index] * (seg_end - seg_start)
        return total

    def observe(
        self, now_s: float, linear: float, angular: float, held: bool = False
    ) -> StallVerdict | None:
        """Record the command about to be published and judge the window.

        Args:
            now_s: Node clock, sim seconds.
            linear: Commanded linear x, m/s.
            angular: Commanded angular z, rad/s.
            held: True while the robot is under a safety hold; the wheels then
                receive zero, so the effective command is zero.

        Returns:
            A verdict to abort on, or None.
        """
        if self._first_observe is None:
            self._first_observe = now_s
        v, w = (0.0, 0.0) if held else (float(linear), float(angular))
        mode = self._classify(v, w)
        if mode != self._mode:
            self._mode = mode
            self._mode_start = now_s
        if not self._commands or now_s > self._commands[-1][0]:
            self._commands.append((now_s, v, w))
        else:
            self._commands[-1] = (self._commands[-1][0], v, w)
        self._prune(now_s)

        latest = self.latest_odom_stamp
        reference = latest if latest is not None else self._first_observe
        age = now_s - reference
        if age > self._cfg.stale_input_s:
            return StallVerdict(
                outcome="input_stale",
                mode=mode,
                odom_age_s=None if latest is None else age,
                stale_bound_s=self._cfg.stale_input_s,
            )
        if mode == "idle" or latest is None:
            return None
        return self._judge(mode)

    def _judge(self, mode: Mode) -> StallVerdict | None:
        cfg = self._cfg
        end = self._poses[-1]
        earliest = self._mode_start + cfg.grace_s
        target = end[0] - cfg.window_s
        if target < earliest:
            return None
        start = None
        for pose in self._poses:
            if pose[0] <= target:
                start = pose
            else:
                break
        if start is None or start[0] < earliest:
            return None
        span = end[0] - start[0]
        if mode == "linear":
            commanded = abs(self._integral(start[0], end[0], 0))
            measured = math.hypot(end[1] - start[1], end[2] - start[2])
            floor = cfg.min_expected_m
        else:
            signed = self._integral(start[0], end[0], 1)
            commanded = abs(signed)
            measured = (end[3] - start[3]) * (1.0 if signed >= 0.0 else -1.0)
            floor = cfg.min_expected_rad
        if commanded < floor:
            return None
        ratio = measured / commanded
        if ratio < self.min_ratio_seen.get(mode, math.inf):
            self.min_ratio_seen[mode] = ratio
        expected_min = cfg.min_progress_ratio * commanded
        if measured >= expected_min:
            return None
        return StallVerdict(
            outcome="stall",
            mode=mode,
            window_s=span,
            commanded_rate=commanded / span if span > 0.0 else 0.0,
            commanded=commanded,
            measured=measured,
            expected_min=expected_min,
            stale_bound_s=cfg.stale_input_s,
        )


class StallWatch:
    """One primitive's stall detector, bound to its robot, command and logger.

    Built per raw-cmd_vel primitive by the command bus and handed to the
    `Nav2Adapter` primitive, which feeds it odometry and its own published
    command on every tick. Fires at most once.
    """

    def __init__(
        self,
        config: StallAbortConfig,
        robot_id: str,
        command_id: str,
        primitive: str,
        is_held: Callable[[], bool] | None = None,
        log: Callable[[str], None] | None = None,
    ) -> None:
        self._detector = StallDetector(config)
        self._robot_id = robot_id
        self._command_id = command_id
        self._primitive = primitive
        self._is_held = is_held
        self._log = log
        self._fired = False
        self.verdict: StallVerdict | None = None

    @property
    def detector(self) -> StallDetector:
        """The underlying detector (for replay diagnostics)."""
        return self._detector

    def on_odom(self, stamp_s: float, x: float, y: float, yaw: float) -> None:
        """Forward one odometry sample (see `StallDetector.on_odom`)."""
        self._detector.on_odom(stamp_s, x, y, yaw)

    def observe(self, now_s: float, linear: float, angular: float, phase: str) -> str | None:
        """Judge one tick; on the first verdict log it and return the FAILED detail.

        Args:
            now_s: Node clock, sim seconds.
            linear: Linear command about to be published (0 when the
                primitive publishes nothing this tick).
            angular: Angular command about to be published.
            phase: The primitive's phase, for the log line.

        Returns:
            The `stall_abort: ...` detail on the firing tick, else None.
        """
        if self._fired:
            return None
        held = self._is_held() if self._is_held is not None else False
        verdict = self._detector.observe(now_s, linear, angular, held=held)
        if verdict is None:
            return None
        self._fired = True
        self.verdict = verdict
        if self._log is not None:
            self._log(
                stall_abort_log_line(
                    self._command_id, self._robot_id, self._primitive, phase, verdict, now_s
                )
            )
        return verdict.detail()


def stall_abort_log_line(
    command_id: str,
    robot_id: str,
    primitive: str,
    phase: str,
    verdict: StallVerdict,
    sim_t: float,
) -> str:
    """The one key-value M4 log line per abort, for scorers.

    Args:
        command_id: The coordination command.
        robot_id: The robot whose primitive was aborted.
        primitive: `backup`, `pull_off` or `escort`.
        phase: The primitive's phase at the abort.
        verdict: The detector's verdict.
        sim_t: Sim time of the abort.

    Returns:
        `stall abort robot=... command=... primitive=... phase=... reason=...`
        then `mode=`, `commanded_m=`/`measured_m=`/`expected_min_m=` (or the
        `_rad` keys for a turn), `window_s=`, `commanded_rate=`, `sim_t=`;
        for `input_stale`, `odom_age_s=` and `bound_s=` instead.
    """
    head = (
        f"{STALL_ABORT_LOG_EVENT} robot={robot_id} command={command_id} "
        f"primitive={primitive} phase={phase} reason={verdict.outcome} mode={verdict.mode}"
    )
    if verdict.outcome == "input_stale":
        age = "none" if verdict.odom_age_s is None else f"{verdict.odom_age_s:.2f}"
        return f"{head} odom_age_s={age} bound_s={verdict.stale_bound_s:.2f} sim_t={sim_t:.3f}"
    unit = "rad" if verdict.mode == "angular" else "m"
    return (
        f"{head} commanded_{unit}={verdict.commanded:.3f} measured_{unit}={verdict.measured:.3f} "
        f"expected_min_{unit}={verdict.expected_min:.3f} window_s={verdict.window_s:.2f} "
        f"commanded_rate={verdict.commanded_rate:.3f} sim_t={sim_t:.3f}"
    )


def config_from_safety(data: Mapping[str, Any]) -> StallAbortConfig:
    """Build the stall-abort config from the `safety:` mapping of the M4 safety file.

    Args:
        data: The `safety` mapping.

    Returns:
        The config. Enabled only for a literal YAML `true` under
        `stall_abort.enabled`; an absent or non-mapping `stall_abort` is off.

    Raises:
        pydantic.ValidationError: If an enabled block carries an invalid
            parameter (fail loud rather than run with an unintended value).
    """
    block = data.get("stall_abort")
    if not isinstance(block, Mapping):
        return StallAbortConfig()
    params = {k: v for k, v in block.items() if k != "enabled"}
    if block.get("enabled") is not True:
        return StallAbortConfig()
    return StallAbortConfig(enabled=True, **params)


def startup_suffix(config: StallAbortConfig) -> str:
    """Suffix for the command bus startup line; empty when the key is off.

    Args:
        config: The loaded config.

    Returns:
        `" stall_abort=True window_s=... ..."` naming every parameter, or "".
    """
    if not config.enabled:
        return ""
    fields = (
        "window_s",
        "min_progress_ratio",
        "grace_s",
        "stale_input_s",
        "min_linear_mps",
        "min_angular_radps",
        "min_expected_m",
        "min_expected_rad",
    )
    return " stall_abort=True " + " ".join(f"{name}={getattr(config, name)}" for name in fields)
