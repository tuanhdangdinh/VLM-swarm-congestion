"""PILOT (exploratory, non-confirmatory): build the V-JEPA 2 probe clip dataset.

Reads OUT_ROOT/inventory.json and writes OUT_ROOT/dataset.json:

- episode roles: `battery` (hosts battery-v2 main items; test-only),
  `excluded_twin` (same scenario + seed as a battery episode, or any GT row
  within 0.10 m per robot of a battery item's configuration), `train`, `test`;
- conflict samples `(episode, t_end, pair)` labelled by battery-v2's own
  `dynamics.conflict_prediction_answer` (yes <= 0.40 m / no >= 0.65 m within
  10 s; separated >= 0.75 m; one robot moving; reachable), with the battery's
  reversing / ambiguous-band drops and the command-free flag;
- temporal robot samples `(episode, t_end, robot)` with target = seconds since
  the robot was last in motion (GT speed > 0.03 m/s), capped at 30 s;
- held-out temporal pairs from `dynamics.temporal_order_answer` (battery rule);
- the battery items mapped to clips where a dense preceding clip exists.

Every clip is 16 frames at 0.5 sim-s spacing ending at `t_end`.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import random
import sys

import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as c  # noqa: E402
from common import dyn  # noqa: E402

from reasoning.vlm.capability_probes import episode_v2  # noqa: E402

BATTERY_RUNS = {
    "battery_v2_harvest/b2_headon_off",
    "battery_v2_harvest/b2_convoy_off",
    "intersection_v2/IBB4_20260929_102427",
}
TWIN_RUNS = {"battery_v2_harvest/b2_headon_on", "battery_v2_harvest/b2_convoy_on"}
NEAR_DUP_M = 0.10
TOL = {"snapshot": 0.15, "video": 0.5}
# Recording clips draw a per-clip spacing from the harvest snapshot range so
# their timing matches the battery snapshot clips.
VIDEO_SPACINGS = (0.50, 0.53, 0.56, 0.60)
IN_FRAME_MARGIN_PX = 30
STILL_CAP_SEC = 30.0
SEED = 20261011
TEST_FRACTION = 0.3


def clip_spacing(run_id: str, t_end: float) -> float:
    h = int(hashlib.sha256(f"{SEED}|{run_id}|{t_end:.2f}".encode()).hexdigest()[:12], 16)
    return VIDEO_SPACINGS[h % len(VIDEO_SPACINGS)]


def clip_for(index: c.FrameIndex, run_id: str, t_end: float) -> list[int] | None:
    return c.match_clip(index, t_end, TOL[index.kind], clip_spacing(run_id, t_end))


def in_frame(row: dict, rid: str) -> bool:
    r = row["robots"][rid]
    u, v = c.world_to_pixel(r["x"], r["y"])
    m = IN_FRAME_MARGIN_PX
    return m <= u <= c.FRAME_W - m and m <= v <= c.FRAME_H - m


def still_since(track: dyn.GtTrack, rid: str, t: float) -> float:
    """Seconds since `rid` was last in motion (speed > STATIONARY_MAX) at or before `t`."""
    i = max(0, min(len(track.times) - 1, __import__("bisect").bisect_right(track.times, t) - 1))
    t_now = track.times[i]
    while i >= 0:
        ti = track.times[i]
        s = track.speed(rid, ti)
        if s is not None and s > dyn.STATIONARY_MAX_SPEED_MPS:
            return t - ti
        if t_now - ti > STILL_CAP_SEC:
            return STILL_CAP_SEC
        i -= 1
    return STILL_CAP_SEC


def battery_items() -> list[dict]:
    m = json.loads(c.MANIFEST_V2.read_text())
    return [i for i in m["items"] if i["subset"] == "main" and i["probe_type"] != "motion_direction"]


def battery_windows(items, tracks) -> list[dict]:
    """GT positions of every robot over each battery item's 16-sample, 0.5 s-spaced window."""
    out = []
    for it in items:
        tr = tracks.get(it["run_id"])
        if tr is None:
            tr = c.load_gt(c.LOGS_ROOT / it["run_id"])
            tracks[it["run_id"]] = tr
        rows = [tr.row_near(t, tolerance=0.1) for t in c.clip_times(it["sim_time_sec"])]
        if any(r is None for r in rows):
            continue
        ids = sorted(rows[-1]["robots"])
        if any(set(r["robots"]) != set(ids) for r in rows):
            continue
        out.append({"item_id": it["item_id"], "ids": ids, "xy": np.array([[[r["robots"][k]["x"], r["robots"][k]["y"]] for k in ids] for r in rows])})
    return out


