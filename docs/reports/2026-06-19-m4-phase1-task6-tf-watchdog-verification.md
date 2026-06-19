# M4 Phase 1 — Task 6 Step 3 Host Verification Report (TF tree + cmd_vel watchdog)

**Date:** 2026-06-19
**Branch:** `feat/m4-phase1-drive-chain`
**Plan under execution:** `docs/superpowers/plans/2026-06-19-m4-phase1-drive-chain.md` (Task 6, Step 3)
**Executed on:** GCP VM (Ubuntu 22.04 / Jammy), Isaac Sim 6.0 **source build** at
`/home/ubuntu/IsaacSim`, accessed via SSH.
**Scenario:** `head_on_deadlock`, `robot_1`, turning twist `linear.x=0.12`, `angular.z=0.6`.
**Reasoning backend:** none — this is a drive-chain/TF verification, **no VLM/OpenAI call**.

---

## Headline

The M4 Phase 1 drive graph's **TF tree** and **Branch B cmd_vel watchdog** are
verified correct on the host. The dynamic `robot_1/odom → robot_1/base_footprint`
transform publishes on `/tf` while driving and tracks `/odom` on a curve; the
watchdog zeros a stale command within ~0.5 s of sim time. The quaternion
convention on the `odom_compute.outputs:orientation → pub_tf.inputs:rotation`
link is intact (no xyzw/wxyz scramble). A "TF freeze" seen in an earlier probe
run was traced to a **probe-side bug** (ROS subscription starvation), not a defect
in `ros_graphs.py`.

---

## Result table

| Check | Measured | Bar | Verdict |
|---|---|---|---|
| Yaw swept on the curve | **166.2°** | ≥ 60° (must turn, not just go straight) | ✅ |
| `\|yaw_wire − yaw_src\|` (in-process: `pub_tf.inputs:rotation` vs `odom_compute.outputs:orientation`) | **0.0°** | ≤ 10° | ✅ |
| `\|yaw_src − path tangent\|` (in-process, vs physical motion) | **9.3°** | ≤ 10° | ✅ |
| Watchdog stop delay after last command | **0.567 s** | ~0.5 s, ≤ 0.8 s | ✅ |
| *Diagnostic:* `\|yaw_tf − yaw_odom\|` (ROS-received, full sweep) | 1.0° | — | ✅ |
| *Diagnostic:* publisher-input freeze step | never | — | ✅ |

**RESULT: PASS** (reproduced — a second confirmation run gave identical gates,
with `\|yaw_tf − yaw_odom\| = 0.0°` and watchdog stop delay 0.533 s).

---

## What was verified, and why each check matters

Task 6 Step 3 (per the plan) requires confirming two things on the host:

1. The dynamic `{robot}/odom → {robot}/base_footprint` TF updates on `/tf` while
   driving, and `/tf_static` carries `base_link`/`base_scan`.
2. Branch B (`CmdVelWatchdog`) zeros velocity ~0.5 s of sim time after a single
   non-repeating twist stops.

An **advisor-added bar** raised the rigour: the TF yaw must track odom yaw on a
**curve** (turning), not just a straight line. Reason — both `pub_odom`
(`ROS2PublishOdometry`, known-good ROS xyzw convention) and `pub_tf`
(`ROS2PublishRawTransformTree`) consume the **same** `odom_compute.outputs:orientation`.
A USD `GfQuat` is w-first while ROS wants xyzw; a silent order scramble on the
`pub_tf` link would be invisible at rest and on a straight line but shows up as
gross yaw divergence under rotation. Driving a curve and comparing the two yaws is
the exact end-to-end test of that convention.

The verification therefore checks, **in-process via OmniGraph reads** (which never
depend on the ROS receive path):

- `yaw_wire` (from `pub_tf.inputs:rotation`) vs `yaw_src` (from
  `odom_compute.outputs:orientation`) — proves the orientation reaches the TF
  publisher's input **byte-identical** (0.0° over a 166° sweep ⇒ no scramble).
- `yaw_src` vs the **path tangent** computed from `odom_compute.outputs:position`
  (diff-drive has no lateral slip, so heading = path tangent) — proves the
  orientation is **physically correct**, not just self-consistent.

and, as a **diagnostic** of the live wire, the ROS-received `/tf` transform yaw vs
the `/odom` message yaw.

The watchdog is checked by reading the graph's own consumed command
(`twist_sub.outputs:linearVelocity` on `/cmd_vel_safe`) and
`diff_ctrl.outputs:velocityCommand` returning to zero after commands stop.

---

## Findings

1. **Quaternion convention is correct.** `|yaw_wire − yaw_src| = 0.0°` for the
   entire 166° sweep. The `odom_compute.outputs:orientation → pub_tf.inputs:rotation`
   connection passes the quaternion through without an order scramble. The 9.3°
   residual against the path tangent is **not** error — it is the expected
   chord-vs-tangent finite-difference lag: over each 20-step sample window the
   robot sweeps ≈18.7°, and the chord direction of an arc lags the endpoint
   heading by ≈half the swept angle (≈9.3°), which matches the measurement
   exactly.

