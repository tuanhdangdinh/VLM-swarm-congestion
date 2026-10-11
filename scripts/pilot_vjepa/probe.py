"""PILOT (exploratory, non-confirmatory): fit and score linear probes on frozen V-JEPA 2 features.

Two stages, run separately so the probe configuration is frozen (and
committed) before any held-out or battery item is scored:

    probe.py fit    # leave-one-episode-out CV on TRAIN episodes only -> frozen.json + models
    probe.py score  # held-out TEST clips + mapped battery items, once -> results.json

Conflict probe (per clip, per robot pair): logistic regression on
`[g, (A+B)/2, |A-B|, (dA+dB)/2, |dA-dB|]`, where A/B are the robots' pooled
tokens averaged over tubelets and dA/dB their last-minus-first tubelet
difference; symmetric in the pair. Trained on the battery-identical label
(`conflict_prediction_answer` + reversing/ambiguous drops + command-free).

Temporal probe (per clip, per robot): ridge regression of
`log1p(min(still_sec, 30))` on `[mean R, dR, std R]` of the robot's own pooled
tokens. "Which stopped first" = the robot with the larger predicted
time-since-motion.

Each probe is fitted twice: on `dyn` (the real 8-frame clip) and `static`
(the last frame repeated) features.
"""

from __future__ import annotations

import itertools
import json
import math
import pickle
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as c  # noqa: E402
from common import dyn  # noqa: E402

FEAT = c.OUT_ROOT / "features"
MODEL_DIR = c.OUT_ROOT / "probe"
C_GRID = [1e-4, 3e-4, 1e-3, 3e-3, 1e-2, 3e-2, 1e-1]
ALPHA_GRID = [1e1, 1e2, 1e3, 1e4, 1e5]
PAIR_MIN_GAP_SEC = 2.0
PAIR_MAX_LATER_SEC = 8.0


FAMILY_PREFIXES = {"loop_": "loop", "blocked_path_": "blocked_path", "dynamic_anomaly": "dynamic_anomaly"}
SPLIT_SEED = 20261011
TEST_FRACTION = 0.3


def family(scenario: str | None) -> str:
    """Scenario family: variants on one map/robot layout count as one family."""
    scenario = scenario or "unknown"
    for prefix, fam in FAMILY_PREFIXES.items():
        if scenario.startswith(prefix):
            return fam
    return scenario


def family_split() -> dict:
    """Seeded scenario-FAMILY split of the non-battery, non-excluded episodes.

    Replaces build_dataset's episode-level split (fixed before any held-out
    scoring): same-scenario, same-seed runs (e.g. the two bottleneck_merge
    seed-43 demos) are near-replays, so an episode split leaks between
    train and test. Stratified on whether the family has conflict "yes" clips.
    """
    import random

    ds = json.loads((c.OUT_ROOT / "dataset.json").read_text())
    pool = [e for e in ds["episodes"] if e["role"] in ("train", "test")]
    fams = defaultdict(list)
    for e in pool:
        fams[family(e["scenario"])].append(e)
    rng = random.Random(SPLIT_SEED)
    roles, fam_role = {}, {}
    for stratum in (True, False):
        group = sorted(f for f, es in fams.items() if (sum(e["conflict_yes_cmdfree"] for e in es) > 0) == stratum)
        rng.shuffle(group)
        n_test = max(1, round(len(group) * TEST_FRACTION)) if group else 0
        for i, f in enumerate(group):
            fam_role[f] = "test" if i < n_test else "train"
            for e in fams[f]:
                roles[e["run_id"]] = fam_role[f]
    return {"roles": roles, "family_role": fam_role, "family_of": {e["run_id"]: family(e["scenario"]) for e in pool}}


SPLIT = None


def load(variant: str) -> tuple[dict, list[dict]]:
    global SPLIT
    if SPLIT is None:
        SPLIT = family_split()
    z = np.load(FEAT / f"{variant}.npz")
    meta = json.loads((FEAT / "index.json").read_text())["samples"]
    for s in meta:
        if s.get("role") in ("train", "test"):
            s["role"] = SPLIT["roles"][s["run_id"]]
            s["family"] = SPLIT["family_of"][s["run_id"]]
    pos = {int(u): i for i, u in enumerate(z["uid"])}
    arr = {k: z[k].astype(np.float32) for k in ("g", "gt", "ra", "rb")}
    return {"pos": pos, **arr}, meta


