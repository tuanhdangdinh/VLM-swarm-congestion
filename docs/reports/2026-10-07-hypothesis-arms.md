# Hypothesis Arms: gemini-3.8-flash (H1) and Molmo2-ER (H2)

**Prepared:** 2026-10-07

**Revision history:**

- Initial draft: H1/H2 reading rule registered before any battery call (results pending).

---

## Registered Reading Rule

Written 2026-10-06T16:45Z, before any probe-battery call on either new arm (only the gemini-3.8-flash preflight had run). Nothing below may be tuned to the data.

**The two hypotheses:**

- **H1, lab-controlled specialization.** gemini-3.8-flash versus Gemini Robotics-ER 2. The lab (Google), the adapter and the packing are held, and so is the thinking dose (`thinking_level: low` on both). What varies is robotics tuning. Question: does ER-2's conflict_prediction lead survive against its own lab's generalist?
- **H2, cross-lab specialist replication.** Molmo2-ER versus ER-2. Embodied specialization is held, and the lab varies (Ai2 versus Google). Question: does a second embodied specialist replicate ER-2's conflict_prediction profile?

**Anchor measure.** Battery v2 main `conflict_prediction`: the same 20 frozen items (`manifest_v2.json`, sha256 `faf1953b…`), the frozen v1 probe template, one call per item.

**Statistics, per arm against ER-2's 2026-10-04 run:**

- accuracy with Wilson 95% CI;
- the GT-yes / GT-no split and the "yes" rate;
- an exact two-sided McNemar test on the per-item discordant pairs.

**Reading of the lead.** ER-2 scored 16/20 [0.58, 0.92]. Its "lead" is a lead over gpt-4o only (9/20, at chance). It ties or trails Sonnet (16), gpt-5.1 (15), Qwen (15) and DeepSeek (19) on overlapping CIs. So:

- **H1 verdict rule:**
  - flash ≤ 10/20, or its Wilson upper bound < 0.66 → **H1 SUPPORTED**: the dynamics advantage tracks robotics tuning within the lab.
  - flash ≥ 14/20 with a McNemar p ≥ 0.05 against ER-2 → **H1 NOT SUPPORTED**: the lab's generalist lands with ER-2, so the "lead" is a lab/generation property, not specialization.
  - Anything else (11–13/20, or ≥ 14 but significantly different) → **INCONCLUSIVE at n = 20**, reported with the split and yes-rate.
- **H2 verdict rule:**
  - Molmo2-ER ≥ 14/20 with McNemar p ≥ 0.05 against ER-2 → **H2 REPLICATED**: a second specialist lands with ER-2.
  - Molmo2-ER ≤ 10/20, or its Wilson upper bound < 0.66 → **H2 NOT REPLICATED**.
  - Otherwise → **INCONCLUSIVE at n = 20**.
- **Profile check, both arms.** A score reached by always-yes or never-yes (yes-rate ≥ 18/20 or ≤ 2/20) is reported as a degenerate profile, whatever the verdict rule says.

**Secondary evidence, not used for the verdicts:**

- probe battery v1 (60, at ceiling and unable to rank backends);
- motion_direction (arrow-confounded);
- temporal_order (QUARANTINED);
- the head-on plan metrics.

The new arms' head-on episodes run prompt v3.4. Every earlier arm's episodes ran v3.2 or v3.3, so any head-on comparison is confounded by prompt version.

**Structural confounds, stated up front:**

- **H1 is lab-matched, not base-matched.** ER-2's base model is undocumented, so flash and ER-2 may differ in generation and size as well as in tuning.
- **H2 confounds scale and serving with lab.** Molmo2-ER is a 4.85B open model served locally in bf16; ER-2 is a hosted frontier-scale preview.
