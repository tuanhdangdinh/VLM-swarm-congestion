#import "../lib.typ": *

= Sources, Terms and Data Availability <sec:s-sources>

*Evidence Index.* Every number in this report is traced to a source: the Evidence Index, published in the companion *Extended Report* (Appendix E), lists each claim with the commit, file and section that support it. The Extended Report is submitted with this report and built from the same sources.

*How claims are traced.* The source files of this report attach to every number the identifier of its Evidence Index row; the identifiers are not printed, to keep the text readable. To check a claim, search the Evidence Index for it: each row repeats the claim in words, with the study it comes from. Table and figure captions name the study and its evidence grade.

*Extended Report.* The companion document holds the full version of every chapter: the complete methods of each study (Chapter 5), all results with their per-episode detail, the failure-cause and interception tables, the offline decision benchmark and the exploratory findings (Chapter 6), the full discussion and future work (Chapters 7 and 8); and its appendices: the source documents (A), the decision trace of intersection take 5, further demonstration stills and the video list (B), the recorded prompts and model answers (C), the physical testbed configuration (D), the Evidence Index (E) and two detail tables (F).

*Data availability.* The repository linked in the front matter holds the project's code, but not everything the Evidence Index cites. The source reports of November 2026 sit on local branches that were not pushed when this report was written; run bundles and demonstration videos are excluded from version control and kept on one machine, with no copy elsewhere; the physical demonstration's record is a README file outside the repository; and the physical testbed details come from the team's notes, also outside the repository#ev("6.16")#ev("1.07")#ev("4.41"). Commits and paths in the Evidence Index therefore identify sources but do not all resolve publicly.

== Terms <sec:s-terms>

#[
#set par(first-line-indent: 0pt, justify: false)
#set terms(separator: [: ], hanging-indent: 1.5em)
/ Bundle: the recorded files of one episode or take (ground truth, logs, decision records).
/ Censored: an episode that ended at the horizon (its time limit) before the event of interest.
/ Escort: the straight leg on which a passer is driven past a parked yielder.
/ Fidelity gate: a check that re-grounding a recorded decision reproduces the recorded dispatch; only decisions that pass are traced.
/ First check episode: the first episode of a run, executed alone so its harness could be accepted before the rest ran.
/ GT: ground truth, the simulator's own record of robot poses.
/ Plan channel: the prompt option that lets the model return a scene-wide plan, which the grounder audits.
/ Plan-order switch: an opt-in setting that lets a verified model plan set the order of `junction_clear` back-outs; used only in the demonstration campaign.
/ Second-stage call: a short follow-up VLM call that picks the yielder's retreat point among offered candidates.
/ Seed pair: one episode per arm from the same start assignment (seed position), so arms are compared pairwise.
/ Take labels: "unresolved failure" (not every robot reached its goal); "VLM-driven execution" (intersection only: a resolved take whose plans were accepted unchanged and dispatched as written, with a back-out order different from the grounder's default; it says the model's order ran, not that it helped); "grounder-default resolution" (every other resolved take, including gate swaps). The convoy rerun is labelled as resolved because the grounder held the queued robots.
/ Third design: the third registered research design (6 October 2026), under which the registered five-robot pilot ran.
/ Throughput at the common window: the fraction of the 25 tasks done, compared for each seed pair at the end of the shorter of its two episodes. Mean delay lower bound: the mean of each leg's travel time minus its solo travel time, where a leg that never arrives counts only up to the end of the episode.
/ Conflict: a ground-truth encounter of two robots below 0.45 m centre distance. Recall: the share of conflicts that a positive analysis matched. Type accuracy: the share of matched analyses whose type was the accepted label (deadlock). Involved-set F1: the overlap between the robots an analysis named and the conflict's robots.
]
