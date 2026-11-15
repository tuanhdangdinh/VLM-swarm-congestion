#import "../lib.typ": *

= Background and Related Work <sec:s-background>

*Planning and reactive control.* Multi-agent path finding plans conflict-free paths for a fleet on a graph @stern2019multi, and its lifelong, warehouse form treats congestion as a first-order objective @ma2017lifelong @li2020lifelong @chen2023traffic. Such planners prevent jams by planning ahead, but once a jam has formed among robots running their own local planners, their model no longer matches what the robots do. Reactive methods @fox1997dynamic @vandenberg2011reciprocal keep each robot safe but do not decide who gives way, and for barrier-function controllers deadlock is an equilibrium on the boundary of the safe set @grover2019deadlock. The remedies layer a slower decision above the reactive one: a resolver that acts once robots are stuck @grover2019deadlock, re-timing of coordinated plans @cap2016provably, or yield-and-back-off at intersections @aoki2022drive. This report keeps Nav2 as the fast layer and puts a model-based decision in the slow one.

*Deadlock and its resolution.* The four classical deadlock conditions @coffman1971system carry over to robots once the contested resource is floor space, which is why a jam does not dissolve on its own: one robot must give up space it holds. For small groups in constrained spaces, social mini-games formalise doorways, hallways and intersections as navigation problems among conflicting agents @chandra2023deadlock. The literature resolves deadlock in four broad ways, each matching a strategy family of this report: perturbation onto deadlock-free states @grover2019deadlock @chandra2023deadlock, ordering by reservation or priority @dresner2008multiagent @okumura2022priority, recede and yield @aoki2022drive, and re-timing instead of re-routing @cap2016provably. Detection is usually a cheap progress test, with expensive reasoning reserved for after it fires @aoki2022drive @garg2026online; this report uses the same division. In classical resolvers, which mechanism applies to which scene is a designer's choice made in advance; the report asks whether a model can make that link online.

*Language and vision-language models as planners.* Multi-robot LLM planners decompose and allocate tasks from instructions @kannan2023smart @mandi2023roco @zhang2024lamma; closer to this report, Garg et al. let an LLM or VLM resolve deadlocks by assigning a leader and waypoints above a provably safe controller, calling the VLM only when a detector fires and prompting it with a top-view image @garg2024foundation @garg2026online, and LLMDR assigns deadlock strategies on grid benchmarks @seo2025llmdr. Set-of-Mark prompting overlays marks on an image to aid grounding @yang2023mark, the idea behind the annotated overhead frame used here.

*Grounding model output.* LLMs are limited at generating executable plans alone but useful with external verifiers; when a planner repairs a model's plan, much of the final plan is the planner's @valmeekam2023planning, and LLM-Modulo frameworks place model-based verifiers in the loop @kambhampati2024llms. Models choosing from a fixed menu also prefer particular option identifiers largely independently of content @zheng2023large. Both points shape this report: the grounder repairs or replaces the model's plan, so credit must be divided, and the model's yielder choice may follow its listing.

#[
#show figure: set block(breakable: true)
#figure(
  {
  set text(size: 8.5pt)
  set par(justify: false)
  table(
    columns: (1.05fr, 1.05fr, 1fr, 1.25fr, 1.05fr, 1.1fr),
    align: left,
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    inset: 4pt,
    table.header(
      [*Work*], [*Coordination*], [*Model input*], [*Grounding or feasibility layer*], [*Evaluation*], [*Safety layer*],
    ),
    [@garg2024foundation @garg2026online], [Central high-level planner over a distributed low-level policy], [Text (LLM), or top-view image with text (VLM)], [Model assigns a leader and waypoints; no separate check reported], [Simulation], [Distributed GNN controller; provably safe low-level policy in the extended version],
    [LLMDR @seo2025llmdr], [Central LLM over learned MAPF policies], [Text: agents' movement patterns], [Prioritised planning (PIBT) turns LLM priorities into moves], [Simulation (grid MAPF benchmarks)], [Conflict-free moves from the prioritised planner],
    [@dwedar2026safe], [Centralised server], [One robot's onboard camera (VLM); text (LLM)], [Reachability gate approves or withholds; no repair reported], [Physical robots (two, heterogeneous)], [Reachability gate holds sole command authority],
    [SwarmVLM @zafar2025swarmvlm], [Leader–follower pair], [Ceiling-mounted top-down camera], [VLM-selected impedance parameters], [Physical robots (drone and ground robot)], [Potential-field planning with impedance links],
    [RoCo @mandi2023roco], [Decentralised dialogue; central motion planner], [Text], [Environment feedback (e.g. collision checks) re-prompts the LLMs], [Simulation benchmark; real-world demonstration], [Collision checking of proposed plans],
    [SMART-LLM @kannan2023smart], [Centralised], [Text instruction], [n/r], [Simulation and real robots], [n/r],
    [COHERENT @liu2024coherent], [Central assigner; per-robot executors], [Text], [Executor feedback adjusts the plan], [Own task benchmark; platform n/r], [n/r],
    [LaMMA-P @zhang2024lamma], [Centralised], [Text], [PDDL problem solved by a classical planner], [Simulation (household benchmark)], [n/r],
    [GAVEL @wang2026gavel], [Single robot], [Text], [Graph world model predicts action effects; repairs violations it can, re-prompts the LLM for semantic errors], [Simulation (household benchmark)], [n/r],
    [Physical Agentic AI @liu2026physical], [Central mission planner; deterministic orchestrator], [Text: skill library, robot state, named locations, workflow contracts], [Orchestrator validates and authorises one skill at a time; refuses faulted steps], [Gazebo; two physical trials (humanoid and quadruped)], [Per-dispatch enforcement gate],
    [@chandra2023deadlock], [Decentralised], [–], [–], [Simulation and physical robots], [Control barrier functions],
    [*This report*], [Coordination layer over per-robot Nav2], [Annotated overhead camera frame with tracked robot states], [Deterministic geometric grounder: check, repair, replace or refuse, with a logged plan-audit label], [Isaac Sim; small physical TurtleBot3 demonstration], [Independent safety monitor (robot pairs) and execution gates below the reasoning layer],
  )
  },
  caption: flex-caption([Comparison of the closest works with this report.], [Comparison of the closest works with this report. "n/r" means not reported in the sources consulted (the paper's abstract or the project's reading notes); it does not mean the property is absent. "–" means not applicable, because the system uses no language model. The row for this report summarises Chapter 3; the Extended Report, Chapter 2, discusses each work.]),
) <tab:s-comparison>
]

*Gap.* As far as we found, no published system feeds a fixed overhead frame of a warehouse fleet to a VLM to classify congestion and choose among named strategies executed through a standard navigation stack, and none reports, per dispatch, how the model's plan fared in a deterministic check and whether it changed what was executed. The report claims no novelty for central deadlock recovery, a two-rate architecture or a propose-and-verify loop; its questions (@sec:s-intro-rq) follow from this gap, and every answer separates the model's share from the grounder's.
