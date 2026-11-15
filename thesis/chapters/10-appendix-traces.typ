#import "../lib.typ": *
#import "../figures/vlm-flow-take5.typ": vlm-flow-figure

= Decision Trace and Demonstration Material <sec:app-traces>

This appendix gives the full decision trace of intersection take 5, the further demonstration stills, the list of demonstration videos, and the offline contact recompute that @sec:res-safety summarises.

== Decision Trace of Intersection Take 5 <sec:app-flow>

@fig:app-flow-take5 traces intersection take 5 (@sec:res-demo-ib) stage by stage with the run's own output; @fig:ch6-flow-take5-simple is its simplified form.

#figure(
  vlm-flow-figure(),
  kind: image,
  placement: auto,
  caption: flex-caption([Decision flow of one live take, annotated with its real output.], [Decision flow of one live run, annotated with its real output (four-robot intersection, demonstration take 5 of 5, selected as the only take labelled VLM-driven execution); text is copied from the run and trimmed (…). Only the back-out order was the model's, a near-tie: back-out costs 0.981 m (`robot_3`) and 0.971 m (`robot_4`) differ by 0.010 m, within the verifier's 0.15 m tolerance; the distances in the back-out phases are commanded distances, and the reason for the difference was not established. The bottom strip is from a different take (two-robot head-on corridor with obstacle, decision 2, n = 1), in which the feasibility gate replaced the model's yielder. Safety rested on robot-pair distance only: the execution and safety monitor (M4) has no obstacle check, no stage checked escort or back-out paths against obstacles, and the scene declares no static obstacles to the grounder (M3) #ev("6.43") #ev("6.13"). Illustrative, not controlled evidence.#fig-source("6.01")]),
) <fig:app-flow-take5>

== Further Demonstration Stills <sec:app-stills>

The stills below complete the demonstration takes of @sec:res-demo and the earlier recorded head-on run of @sec:res-headon. All are from Isaac Sim, annotated overhead camera frames (box colours show perception status), illustrative takes with no rate drawn from them.

#figure(
  image("../assets/images/fig_intersection_panel_dispatch_t33p07.png", width: 100%),
  caption: flex-caption([Format of the demonstration videos.], [Format of the demonstration videos: one frame of the panel video of four-robot intersection take 5 (labelled VLM-driven execution, chosen for that label) at simulated time 33.1 s. Left: the annotated overhead camera stream with the renderer's captions. Right: the run's own orchestrator (M5) and execution-monitor (M4) log lines replayed in sync, here the decision (`junction_clear`, plan accepted unchanged, `vlm_verbatim`) and the dispatch of `robot_3`'s back-out.#fig-source("6.01")]),
) <fig:ch6-demo-panel>

#figure(
  image("../assets/images/fig_intersection_all_arrived_t154p83.png", width: 75%),
  caption: flex-caption([Intersection take 5: all four robots at their goals.], [Four-robot intersection, demonstration take 5 of 5, simulated time 154.8 s: all four robots stopped at their goals on the opposite arms (GT arrivals between 95.1 s and 146.4 s). Take 1 was unresolved and takes 2 to 4 were grounder-default resolutions.#fig-source("6.39")]),
) <fig:ch6-ib-arrived>

#figure(
  image("../assets/images/fig_convoy_first_yield_t38p00.png", width: 75%),
  caption: flex-caption([Convoy take 1: the first yield.], [Four-robot convoy counterflow, demonstration take 1 of 6 (unresolved), simulated time 38.0 s: the first yield executes as the model named it. `robot_2` (green) backs out of the gap while `robot_1` waits in it and `robot_3` and `robot_4` stay queued; the decision named only the standoff pair.#fig-source("6.40")]),
) <fig:ch6-cv-yield>

#figure(
  image("../assets/images/fig_headon_robot2_yield_pass_t99p00.png", width: 75%),
  caption: flex-caption([Head-on take: `robot_1` passes the parked `robot_2`.], [Two-robot head-on corridor with obstacle, demonstration take 1 of 1 (grounder-default resolution, grounder-corrected), simulated time 99.0 s: `robot_2` is parked at its pull-off point beside the lane (red, stopped) while `robot_1` (green) is escorted past it.#fig-source("6.37")]),
) <fig:ch6-ho-pass>

#figure(
  image("../assets/images/fig_headon_both_arrived_t147p93.png", width: 75%),
  caption: flex-caption([Head-on take: both robots at their goals.], [Two-robot head-on corridor with obstacle, demonstration take 1 of 1 (grounder-default resolution, grounder-corrected), simulated time 147.9 s: both robots at their goals, `robot_2` at the left beside the obstacle and `robot_1` at the right edge (GT arrivals at 112.5 s and 136.1 s).#fig-source("6.37")]),
) <fig:ch6-ho-arrived>

#figure(
  image("../assets/images/fig_fiverobot_standoff_t43p67.png", width: 75%),
  caption: flex-caption([Five-robot take: the first standoff.], [Five-robot pickup-and-delivery scene (seed position 21, an exploratory seed outside the 20 confirmatory seeds), demonstration take 1 of 1 (unresolved; a limitation demonstration), simulated time 43.7 s, before the first decision: two rack islands; `robot_1` and `robot_4` meet head-on at the bottom (yellow, slow), and the other three are moving. The start assignment differs from the scene figure of Chapter 5.#fig-source("6.42")]),
) <fig:ch6-m5-start>

#figure(
  image("../assets/images/fig_fiverobot_after_decision1_t101p40.png", width: 75%),
  caption: flex-caption([Five-robot take: after the first decision.], [Five-robot scene, seed position 21, demonstration take 1 of 1 (unresolved), simulated time 101.4 s, after decision 1, executed as the model named it: `robot_1` yielded and `robot_4` passed, and both stand at the left edge. `robot_2` and `robot_3` are stopped beside the east island, the conflict of decision 2. Of eight decisions, two were executed and six withheld by grounding refusals; 1 of 5 robots arrived.#fig-source("6.42")]),
) <fig:ch6-m5-after1>

#figure(
  image("../assets/images/fig_er2live_robot2_aside_robot1_passing_t86p30.png", width: 75%),
  caption: flex-caption([Earlier head-on run: the model's yielder kept and executed.], [Two-robot head-on corridor with obstacle, earlier recorded head-on run (30 Sep 2026, older code, not part of the demonstration campaign), simulated time 86.3 s. `robot_2`, the yielder the model named and the feasibility gate kept, has backed out and parked beside the lane, and `robot_1` is escorted past it. The model named the second-listed robot, and its second-stage retreat pick was the first-listed of two mirror-equivalent options. 2 of 2 arrived, `robot_2` only after a navigation-stack stall and recovery. n = 1, chosen because the model's yielder was kept.#fig-source("6.38")]),
) <fig:ch6-er2live>

#figure(
  grid(
    columns: (1fr, 1fr),
    column-gutter: 8pt,
    image("../assets/images/fig_convoy_rerun_held_robot1_crossing_t61p87_clean.png"),
    image("../assets/images/fig_convoy_rerun_all_arrived_t189p93_clean.png"),
  ),
  caption: flex-caption([Convoy rerun take: queued robots held, then all at their goals.], [Four-robot convoy counterflow scene, rerun take (1 of 1, after five unresolved convoy takes), overhead camera frames with the recorder's clock cropped. Left, simulated time 61.87 s: `robot_1` is escorted through the gate while the grounder's queued-robot hold keeps `robot_3` and `robot_4` in place. Right, 189.93 s: all four robots at their goals. Label: resolved, grounder held the queued robots; the model chose the strategy and the yielder (`robot_2`) but named only the two robots in the standoff. The yielder correction was armed and did not fire, so it is untested live. Illustrative, n = 1; not evidence that the VLM resolves convoy congestion.#fig-source("6.84")]),
) <fig:app-convoy-rerun>

== Demonstration Videos <sec:app-videos>

The demonstration videos are kept outside the repository, on the owner's machine; each is identified by its file name and md5 (@tab:app-videos). Each video is an illustrative demo, not controlled evidence. The panel videos show the annotated camera stream beside the run's own log lines, as in @fig:ch6-demo-panel #ev("6.01").

#[
#show raw: set text(size: 7pt)
#figure(
  table(
    columns: (1.45fr, 1.75fr, 1.5fr),
    align: left,
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([*File*], [*md5*], [*What it shows*]),
    [`ibD_t05_a1_panel.mp4`], [`fdf07a82fcb657b738c44a89bfbe3dae`], [intersection take 5, labelled VLM-driven execution],
    [`cvD_t01_a1_panel.mp4`], [`824319447d05aaef6623158d00d2818f`], [convoy take 1, unresolved],
    [`hoD_t01_a1_panel.mp4`], [`2aa6534ad508d3440e51822fdcd3f0f0`], [head-on take 1, grounder-default resolution (grounder-corrected)],
    [`m5D_t01_a1_panel.mp4`], [`33e9f5eedd7fb56edd007d8b728ea8c0`], [five robots, unresolved, with the escort caption],
    [`ER2LIVE_20260930_panel.mp4`], [`93cbfe7108e6a9ca9a71fc4c7c79bd47`], [earlier recorded head-on run (30 Sep 2026), the model's yielder kept by the gate; not part of the campaign],
    [`cvY_t01_a2_panel.mp4`], [`92fc06a855ae0527479d1bfe49af2fbc`], [convoy rerun take, resolved: grounder held the queued robots; model chose strategy and yielder],
    [`demo_campaign_combined.mp4`], [`de8cb6ed07e42008b8acb3f9274352db`], [excerpts of all four scenes plus the earlier run (version 3)],
    [`cvY_t01_a2_presentation.mp4`], [`60c4ee7c46e9f6ded4f8f3496589e1e0`], [presentation cut of the convoy rerun take],
    [`presentation_combined.mp4`], [`3d45c8d850952f9b7013bd154957034a`], [presentation excerpts including the convoy rerun (version 2); two older convoy excerpts carry a burned-in "take 1 of 3" header, although there were five such takes],
  ),
  caption: flex-caption([Demonstration videos.], [Demonstration videos with md5. Every video is an illustrative demo, not controlled evidence.#fig-source("6.01") #fig-source("6.84")]),
) <tab:app-videos>
]