def conflict_x(F: dict, uids: list[int]) -> np.ndarray:
    idx = [F["pos"][u] for u in uids]
    g, ra, rb = F["g"][idx], F["ra"][idx], F["rb"][idx]
    a, b = ra.mean(1), rb.mean(1)
    da, db = ra[:, -1] - ra[:, 0], rb[:, -1] - rb[:, 0]
    return np.concatenate([g, (a + b) / 2, np.abs(a - b), (da + db) / 2, np.abs(da - db)], axis=1)


def temporal_x(F: dict, uids: list[int]) -> np.ndarray:
    idx = [F["pos"][u] for u in uids]
    ra = F["ra"][idx]
    return np.concatenate([ra.mean(1), ra[:, -1] - ra[:, 0], ra.std(1)], axis=1)


def still_target(s: dict) -> float:
    return math.log1p(min(s["still_sec"], 30.0))


def balanced_acc(y: np.ndarray, p: np.ndarray) -> float:
    accs = [float((p[y == k] == k).mean()) for k in (0, 1) if (y == k).any()]
    return float(np.mean(accs))


def conflict_train_set(meta: list[dict], role: str) -> list[dict]:
    return [s for s in meta if s["task"] == "conflict" and s.get("role") == role and s.get("command_free") is True]


def temporal_train_set(meta: list[dict], role: str) -> list[dict]:
    return [s for s in meta if s["task"] == "temporal_robot" and s.get("role") == role and not s.get("from_pair")]


def broad_pairs(robot_samples: list[dict]) -> list[tuple[dict, dict, str]]:
    """Same-clip robot pairs whose stop times differ by >= 2 s, the later within 8 s.

    Returns `(sample_a, sample_b, first_robot_id)` with the robot that has been
    still longer as the answer.
    """
    by_clip = defaultdict(list)
    for s in robot_samples:
        by_clip[(s["run_id"], s["t_end"])].append(s)
    out = []
    for group in by_clip.values():
        for a, b in itertools.combinations(sorted(group, key=lambda s: s["robot"]), 2):
            da, db = a["still_sec"], b["still_sec"]
            if abs(da - db) < PAIR_MIN_GAP_SEC or min(da, db) > PAIR_MAX_LATER_SEC:
                continue
            out.append((a, b, a["robot"] if da > db else b["robot"]))
    return out


def logo_splits(groups: list[str]):
    for g in sorted(set(groups)):
        tr = [i for i, x in enumerate(groups) if x != g]
        te = [i for i, x in enumerate(groups) if x == g]
        yield tr, te


def fit_conflict(F: dict, train: list[dict]) -> dict:
    X = conflict_x(F, [s["uid"] for s in train])
    y = np.array([s["label"] for s in train])
    groups = [s["family"] for s in train]
    cv = {}
    for C in C_GRID:
        pred = np.zeros_like(y)
        for tr, te in logo_splits(groups):
            if len(set(y[tr])) < 2:
                pred[te] = int(y[tr].mean() > 0.5)
                continue
            sc = StandardScaler().fit(X[tr])
            m = LogisticRegression(C=C, class_weight="balanced", max_iter=5000).fit(sc.transform(X[tr]), y[tr])
            pred[te] = m.predict(sc.transform(X[te]))
        cv[C] = balanced_acc(y, pred)
    best = max(C_GRID, key=lambda C: (cv[C], -C))
    sc = StandardScaler().fit(X)
    m = LogisticRegression(C=best, class_weight="balanced", max_iter=5000).fit(sc.transform(X), y)
    return {"C": best, "cv_balanced_acc": {str(k): v for k, v in cv.items()}, "scaler": sc, "model": m,
            "n_train": len(y), "n_yes": int(y.sum()), "n_families": len(set(groups)), "n_episodes": len({s["run_id"] for s in train})}


def pair_acc(pred_by_uid: dict[int, float], pairs) -> float | None:
    if not pairs:
        return None
    ok = 0
    for a, b, first in pairs:
        pick = a["robot"] if pred_by_uid[a["uid"]] > pred_by_uid[b["uid"]] else b["robot"]
        ok += pick == first
    return ok / len(pairs)


