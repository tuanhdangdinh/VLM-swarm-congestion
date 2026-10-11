# PILOT: Frozen V-JEPA 2 Encoder + Linear Probe on the Battery-v2 Conflict and Temporal Probes

**Prepared:** 2026-10-11

**Status:** PILOT. Exploratory, non-confirmatory, and EXCLUDED from every confirmatory count.

**Revision history:**

- Rev 0 (committed before any held-out or battery item was scored): dataset card, method, the frozen probe configuration and the decision rule.

---

## Decision Rule (Fixed Before Scoring)

The probe configuration below was selected by leave-one-episode-out CV on
TRAIN episodes only and frozen in this revision. Held-out TEST clips and the
mapped battery items are then scored exactly once.

**"Earns a thesis table"** requires all three:

- **T1.** The held-out conflict probe (`dyn`, command-free clips) reaches
  balanced accuracy >= 0.70, and its Wilson 95% lower bound on plain accuracy
  is above 0.5.
- **T2.** Motion is what the probe uses. `dyn` beats the `static` control
  (last frame repeated) by >= 0.10 on held-out conflict balanced accuracy, or
  by >= 0.10 on held-out broad temporal pair accuracy.
- **T3.** On the mapped battery conflict items, `dyn` scores at least
  gpt-4o + 3 on the same items. This is direction only; n is too small for a
  test.

Otherwise the result **earns a paragraph** (Discussion / Future Work), not a
table. Two readouts are fixed in advance as well:

- If `static` is within 0.05 of `dyn` on a task, that task's score is
  attributed to static cues (status colour, arrow, label, layout), not motion.
- On temporal_order, the earlier event lies 32-183 s before every battery
  frame, outside any clip. A clip probe can at best detect "which robot moved
  recently". The lower-id rule (15/19 on the full battery) and the
  drawn-STOPPED rule are the bars it has to clear.

## Frozen Configuration

Frozen at this revision from `data/logs/vjepa_pilot_20261011/probe/frozen.json`
(gitignored; reproduced here verbatim in substance).

| Setting | Value |
|---|---|
| Encoder | `facebook/vjepa2-vitl-fpc64-256` (ViT-L/16, ~300M params, MIT licence), frozen, fp32 on Apple MPS |
| Clip | 8 frames, 0.50-0.60 sim-s apart (3.0-5.2 s of history), 256x256, ImageNet mean/std |
| Tokens | 4 (tubelet 2) x 16 x 16, width 1024; pooled at extraction, never stored raw |
| Conflict crop | 960 px square centred on the pair midpoint at the last frame |
| Temporal crop | 480 px square centred on the robot at the last frame |
| Conflict features | `[g, (A+B)/2, abs(A-B), (dA+dB)/2, abs(dA-dB)]` (5x1024) |
| Conflict model | StandardScaler + LogisticRegression(class_weight=balanced), threshold 0.5; C = **0.0001** (dyn), **0.001** (static) |
| Conflict training rows | battery-identical label, command-free only: 375 clips (142 yes), 7 episodes, 5 scenario families |
| Temporal features | `[mean R, R_last-R_first, std R] (3x1024), robot-own pooled tokens only` |
| Temporal model | StandardScaler + Ridge on log1p(min(still_sec,30)); first = larger prediction; alpha = **1000** (dyn), **1000** (static) |
| Temporal training rows | 1725 robot clips, 8 episodes, 5 families |
| Selection | leave-one-scenario-family-out over TRAIN families only; selection metric balanced acc (conflict) / pair acc (temporal) |
| Broad temporal pair rule | same clip, abs(still_a - still_b) >= 2.0 s, later stop <= 8.0 s |
| Split | scenario families: test = ['bottleneck_merge', 'loop', 's6_dual_conflict']; train = ['blocked_path', 'dynamic_anomaly', 'intersection_bottleneck', 'obstacle_in_candidate', 't2b_flow_ordering'] |

CV scores on TRAIN families only (the selection data; not a result):

- conflict balanced accuracy, dyn: 0.0001: 0.732, 0.0003: 0.722, 0.001: 0.725, 0.003: 0.725, 0.01: 0.722, 0.03: 0.722, 0.1: 0.722
- conflict balanced accuracy, static: 0.0001: 0.573, 0.0003: 0.577, 0.001: 0.582, 0.003: 0.580, 0.01: 0.577, 0.03: 0.572, 0.1: 0.567
- temporal broad-pair accuracy (448 pairs), dyn: 10.0: 0.942, 100.0: 0.962, 1000.0: 0.973, 10000.0: 0.971, 100000.0: 0.967
- temporal broad-pair accuracy, static: 10.0: 0.920, 100.0: 0.938, 1000.0: 0.940, 10000.0: 0.926, 100000.0: 0.902

**Split change before scoring.** `build_dataset.py` first split by episode.
Before any held-out score was computed, the episode table showed same-scenario,
same-seed near-replays on both sides (`B1DEMO`/`B1DEMO2`, bottleneck_merge
seed 43; the two `t3b_smoke` runs). The split and the CV grouping were moved
to scenario families (`probe.py family_split`), and the probes refitted. The
features were not re-extracted; only the role labels changed.
