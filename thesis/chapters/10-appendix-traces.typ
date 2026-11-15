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
  caption: flex-caption([Convoy take 1: the first yield.], [Four-robot convoy counterflow, demonstration take 1 of 5 (unresolved), simulated time 38.0 s: the first yield executes as the model named it. `robot_2` (green) backs out of the gap while `robot_1` waits in it and `robot_3` and `robot_4` stay queued; the decision named only the standoff pair.#fig-source("6.40")]),
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
    [`demo_campaign_combined.mp4`], [`de8cb6ed07e42008b8acb3f9274352db`], [excerpts of all four scenes plus the earlier run (version 3)],
  ),
  caption: flex-caption([Demonstration videos.], [Demonstration videos with md5. Every video is an illustrative demo, not controlled evidence.#fig-source("6.01")]),
) <tab:app-videos>
]

== Offline Contact Recompute (Pending Validation) <sec:app-contacts>

@tab:app-contacts lists the offline recompute of footprint gaps over 44 recorded bundles: the demonstration takes, both intersection runs and the registered five-robot pilot #ev("6.12"). For every ground-truth row the URDF collision shapes are placed at the logged pose, and the signed planar gap to every box (walls, racks, barrier blocks and declared obstacles) and to every other robot is measured. A gap of 5 mm or less is a contact entry. The values are a geometric footprint proximity at 10 Hz, not a physics contact. *They are pending validation:* they become citable as measurements only after a live run shows that entries appear when a robot is pinned, which the validation take could not show #ev("6.17"). The one sustained contact in the table is independently confirmed from the demonstration record #ev("6.42"). Gaps are in millimetres, rounded to 0.1 mm (so the five-robot minimum of −0.16 mm reads −0.2), times in simulated seconds, and r$n$ stands for `robot_`$n$.

#[
#set text(size: 8pt)
#show raw: set text(size: 6.5pt)
#figure(
  table(
    columns: (0.75fr, 1.55fr, 0.5fr, 0.75fr, 1.7fr, 0.7fr, 1.3fr),
    align: left,
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    inset: 3pt,
    table.header([*Group*], [*Bundle*], [*Rows*], [*Static verdict*], [*Min static gap (robot, box, time)*], [*Robot–robot verdict*], [*Min robot–robot gap (pair, time)*]),
    [demo], [`cvD_t01_a1`], [2601], [clear], [103.0 (r4, `aisle_barrier/north`, 65.0)], [clear], [195.0 (r1/r2, 67.2)],
    [demo], [`cvD_t02_a1`], [2601], [clear], [137.3 (r1, `rack/NW`, 53.9)], [clear], [176.3 (r1/r2, 25.7)],
    [demo], [`cvD_t03_a1`], [2601], [clear], [96.8 (r4, `aisle_barrier/north`, 65.5)], [clear], [190.1 (r1/r2, 26.1)],
    [demo], [`hoD_t01_a1`], [3001], [clear], [44.5 (r2, `aisle_barrier/north`, 121.0)], [clear], [138.8 (r1/r2, 22.3)],
    [demo], [`ibD_t01_a1`], [585], [clear], [511.0 (r1, `rack/NW`, 0.0)], [clear], [2302.5 (r2/r3, 34.3)],
    [demo], [`ibD_t01_a2`], [3001], [clear], [136.4 (r1, `rack/NW`, 56.3)], [clear], [191.6 (r1/r2, 76.1)],
    [demo], [`ibD_t02_a1`], [3001], [clear], [131.0 (r1, `rack/SW`, 74.9)], [clear], [135.6 (r2/r4, 28.7)],
    [demo], [`ibD_t03_a1`], [3001], [clear], [93.6 (r1, `rack/NW`, 130.5)], [clear], [153.8 (r2/r3, 28.0)],
    [demo], [`ibD_t04_a1`], [3001], [clear], [129.3 (r1, `rack/SW`, 72.8)], [clear], [147.6 (r2/r3, 28.2)],
    [demo], [`ibD_t05_a1`], [3001], [clear], [129.4 (r1, `rack/SW`, 73.8)], [clear], [149.0 (r1/r4, 27.9)],
    [demo], [*`m5D_t01_a1`*], [6001], [*sustained contact*], [*−0.2 (r3, `obstacle_2`, 191.4)*], [clear], [85.0 (r1/r4, 42.6)],
    [Intersection run 1], [`ib10L_e01_armA_a1`], [3001], [clear], [103.5 (r1, `rack/NW`, 131.9)], [clear], [152.0 (r1/r3, 28.2)],
    [Intersection run 1], [`ib10L_e01_armA_a2`], [3001], [clear], [132.3 (r1, `rack/SW`, 72.8)], [clear], [156.8 (r2/r3, 27.7)],
    [Intersection run 1], [`ib10L_e02_armB_a1`], [3001], [clear], [504.9 (r3, `rack/SE`, 23.3)], [clear], [140.0 (r1/r4, 27.6)],
    [Intersection run 1], [`ib10L_e03_armA_a1`], [3001], [clear], [128.5 (r1, `rack/SW`, 126.6)], [clear], [145.0 (r2/r4, 26.5)],
    [Intersection run 1], [`ib10L_e04_armB_a1`], [3001], [clear], [496.5 (r3, `rack/SE`, 24.1)], [clear], [126.8 (r2/r3, 27.7)],
    [Intersection run 1], [`ib10L_e05_armA_a1`], [3001], [clear], [108.7 (r1, `rack/NW`, 131.4)], [clear], [139.5 (r1/r4, 28.6)],
    [Intersection run 1], [`ib10L_e06_armB_a1`], [3001], [clear], [487.6 (r3, `rack/SE`, 23.4)], [clear], [157.5 (r2/r3, 27.4)],
    [Intersection run 1], [`ib10L_e07_armA_a1`], [3001], [clear], [101.3 (r1, `rack/NW`, 130.4)], [clear], [172.9 (r2/r3, 28.1)],
    [Intersection run 1], [`ib10L_e08_armB_a1`], [3001], [clear], [497.2 (r3, `rack/SE`, 24.6)], [clear], [151.1 (r1/r4, 27.3)],
    [Intersection run 1], [`ib10L_e09_armA_a1`], [3001], [clear], [121.9 (r1, `rack/NW`, 57.5)], [clear], [82.1 (r1/r2, 295.4)],
    [Intersection run 1], [`ib10L_e10_armB_a1`], [3001], [clear], [490.1 (r3, `rack/SE`, 21.8)], [clear], [163.1 (r2/r3, 27.5)],
    [Intersection run 2], [`ib10S_e01_armA_a1`], [3001], [clear], [95.9 (r1, `rack/NW`, 129.7)], [clear], [121.7 (r3/r4, 109.4)],
    [Intersection run 2], [`ib10S_e02_armC_a1`], [3001], [clear], [171.0 (r1, `rack/SW`, 283.6)], [clear], [1772.2 (r2/r3, 43.7)],
    [Intersection run 2], [`ib10S_e02_armC_a2`], [3001], [clear], [115.8 (r1, `rack/NW`, 131.9)], [clear], [149.6 (r1/r4, 27.5)],
    [Intersection run 2], [`ib10S_e03_armA_a1`], [3001], [clear], [125.0 (r1, `rack/SW`, 71.8)], [clear], [155.0 (r2/r3, 27.3)],
    [Intersection run 2], [`ib10S_e04_armC_a1`], [3001], [clear], [130.2 (r1, `rack/SW`, 74.1)], [clear], [157.3 (r2/r3, 27.0)],
    [Intersection run 2], [`ib10S_e05_armA_a1`], [3001], [clear], [125.0 (r1, `rack/SW`, 73.6)], [clear], [162.3 (r2/r3, 28.1)],
    [Intersection run 2], [`ib10S_e06_armC_a1`], [3001], [clear], [128.1 (r1, `rack/SW`, 74.2)], [clear], [159.8 (r2/r3, 27.3)],
    [Intersection run 2], [`ib10S_e07_armA_a1`], [3001], [clear], [130.7 (r1, `rack/SW`, 71.0)], [clear], [134.9 (r2/r3, 26.1)],
    [Intersection run 2], [`ib10S_e08_armC_a1`], [3001], [clear], [129.4 (r1, `rack/SW`, 73.5)], [clear], [201.5 (r1/r2, 89.8)],
    [Intersection run 2], [`ib10S_e09_armA_a1`], [3001], [clear], [110.0 (r1, `rack/NW`, 132.3)], [clear], [185.0 (r1/r3, 29.4)],
    [Intersection run 2], [`ib10S_e10_armC_a1`], [3001], [clear], [130.5 (r1, `rack/SW`, 75.0)], [clear], [142.3 (r2/r3, 27.9)],
    [Registered pilot], [`E27 A a1`], [6001], [clear], [34.8 (r1, `obstacle_1`, 99.8)], [clear], [221.9 (r1/r5, 581.7)],
    [Registered pilot], [`E27 B a1` (bring-up abort)], [670], [clear], [97.9 (r4, `rack/SW_west`, 37.8)], [clear], [1922.8 (r1/r2, 29.4)],
    [Registered pilot], [`E27 B a2`], [6001], [clear], [34.7 (r5, `obstacle_2`, 50.4)], [clear], [215.8 (r3/r4, 46.9)],
    [Registered pilot], [`E28 A a1`], [6001], [clear], [28.1 (r5, `rack/SE_east`, 104.4)], [clear], [223.5 (r1/r5, 45.5)],
    [Registered pilot], [`E28 B a1`], [6001], [clear], [41.1 (r1, `obstacle_2`, 42.5)], [clear], [101.1 (r1/r5, 44.8)],
    [Registered pilot], [`E29 A a1`], [6001], [clear], [7.1 (r2, `obstacle_2`, 42.8)], [clear], [133.4 (r1/r4, 46.4)],
    [Registered pilot], [`E29 B a1`], [6001], [clear], [14.0 (r1, `obstacle_1`, 38.8)], [clear], [119.4 (r1/r4, 46.1)],
    [Registered pilot], [*`E30 A a1`*], [6001], [*brief graze*], [*1.0 (r2, `obstacle_1`, 48.9)*], [clear], [231.7 (r3/r4, 44.9)],
    [Registered pilot], [`E30 B a1`], [6001], [clear], [10.0 (r2, `obstacle_1`, 47.9)], [clear], [169.1 (r3/r4, 43.3)],
    [Registered pilot], [`E31 A a1`], [6001], [clear], [19.3 (r2, `obstacle_2`, 44.3)], [clear], [178.9 (r1/r5, 577.2)],
    [Registered pilot], [`E31 B a1`], [6001], [clear], [8.7 (r2, `obstacle_2`, 42.0)], [clear], [209.3 (r1/r5, 41.2)],
  ),
  caption: flex-caption([Offline contact recompute over 44 bundles (pending validation).], [Offline footprint-gap recompute over 44 recorded bundles, pending validation. Robot–static: one sustained contact, two brief grazes within noise, 42 bundles clear. Robot–robot: closest footprint gap 82.1 mm. Two short bundles (a bring-up abort and an early-ended take) and one run that formed no jam have robot–robot minima above 1.7 m.#fig-source("6.12")]),
) <tab:app-contacts>
]