def fit_temporal(F: dict, train: list[dict]) -> dict:
    X = temporal_x(F, [s["uid"] for s in train])
    y = np.array([still_target(s) for s in train])
    groups = [s["family"] for s in train]
    pairs = broad_pairs(train)
    cv = {}
    for alpha in ALPHA_GRID:
        pred = np.zeros_like(y)
        for tr, te in logo_splits(groups):
            sc = StandardScaler().fit(X[tr])
            m = Ridge(alpha=alpha).fit(sc.transform(X[tr]), y[tr])
            pred[te] = m.predict(sc.transform(X[te]))
        cv[alpha] = pair_acc({s["uid"]: p for s, p in zip(train, pred)}, pairs)
    best = max(ALPHA_GRID, key=lambda a: (cv[a], a))
    sc = StandardScaler().fit(X)
    m = Ridge(alpha=best).fit(sc.transform(X), y)
    return {"alpha": best, "cv_pair_acc": {str(k): v for k, v in cv.items()}, "scaler": sc, "model": m,
            "n_train": len(y), "n_cv_pairs": len(pairs), "n_families": len(set(groups)), "n_episodes": len({s["run_id"] for s in train})}


def cmd_fit() -> None:
    MODEL_DIR.mkdir(exist_ok=True)
    frozen = {}
    for variant in ("dyn", "static"):
        F, meta = load(variant)
        cf = fit_conflict(F, conflict_train_set(meta, "train"))
        tf = fit_temporal(F, temporal_train_set(meta, "train"))
        with open(MODEL_DIR / f"{variant}.pkl", "wb") as fh:
            pickle.dump({"conflict": cf, "temporal": tf}, fh)
        frozen[variant] = {
            "conflict": {k: v for k, v in cf.items() if k not in ("scaler", "model")},
            "temporal": {k: v for k, v in tf.items() if k not in ("scaler", "model")},
        }
    frozen["split"] = SPLIT
    frozen["design"] = {
        "encoder": "facebook/vjepa2-vitl-fpc64-256 (frozen, fp32, MPS)",
        "clip": "8 frames, 0.5-0.6 sim-s spacing (3.5-5.2 s history), 256x256",
        "conflict_crop_px": 960,
        "temporal_crop_px": 480,
        "conflict_features": "[g, (A+B)/2, |A-B|, (dA+dB)/2, |dA-dB|] (5x1024)",
        "conflict_model": "StandardScaler + LogisticRegression(class_weight=balanced), threshold 0.5",
        "conflict_C_grid": C_GRID,
        "conflict_train_filter": "role=train, battery-identical label, command_free=True",
        "temporal_features": "[mean R, R_last-R_first, std R] (3x1024), robot-own pooled tokens only",
        "temporal_model": "StandardScaler + Ridge on log1p(min(still_sec,30)); first = larger prediction",
        "temporal_alpha_grid": ALPHA_GRID,
        "cv": "leave-one-scenario-family-out over TRAIN families only; selection metric balanced acc (conflict) / pair acc (temporal)",
        "broad_pair_rule": f"same clip, |still_a - still_b| >= {PAIR_MIN_GAP_SEC} s, later stop <= {PAIR_MAX_LATER_SEC} s",
    }
    (MODEL_DIR / "frozen.json").write_text(json.dumps(frozen, indent=1, default=float))
    print(json.dumps(frozen, indent=1, default=float))


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, centre - half), min(1.0, centre + half))


def mcnemar_exact(a: list[bool], b: list[bool]) -> dict:
    only_a = sum(1 for x, y in zip(a, b) if x and not y)
    only_b = sum(1 for x, y in zip(a, b) if y and not x)
    n = only_a + only_b
    if n == 0:
        return {"only_a": 0, "only_b": 0, "p": 1.0}
    k = min(only_a, only_b)
    p = min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2**n)
    return {"only_a": only_a, "only_b": only_b, "p": p}


def cluster_boot_acc(correct: list[bool], groups: list[str], n_boot: int = 2000, seed: int = 0) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    by = defaultdict(list)
    for ok, g in zip(correct, groups):
        by[g].append(ok)
    keys = sorted(by)
    stats = []
    for _ in range(n_boot):
        pick = rng.choice(len(keys), len(keys), replace=True)
        vals = [v for i in pick for v in by[keys[i]]]
        stats.append(np.mean(vals))
    return float(np.percentile(stats, 2.5)), float(np.percentile(stats, 97.5))


