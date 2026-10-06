# PILOT: Motion-Trails-On Re-Run of Battery-v2 Main Probes (Same Frames, Offline)

**Prepared:** 2026-10-06

**Status:** PILOT — exploratory, EXCLUDED from all confirmatory counts.

**Revision history:**

- Rev 0 (pre-registration, committed before any API call): method, fidelity checks, arms, decision rule.

---

## Decision Rule (Fixed Before Any API Call)

Arms, all on the 59 frozen battery-v2 `main` items (`manifest_v2.json`,
SHA `faf1953b…`), same frozen v1 prompt, same seeded lettering, same pinned
backends (gpt-4o-2024-08-06, gemini-robotics-er-2-preview), one call per
item, no re-ask:

- **ON** — trails-on composite of the same frame (all 59 items, both backends).
- **OFF-retest** — the frozen trails-off frame, re-asked the same day
  (conflict_prediction + temporal_order, 39 items, both backends), as a
  test-retest noise floor. Gemini's API drops temperature, so its answers
  are not deterministic.
- **OFF-frozen** — the 2026-10-04 battery-v2 main results (no new calls).

Primary comparison: ON vs OFF-retest per backend on conflict_prediction and
temporal_order; secondary: ON vs OFF-frozen on all three types. "Net" =
on-only-correct minus off-only-correct over matched items. "Drift" = the net
of OFF-retest vs OFF-frozen on the same items.

- **YES (register a trail arm in v3)** — for at least one backend, ON beats
  OFF-retest on conflict_prediction or temporal_order by net >= +3 of the
  type's items, AND that net is at least twice |drift| for the same
  backend × type, AND no backend × type shows net <= -3 (harm).
- **NO** — every backend × type on the primary comparison has |net| <= 2
  (no detectable change at pilot n), consistent with the battery-v2 40-pair
  null.
- **NEEDS-BIGGER-PILOT** — anything else (an effect of >= 3 that fails the
  drift test, or effects of opposite sign across backends/types).
- **Harm flag (reported regardless):** gpt-4o refusals ON minus OFF-retest
  >= +3 on the 39 shared items.

Results are reported for all 59 items and for the 44-item exact-history
subset (see Method); the decision uses all items, with the subset as a
robustness check.
