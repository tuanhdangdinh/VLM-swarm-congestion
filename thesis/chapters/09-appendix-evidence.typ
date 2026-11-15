#import "../lib.typ": *

= Sources and Evidence Index <sec:app-sources>

Every number in this report is traced to a source. The Evidence Index (@sec:supp-evidence) lists each claim with the commit, file and section that support it, and two detail tables follow it (@sec:supp-tables). The tables below list the documents the index draws on: design and registration documents (@tab:app-src-designs) and result and analysis reports (@tab:app-src-reports). Code files cited by line are listed in the supplement only.

*Data availability.* The repository linked in the front matter holds the project's code, but not everything the index cites. The source reports of November 2026 sit on local branches that were not pushed when this report was written; run bundles and demonstration videos are excluded from version control and kept on one machine, with no copy elsewhere; and the physical demonstration's record is a README file outside the repository #ev("6.16") #ev("1.07"). Commits and paths in the index therefore identify sources but do not all resolve publicly.

#[
#set text(size: 9pt)
#figure(
  table(
    columns: (auto, 1fr),
    align: left,
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([*Date*], [*Document*]),
    [–], [Module 5 (orchestrator) specification],
    [–], [Module 6 (simulation) specification],
    [–], [Module 4 safety-monitor specification],
    [–], [Offline VLM benchmark specification],
    [2026-07-05], [Research design (binding text of the first registration)],
    [2026-09-26], [First registered design: amendments],
    [2026-09-30], [Second registered design],
    [2026-10-06], [Third registered design],
    [2026-11-13], [Intersection run 1 registration],
    [2026-11-14], [Intersection run 2 registration (addendum)],
    [2026-11-15], [Demonstration campaign registration],
    [2026-11-15], [Scripted safety tests registration],
  ),
  caption: flex-caption([Design and registration documents cited.], [Design, specification and registration documents cited in the report, by date.]),
) <tab:app-src-designs>

#figure(
  table(
    columns: (auto, 1fr),
    align: left,
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([*Date*], [*Document*]),
    [2026-06-21], [Execution module (M4), phase 1 completion],
    [2026-06-21], [Simulator pose synchronisation investigation],
    [2026-09-18], [Two-robot head-on scene family: validity runs],
    [2026-09-25], [Real-frame replay of gpt-4o refusals],
    [2026-09-25], [gpt-4o refusals on the head-on frame],
    [2026-09-25], [Findings log, September build phase],
    [2026-10-03], [Scripted-oracle freeze for the second registered design],
    [2026-10-06], [Prompt version 3.4 and runtime re-pin],
    [2026-10-09], [Environment audit],
    [2026-10-12], [Retreat-shield fix and pilot mini-batch],
    [2026-10-21], [Registered five-robot pilot (tranche 1) results],
    [2026-10-22], [Offline VLM benchmark: baseline],
    [2026-10-23], [Offline benchmark: grounding-first candidates],
    [2026-10-23], [Offline benchmark: ER-2 replay],
    [2026-10-24], [Offline benchmark: grounding-first per-group candidates],
    [2026-11-12], [Per-group decision format],
    [2026-11-13], [Intersection run 1 results],
    [2026-11-13], [Five-robot scene: grounding refusals],
    [2026-11-13], [Safety-exemption trace],
    [2026-11-13], [Evidence register for this report],
    [2026-11-13], [Per-group live shadow results],
    [2026-11-14], [Head-on JSON-only replay results],
    [2026-11-14], [Head-on re-score: VLM against rules and the gate],
    [2026-11-14], [Head-on swapped-label replay results],
    [2026-11-14], [Intersection run 2 results (scripted default-plan arm)],
    [2026-11-14], [Improved-annotation replay results],
    [2026-11-14], [Safety-exemption scope fix],
    [2026-11-15], [Convoy held-robot prompt check],
    [2026-11-15], [Convoy queued-robot hold],
    [2026-11-15], [Convoy non-arrival and yielder correction],
    [2026-11-15], [Demonstration campaign results],
    [2026-11-15], [Escort and reverse obstacle guards],
    [2026-11-15], [Failure-cause evidence tool],
    [2026-11-15], [Failure-cause rating protocol],
    [2026-11-15], [Failure-cause rating, round 2],
    [2026-11-15], [Failure-cause reconciliation and interception],
    [2026-11-15], [Failure-cause rubric and plan-versus-dispatch finding],
    [2026-11-15], [Geometric contact logging and offline recompute],
    [2026-11-15], [Execution-side stall abort],
    [2026-11-15], [Plan-dispatch mismatch record],
    [2026-11-15], [Scripted safety tests results],
    [2026-11-15], [Plan-order prompt check],
    [2026-11-15], [Plan-influence trace],
    [2026-11-15], [Five-robot validation take results],
  ),
  caption: flex-caption([Result and analysis reports cited.], [Result and analysis reports cited in the report, by date. Titles follow the report file names.]),
) <tab:app-src-reports>
]