def cpa_yes(track: dyn.GtTrack, a: str, b: str, t: float) -> int:
    """Constant-velocity closest approach from GT state at `t`: 1 if within 0.5 m in 10 s."""
    row = track.row_near(t)
    pa, pb = row["robots"][a], row["robots"][b]
    va, vb = track.velocity(a, t), track.velocity(b, t)
    px, py = pb["x"] - pa["x"], pb["y"] - pa["y"]
    vx, vy = vb[0] - va[0], vb[1] - va[1]
    vv = vx * vx + vy * vy
    ts = 0.0 if vv == 0 else min(max(-(px * vx + py * vy) / vv, 0.0), dyn.CONFLICT_HORIZON_SEC)
    return int(math.hypot(px + vx * ts, py + vy * ts) <= dyn.CONFLICT_THRESHOLD_M)


def vlm_correct(backend: str) -> dict[str, dict]:
    d = c.BATTERY_RESULTS / f"{backend}__main"
    rows = [json.loads(l) for f in sorted(d.glob("*.jsonl")) for l in f.open() if l.strip()]
    return {r["item_id"]: r for r in rows}


def lower_id(a: str, b: str) -> str:
    return min(a, b, key=lambda r: int(r.split("_")[1]))


def cmd_score() -> None:
    out: dict = {}
    models = {v: pickle.load(open(MODEL_DIR / f"{v}.pkl", "rb")) for v in ("dyn", "static")}
    feats = {v: load(v) for v in ("dyn", "static")}
    meta = feats["dyn"][1]
    tracks: dict[str, dyn.GtTrack] = {}

    def track(rid):
        if rid not in tracks:
            tracks[rid] = c.load_gt(c.LOGS_ROOT / rid)
        return tracks[rid]

    # Held-out conflict clips.
    test_c = conflict_train_set(meta, "test")
    test_c_all = [s for s in meta if s["task"] == "conflict" and s.get("role") == "test"]
    res_c = {}
    for name, subset in (("command_free", test_c), ("all_kinematic", test_c_all)):
        y = np.array([s["label"] for s in subset])
        row = {"n": len(y), "n_yes": int(y.sum()), "episodes": sorted({s["run_id"] for s in subset})}
        for v in ("dyn", "static"):
            m = models[v]["conflict"]
            X = conflict_x(feats[v][0], [s["uid"] for s in subset])
            p = m["model"].predict(m["scaler"].transform(X))
            ok = (p == y).tolist()
            row[v] = {"acc": float(np.mean(ok)), "k": int(sum(ok)), "wilson": wilson(int(sum(ok)), len(ok)),
                      "balanced_acc": balanced_acc(y, p), "cluster_boot": cluster_boot_acc(ok, [s["run_id"] for s in subset]),
                      "said_yes": int(p.sum())}
        cpa = np.array([cpa_yes(track(s["run_id"]), *s["pair"], s["t_end"]) for s in subset])
        row["cpa_state_rule"] = {"acc": float((cpa == y).mean()), "balanced_acc": balanced_acc(y, cpa)}
        row["always_yes"] = {"acc": float(y.mean()), "balanced_acc": 0.5}
        res_c[name] = row
    out["heldout_conflict"] = res_c

    # Held-out temporal pairs.
    res_t = {}
    test_r = temporal_train_set(meta, "test")
    pair_sets = {"broad_same_clip": broad_pairs(test_r)}
    bp = [s for s in meta if s["task"] == "temporal_robot" and s.get("from_pair") and s.get("role") == "test"]
    by = defaultdict(dict)
    for s in bp:
        by[(s["run_id"], s["t_end"], s["kind"], tuple(s["pair"]))][s["robot"]] = s
    pair_sets["battery_rule"] = [(g[k[3][0]], g[k[3][1]], next(s for s in g.values())["answer"]) for k, g in by.items() if len(g) == 2]
    for name, pairs in pair_sets.items():
        row = {"n": len(pairs), "episodes": sorted({a["run_id"] for a, _, _ in pairs})}
        for v in ("dyn", "static"):
            m = models[v]["temporal"]
            uids = sorted({s["uid"] for a, b, _ in pairs for s in (a, b)})
            pred = dict(zip(uids, m["model"].predict(m["scaler"].transform(temporal_x(feats[v][0], uids))))) if uids else {}
            ok = [(a["robot"] if pred[a["uid"]] > pred[b["uid"]] else b["robot"]) == first for a, b, first in pairs]
            row[v] = {"acc": float(np.mean(ok)) if ok else None, "k": int(sum(ok)), "wilson": wilson(int(sum(ok)), len(ok)),
                      "cluster_boot": cluster_boot_acc(ok, [a["run_id"] for a, _, _ in pairs]) if ok else None}
        lo = [lower_id(a["robot"], b["robot"]) == first for a, b, first in pairs]
        row["lower_id"] = {"acc": float(np.mean(lo)) if lo else None, "k": int(sum(lo))}
        res_t[name] = row
    out["heldout_temporal"] = res_t

    # Battery items (mapped subset), one pass.
    vlm = {b: vlm_correct(b) for b in ("openai", "gemini")}
    manifest = {i["item_id"]: i for i in json.loads(c.MANIFEST_V2.read_text())["items"]}
    bat = [s for s in meta if s.get("role") == "battery"]
    items = []
    by_item = defaultdict(list)
    for s in bat:
        by_item[s["item_id"]].append(s)
    for item_id, ss in sorted(by_item.items()):
        it = manifest[item_id]
        rec = {"item_id": item_id, "probe_type": it["probe_type"], "run_id": it["run_id"], "correct_answer": it["correct_answer"]}
        for v in ("dyn", "static"):
            F = feats[v][0]
            if it["probe_type"] == "conflict_prediction":
                m = models[v]["conflict"]
                prob = float(m["model"].predict_proba(m["scaler"].transform(conflict_x(F, [ss[0]["uid"]])))[0, 1])
                ans = "yes" if prob >= 0.5 else "no"
                rec[f"{v}_score"] = prob
            else:
                m = models[v]["temporal"]
                pr = dict(zip([s["robot"] for s in ss], m["model"].predict(m["scaler"].transform(temporal_x(F, [s["uid"] for s in ss])))))
                ans = max(pr, key=pr.get)
                rec[f"{v}_score"] = {k: float(np.expm1(x)) for k, x in pr.items()}
            rec[f"{v}_answer"] = ans
            rec[f"{v}_correct"] = ans == it["correct_answer"]
        if it["probe_type"] == "conflict_prediction":
            a, b = it["question_key"].split("|")
            rec["cpa_answer"] = "yes" if cpa_yes(track(it["run_id"]), a, b, it["sim_time_sec"]) else "no"
            rec["cpa_correct"] = rec["cpa_answer"] == it["correct_answer"]
            rec["always_yes_correct"] = it["correct_answer"] == "yes"
        else:
            kind, _, pair = it["question_key"].partition(":")
            a, b = pair.split("|")
            rec["lower_id_correct"] = lower_id(a, b) == it["correct_answer"]
            sa, sb = it["derivation"].get(f"m1_status_{a}"), it["derivation"].get(f"m1_status_{b}")
            stopped = [r for r, st in ((a, sa), (b, sb)) if st == "STOPPED"]
            pick = stopped[0] if len(stopped) == 1 else lower_id(a, b)
            rec["drawn_stopped_rule_correct"] = pick == it["correct_answer"]
            rec["m1_status"] = {a: sa, b: sb}
        for bk, rows in vlm.items():
            r = rows.get(item_id)
            rec[f"{bk}_correct"] = bool(r and r.get("correct"))
            rec[f"{bk}_option"] = r.get("parsed_option") if r else None
        items.append(rec)
    out["battery_items"] = items
    summary = {}
    for ptype in ("conflict_prediction", "temporal_order"):
        sub = [r for r in items if r["probe_type"] == ptype]
        cols = ["dyn", "static", "openai", "gemini"] + (["cpa", "always_yes"] if ptype == "conflict_prediction" else ["lower_id", "drawn_stopped_rule"])
        row = {"n_mapped": len(sub)}
        for col in cols:
            ok = [r[f"{col}_correct"] for r in sub]
            row[col] = {"k": int(sum(ok)), "wilson": wilson(int(sum(ok)), len(ok))}
        for vlm_name in ("openai", "gemini"):
            for v in ("dyn", "static"):
                row[f"mcnemar_{v}_vs_{vlm_name}"] = mcnemar_exact([r[f"{v}_correct"] for r in sub], [r[f"{vlm_name}_correct"] for r in sub])
        row["mcnemar_dyn_vs_static"] = mcnemar_exact([r["dyn_correct"] for r in sub], [r["static_correct"] for r in sub])
        summary[ptype] = row
    out["battery_summary"] = summary
    (MODEL_DIR / "results.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps({"heldout_conflict": res_c, "heldout_temporal": res_t, "battery_summary": summary}, indent=1, default=float))


if __name__ == "__main__":
    {"fit": cmd_fit, "score": cmd_score}[sys.argv[1]]()