def near_duplicate(track: dyn.GtTrack, windows: list[dict]) -> str | None:
    """Return the first battery item whose 8 s GT window this episode reproduces within 0.10 m, or None.

    Every robot at every one of the 16 window samples must lie within
    NEAR_DUP_M of the battery window: the clip-level analogue of the
    battery's own near-duplicate rule, so a replay of a battery trajectory
    is caught while merely sharing a parked configuration is not.
    """
    times = np.array(track.times)
    for w in windows:
        ids = w["ids"]
        if set(track.rows[0]["robots"]) != set(ids):
            continue
        xy = np.array([[[r["robots"][k]["x"], r["robots"][k]["y"]] for k in ids] for r in track.rows])
        for i in range(len(times)):
            t_end = times[i]
            js = np.searchsorted(times, np.array(c.clip_times(t_end)))
            if js[0] <= 0 or js[-1] >= len(times):
                continue
            d = np.linalg.norm(xy[js] - w["xy"], axis=-1)
            if (d <= NEAR_DUP_M).all():
                return w["item_id"]
    return None


def frame_index_for(rec: dict) -> c.FrameIndex:
    b = c.LOGS_ROOT / rec["run_id"]
    if rec["source"] == "snapshot":
        return c.snapshot_index(b / "snapshots")
    tl = json.loads((c.OUT_ROOT / "timelines" / (rec["run_id"].replace("/", "__") + ".json")).read_text())
    return c.video_index(tl)


def conflict_samples(rec, ep, index) -> list[dict]:
    track = ep.track
    out = []
    t = index.times[0] + (c.CLIP_FRAMES - 1) * c.CLIP_SPACING_SEC
    t = math.ceil(t * 2) / 2
    while t <= index.times[-1]:
        frames = clip_for(index, rec["run_id"], t)
        row = track.row_near(t, tolerance=0.1)
        if frames is not None and row is not None:
            for a, b in itertools.combinations(sorted(row["robots"]), 2):
                answer, reason, facts = dyn.conflict_prediction_answer(track, a, b, t)
                if answer is None:
                    continue
                if not (in_frame(row, a) and in_frame(row, b)):
                    continue
                bad = False
                for rid in (a, b):
                    sp = track.speed(rid, t)
                    mc = dyn.motion_class(sp)
                    v = track.velocity(rid, t)
                    if mc == "ambiguous" or (mc == "moving" and dyn.is_reversing(v, row["robots"][rid]["theta"])):
                        bad = True
                if bad:
                    continue
                cmd_free = None
                if ep.command_windows is not None:
                    windows = list(ep.command_windows) + list(ep.onset_windows)
                    cmd_free = dyn.horizon_is_command_free(t, dyn.exclusion_horizon_sec(answer, t, facts), windows)
                out.append(
                    {
                        "task": "conflict",
                        "run_id": rec["run_id"],
                        "t_end": t,
                        "pair": [a, b],
                        "label": int(answer == "yes"),
                        "command_free": cmd_free,
                        "facts": {k: round(v, 4) for k, v in facts.items()},
                        "frames": frames,
                    }
                )
        t += 0.5
    return out


def temporal_robot_samples(rec, track, index) -> list[dict]:
    out = []
    t = index.times[0] + (c.CLIP_FRAMES - 1) * c.CLIP_SPACING_SEC
    t = math.ceil(t)
    while t <= index.times[-1]:
        frames = clip_for(index, rec["run_id"], t)
        row = track.row_near(t, tolerance=0.1)
        if frames is not None and row is not None:
            for rid in sorted(row["robots"]):
                if not in_frame(row, rid):
                    continue
                out.append(
                    {
                        "task": "temporal_robot",
                        "run_id": rec["run_id"],
                        "t_end": float(t),
                        "robot": rid,
                        "still_sec": round(still_since(track, rid, t), 3),
                        "frames": frames,
                    }
                )
        t += 1.0
    return out