2. **TF publishes and tracks live.** The ROS-received `robot_1/odom →
   robot_1/base_footprint` yaw tracked the full 13°→164° sweep at a steady **−1.0°**
   offset vs `/odom`. `/tf_static` carries `base_footprint→base_link→base_scan`.

3. **Watchdog works.** After a single non-repeating twist, `/cmd_vel_safe`
   (`[0.12, 0, 0] → [0, 0, 0]`) and `diff_ctrl.outputs:velocityCommand`
   (`[2.18, 5.09] → [0, 0]`) zeroed in **0.567 s** of sim time — the 0.5 s
   `command_timeout_sec` plus one ~0.05 s relay tick. The robots never move
   without this node running; it is load-bearing for every run.

4. **The earlier "TF freeze" was a probe artifact, not a graph bug.** A prior
   probe run showed the ROS-received TF yaw freezing at ~114° while `/odom` kept
   climbing (43° divergence). Instrumenting the **in-process** publisher input
   showed it kept advancing the whole time (`publisher-input froze at = never`),
   so the publisher was healthy. Root cause: the probe serviced only one rclpy
   callback per sim step while the graph emits **≥2 messages/step** (`/odom` +
   `/tf`); the lower-priority `/tf` subscription queue saturated and stopped
   advancing. Draining all ready callbacks per step (8× `spin_once`) eliminated
   the freeze entirely.

5. **Benign warning.** A `[Warning] Frame robot_1/odom Timestamp is invalid.
   Timestamp 0 will be neglected for all published ROS messages` floods the log.
   It appears from the first ticks (a persistent-from-start condition) and does
   **not** gate anything — TF tracked perfectly throughout. Left as a known-benign
   note; not investigated further because it does not affect the drive chain.

---

## What I changed

### Production code (already committed before this run)
No production source was changed *during* this verification. The code under test
was committed earlier in the workflow:

- `isaac/vgu_sim/ros_graphs.py` (`3579221`) — added the TF tree
  (`pub_tf`/`pub_tf_base`/`pub_tf_scan`, `IsaacReadSimulationTime`) and pointed
  `twist_sub` at `/cmd_vel_safe`.
- `isaac/vgu_sim/cmd_vel_watchdog_node.py` (`ff67fd8`) — fixed
  `SingleThreadedExecutor` import (was referenced as `rclpy.executors.*`, which
  `import rclpy` does not bind).

### Verification probe (ephemeral — NOT committed, removed from host)
`isaac/scripts/probe_tf_watchdog.py` was authored as a throwaway in-sim diagnostic.
It builds the real `head_on_deadlock` scene with the runner's own helpers, starts
the watchdog exactly as `runner._start_cmd_vel_watchdog` does, drives a curve, and
samples the yaws and watchdog state described above. Key fixes made to it this
session:

- Open the scenario stage with an **absolute** path. The live Omniverse resolver
  anchors the scenario's relative `../assets/...` references against the layer
  *identifier*; a relative identifier doubles to `isaac/scenarios/isaac/assets/...`
  and fails to resolve. (A bare `Usd.Stage.Open` uses realPath and is unaffected —
  which is why offline validation passed but the in-app open did not.)
- Drain **all** ready rclpy callbacks per step (fixes the false TF freeze, finding 4).
- Decoupled verdict: gate on **in-process** OmniGraph reads (never starve), report
  the ROS-received yaws as diagnostics only, so a probe-side stall can neither fake
  nor mask the result.
- Fixed the watchdog check to handle the numpy-vector `twist_sub.outputs:linearVelocity`
  (`[vx, vy, vz]`), not a float.

The probe was deleted from the host after the run.

### Plan / docs
- `docs/superpowers/plans/2026-06-19-m4-phase1-drive-chain.md` (`a54b2ec`) — Task 6
  Step 3 checked off with the PASS evidence and a note for Task 7's TF subscriber
  (must drain ≥2 callbacks/step).
- This report.

---

## Carry-forward for Task 7 (in-sim acceptance test)

Task 7's acceptance test subscribes to `/tf` the same way and **will hit the same
starvation** unless it drains all ready callbacks per step (or uses a `tf2` buffer).
This is the single most important lesson to carry into the automated test. The
proven verification pattern — a `FixedTwistDriver` publishing a known twist, an
in-process odometry-displacement oracle (`forward_distance`, Task 2), then a
watchdog-stop assertion — is exactly what Task 7 formalizes as pytest.

---

## Security / cleanup

- Ephemeral host diagnostics removed (`isaac/scripts/probe_tf_watchdog.py`,
  `/tmp/run_probe.sh`, `/tmp/build_scenario.sh`, `/tmp/probe_tf_wd.log`).
- **No SSH private key left on the remote** — a `find` over `/home/ubuntu` and
  `/tmp` returned only bundled CA certificate stores (`cacert.pem`), never the
  access key (`key.pem` is used only locally via `ssh -i`).
- No secrets written or logged; no VLM/OpenAI key involved in this run.
