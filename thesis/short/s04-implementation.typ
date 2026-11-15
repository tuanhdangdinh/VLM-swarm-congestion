#import "../lib.typ": *

= Implementation <sec:s-impl>

*Stack.* Isaac Sim 6.0.1 @isaacsimdocs runs on a cloud virtual machine with an NVIDIA L4 GPU, with ROS 2 Jazzy @macenski2022robot and one Nav2 stack per robot @macenski2020marathon in a container on the same machine#ev("4.02")#ev("4.03"). The robots are TurtleBot3 Burger models#ev("4.05") articulated by Isaac Sim's Newton backend#ev("4.33"). Every evaluated run used Gemini Robotics-ER 2 (`gemini-robotics-er-2-preview`, "ER-2") @google2026geminier as the live model; `gpt-4o-2024-08-06` ran in an October live intersection pilot, earlier head-on runs and offline replays, and `claude-sonnet-5-5` offline only#ev("4.07"). Experimental cells ran from a prepared kit whose pin gate compares every runtime file's checksum with its registered value before each episode.

*Prompt.* The system prompt is one assistant line; the user prompt (version 3.4 in the evaluated runs) holds the robot states, pairwise distances and facing, the known identifiers, an optional summary of the previous attempt, a gloss of each congestion type and strategy, the plan grammar and the JSON output schema#ev("4.17"). An earlier ending that invited free-form reasoning in a `<think>` block was replaced by a JSON-only ending, because it contradicted the registered ban on spatial chain-of-thought and made one model refuse most attempts#ev("4.17"). The annotated overhead frame is attached as an image after the text. @fig:s-prompt shows an abridged recorded prompt; the full recorded prompts and answers are in the Extended Report, Appendix C.

#figure(
  kind: raw,
  supplement: [Listing],
  block(width: 100%)[
    #show raw: set text(size: 7.5pt)
    ```text
You are a warehouse swarm robotics traffic controller. Analyze the overhead camera view […]

Robot states:
- robot_id=robot_1, x=-0.36, y=0.00, theta=0.00, status=STOPPED, goal_x=1.75, goal_y=0.00, […]
- robot_id=robot_2, x=0.22, y=0.00, theta=3.14, status=STOPPED, goal_x=-1.75, goal_y=0.00, […]
- robot_id=robot_3, x=0.02, y=-0.38, theta=1.50, status=STOPPED, goal_x=0.00, goal_y=1.75, […]
- robot_id=robot_4, x=0.01, y=0.23, theta=-1.42, status=SLOW, goal_x=0.00, goal_y=-1.75, […]

Pairwise geometry (faces = heading within 60° of the direction to the other robot):
- robot_1 <-> robot_2: distance 0.58 m; robot_1 faces robot_2: yes; robot_2 faces robot_1: yes
[… four more pairs …]
- robot_3 <-> robot_4: distance 0.60 m; robot_3 faces robot_4: yes; robot_4 faces robot_3: yes

Known robot IDs: ["robot_1", "robot_2", "robot_3", "robot_4"]

Guidance:
- Robots are roughly 0.3 m wide; treat any two robots within ~0.5 m of each other […]
[… five more guidance lines, the plan invitation and the plan grammar …]
Produce a JSON object with exactly these fields:
- "reasoning": one to three sentences of your analysis, written before you commit […]
- "congestion_detected": true or false
- "type": "none" | "deadlock" | "bottleneck" | "crowding" | "anomaly"
[…]
- "strategy": one of
  - "none": no congestion to resolve
  - "yield": one robot (yield_robot) backs up and steps aside while the others pass
  [… five more strategy glosses …]
  - "junction_clear": multi-robot junction recovery: some robots first back out, […]
[… justification, yield_robot, blocker_kind, crossing_order, proposed_plan, rules …]

Write ONLY the final JSON object, with no surrounding text or markdown.
    ```
  ],
  caption: flex-caption([Abridged excerpt of a recorded v3.4 user prompt.], [Abridged user prompt, version 3.4, from an analysis in episode 3 of intersection run 1 (coordination layer on, four robots jammed in the junction, robots in ascending identifier order). Cuts are marked "[…]"; kept text is verbatim. The annotated overhead image is sent after the text. The full prompt, system prompt and model answer are in the Extended Report, Appendix C.#fig-source("4.39")]),
) <fig:s-prompt>


*Later extensions (not evaluated).* After the pinned runtime, several mechanisms were built behind keys that are off by default and ran in no evaluated experiment: a scope fix for the safety exemption#ev("6.07"); an escort obstacle guard and a reverse obstacle guard that refuse a straight leg crossing a declared obstacle#ev("6.13"); an execution-side stall abort that ends a primitive whose commanded motion produces no measured movement#ev("6.18"); geometric contact logging#ev("6.12"); a queued-robot hold for the convoy scene#ev("6.19"); and a convoy yielder correction#ev("6.85"). In scripted safety tests with no model call, the reverse guard and the stall abort were each validated live once (n = 1 per mechanism); the escort guard is validated offline only#ev("6.86").

== Physical Demonstration Setup <sec:s-impl-physical>

On 12 November 2026 the detect-to-dispatch chain ran on four physical TurtleBot3 robots under an overhead Intel RealSense camera, with `gemini-3.1-flash-lite` as the model#ev("4.28")#ev("4.29"). According to the team's testbed notes, which are outside the repository, each robot had a Raspberry Pi and an OpenCR motor controller, and five local ROS 2 graphs (a central laptop and four robots) were joined by Zenoh in a star, carrying only each robot's odometry and velocity-command topics; the safety boundary was 0.50 m and the speed limit 0.08 m/s#ev("4.41")#ev("4.30"). The configuration is reproduced in the Extended Report, Appendix D. The code that ran on the robots is not in the repository's history, and the hardware results are never pooled with the simulation results.