def temporal_pairs(rec, track, index) -> list[dict]:
    """Battery-rule temporal_order pairs in one episode, one per (kind, pair, event pair)."""
    found: dict[tuple, list] = {}
    t = index.times[0] + (c.CLIP_FRAMES - 1) * c.CLIP_SPACING_SEC
    t = math.ceil(t * 2) / 2
    while t <= index.times[-1]:
        row = track.row_near(t, tolerance=0.1)
        frames = clip_for(index, rec["run_id"], t)
        if row is not None and frames is not None:
            for a, b in itertools.combinations(sorted(row["robots"]), 2):
                if not (in_frame(row, a) and in_frame(row, b)):
                    continue
                for kind in ("goal", "stop"):
                    ans, reason, facts = dyn.temporal_order_answer(track, kind, a, b, t)
                    if ans is None:
                        continue
                    key = (kind, a, b, round(facts["event_a_sec"], 1), round(facts["event_b_sec"], 1))
                    found.setdefault(key, []).append((t, ans, facts, frames))
        t += 0.5
    out = []
    for (kind, a, b, _, _), hits in sorted(found.items()):
        t, ans, facts, frames = hits[len(hits) // 2]
        out.append(
            {
                "task": "temporal_pair",
                "run_id": rec["run_id"],
                "t_end": t,
                "kind": kind,
                "pair": [a, b],
                "answer": ans,
                "facts": {k: round(v, 3) for k, v in facts.items()},
                "frames": frames,
            }
        )
    return out


def battery_mapping(items, indexes, tracks) -> list[dict]:
    out = []
    for it in items:
        rec = {
            "task": "battery",
            "item_id": it["item_id"],
            "probe_type": it["probe_type"],
            "run_id": it["run_id"],
            "frame_source": it["frame_source"],
            "t_end": it["sim_time_sec"],
            "question_key": it["question_key"],
            "correct_answer": it["correct_answer"],
            "derivation": it["derivation"],
        }
        idx = indexes.get(it["run_id"])
        if idx is None:
            rec["mappable"], rec["unmappable_reason"] = False, "no_dense_frames_in_episode"
            out.append(rec)
            continue
        frames = clip_for(idx, it["run_id"], it["sim_time_sec"])
        if frames is None:
            rec["mappable"], rec["unmappable_reason"] = False, "clip_not_covered"
            out.append(rec)
            continue
        last = idx.refs[frames[-1]]
        if idx.kind == "snapshot":
            rec["last_frame_is_item_frame"] = Path(last).name == Path(it["frame_relpath"]).name
        else:
            rec["last_frame_is_item_frame"] = False
            rec["last_frame_stamp_err_sec"] = round(abs(idx.times[frames[-1]] - it["sim_time_sec"]), 3)
        rec["frames"] = frames
        rec["mappable"] = True
        tr = tracks[it["run_id"]]
        row = tr.row_near(it["sim_time_sec"], tolerance=0.1)
        if it["probe_type"] == "conflict_prediction":
            # The probe is trained on the pair label; also record the any-pair label.
            rec["pair"] = it["question_key"].split("|")
        else:
            kind, _, pair = it["question_key"].partition(":")
            rec["kind"], rec["pair"] = kind, pair.split("|")
            rec["still_sec"] = {rid: round(still_since(tr, rid, it["sim_time_sec"]), 3) for rid in rec["pair"]}
        rec["n_robots"] = len(row["robots"]) if row else None
        out.append(rec)
    return out


def split_episodes(runs: list[str], has_yes: dict[str, bool]) -> dict[str, str]:
    """Seeded episode-level split, stratified on whether an episode has conflict "yes" clips."""
    rng = random.Random(SEED)
    out = {}
    for stratum in (True, False):
        group = sorted(r for r in runs if has_yes[r] == stratum)
        rng.shuffle(group)
        n_test = max(1, round(len(group) * TEST_FRACTION)) if group else 0
        out.update({r: ("test" if i < n_test else "train") for i, r in enumerate(group)})
    return out


def main() -> None:
    inventory = [r for r in json.loads((c.OUT_ROOT / "inventory.json").read_text()) if r.get("usable")]
    items = battery_items()
    tracks: dict[str, dyn.GtTrack] = {}
    windows = battery_windows(items, tracks)
    roles: dict[str, str] = {}
    role_reason: dict[str, str] = {}
    battery_scen_seed = set()
    for r in inventory:
        if r["run_id"] in BATTERY_RUNS:
            cnd = r["condition"]
            battery_scen_seed.add((cnd.get("scenario", cnd.get("variant")), cnd.get("seed")))
    for r in inventory:
        rid = r["run_id"]
        cnd = r["condition"]
        if rid in BATTERY_RUNS:
            roles[rid], role_reason[rid] = "battery", "hosts battery-v2 main items"
            continue
        if rid in TWIN_RUNS:
            roles[rid], role_reason[rid] = "excluded_twin", "trails-on harvest twin (same scenario+seed)"
            continue
        if (cnd.get("scenario", cnd.get("variant")), cnd.get("seed")) in battery_scen_seed and cnd.get("seed"):
            roles[rid], role_reason[rid] = "excluded_twin", "same scenario+seed as a battery episode"
            continue
        tr = tracks.get(rid) or c.load_gt(c.LOGS_ROOT / rid)
        tracks[rid] = tr
        dup = near_duplicate(tr, windows)
        if dup:
            roles[rid], role_reason[rid] = "excluded_twin", f"8 s GT window within 0.10 m of battery item {dup}"
            continue
        roles[rid] = "pool"
    pre, indexes, eps = {}, {}, {}
    for r in inventory:
        rid = r["run_id"]
        indexes[rid] = frame_index_for(r)
        eps[rid] = episode_v2.load_episode(c.LOGS_ROOT / rid, c.LOGS_ROOT)
        tracks[rid] = eps[rid].track
        if roles[rid] == "pool":
            pre[rid] = conflict_samples(r, eps[rid], indexes[rid])
    pool = sorted(pre)
    split = split_episodes(pool, {r: any(s["label"] == 1 for s in pre[r]) for r in pool})
    for r, sp in split.items():
        roles[r], role_reason[r] = sp, "seeded episode-level split (stratified on conflict-yes presence)"

    episodes, samples = [], []
    for r in inventory:
        rid = r["run_id"]
        index, ep = indexes[rid], eps[rid]
        role = roles[rid]
        ep_samples = []
        if role in ("train", "test"):
            ep_samples += pre[rid]
            ep_samples += temporal_robot_samples(r, ep.track, index)
            ep_samples += temporal_pairs(r, ep.track, index)
        for s in ep_samples:
            s["role"] = role
        samples += ep_samples
        cnt = lambda task, **kw: sum(  # noqa: E731
            1 for s in ep_samples if s["task"] == task and all(s.get(k) == v for k, v in kw.items())
        )
        episodes.append(
            {
                "run_id": rid,
                "role": role,
                "role_reason": role_reason[rid],
                "scenario": r["condition"].get("scenario", r["condition"].get("variant")),
                "seed": r["condition"].get("seed"),
                "source": r["source"],
                "n_robots": len(r["robots"]),
                "command_log": ep.command_windows is not None,
                "conflict_yes": cnt("conflict", label=1),
                "conflict_no": cnt("conflict", label=0),
                "conflict_yes_cmdfree": cnt("conflict", label=1, command_free=True),
                "conflict_no_cmdfree": cnt("conflict", label=0, command_free=True),
                "temporal_robot": cnt("temporal_robot"),
                "temporal_pair": cnt("temporal_pair"),
            }
        )
        print(episodes[-1], flush=True)
    battery = battery_mapping(items, {k: v for k, v in indexes.items() if roles.get(k) == "battery"}, tracks)
    for b in battery:
        b["role"] = "battery"
    out = {
        "seed": SEED,
        "clip_frames": c.CLIP_FRAMES,
        "clip_spacing_sec": c.CLIP_SPACING_SEC,
        "episodes": episodes,
        "samples": samples,
        "battery": battery,
        "frame_indexes": {k: {"kind": v.kind, "times": v.times} for k, v in indexes.items()},
    }
    blob = json.dumps(out, default=float)
    (c.OUT_ROOT / "dataset.json").write_text(blob)
    print("sha256", hashlib.sha256(blob.encode()).hexdigest())


if __name__ == "__main__":
    main()
