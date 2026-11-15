#import "../lib.typ": *

#[
  #set par(first-line-indent: 0pt)

  © 2026 Vietnamese-German University (VGU). All rights reserved.

  #v(1.5cm)

  // Plain bold text, not a heading: a level-1 heading would force a page break after the line above.
  #align(center)[#text(size: 14.4pt, weight: "bold")[Copyright]]

  #v(0.5cm)

  This report, including its text, figures, tables, and any accompanying materials, is the intellectual property of the authors and Vietnamese-German University. No part of this publication may be reproduced, stored, transmitted, or distributed in any form or by any means (electronic, mechanical, photocopying, recording, or otherwise) without prior written permission, except for brief quotations used for academic or non-commercial purposes with proper citation.

  #v(0.4cm)

  *Authors:* Dang Dinh Tu Anh; Nguyen Khanh Tuong

  #v(0.4cm)

  *Course Module:* Project Course \
  *Department:* Computer Science, Faculty of Engineering \
  *Institution:* Vietnamese-German University \
  *Location:* Ho Chi Minh City, Vietnam

  #v(1em)

  *Source code.* The source code of this project is kept in the repository below.

  #v(0.5em)

  #link("https://github.com/tuanhdangdinh/VLM-swarm-congestion")[
    #underline[https://github.com/tuanhdangdinh/VLM-swarm-congestion]
  ]
]

#pagebreak()

#[
  #set par(first-line-indent: 0pt)

  #align(center)[
    #heading(numbering: none, outlined: false)[Acknowledgements]
  ]

  #v(1.2cm)

  We would like to express our sincere gratitude to our supervisor, *Dr. Vo Bich Hien*, for his valuable guidance, constructive feedback, and continuous support throughout this project. His expertise and direction greatly helped us shape the research approach and improve the quality of this report.

  #v(0.6cm)

  We are also grateful to *Mr. Chau Thai Nguyen* for the support and advice he gave us during this project.

  #v(0.6cm)

  We also thank the *Department of Computer Science, Faculty of Engineering, Vietnamese-German University (VGU)* for providing an academic environment, resources, and opportunities that supported our work.

  #v(0.6cm)

  Finally, we would like to thank our classmates, friends, and families for their encouragement and motivation during the project period. Their support helped us stay focused and complete this report.

  #v(1fr)

  #align(right)[
    _The Authors_
  ]
]

#pagebreak()
#heading(numbering: none, outlined: false)[Abstract]
Local navigation does not decide which warehouse robot yields, so robots jam. This report asks whether a vision-language model (VLM) shown an annotated overhead frame and robot states classifies such a jam, chooses strategies that clear it, and names an effective yielder and order. A slow coordination layer detects the stall, asks the VLM for a congestion type and strategy and has a deterministic grounder repair, replace or refuse infeasible plans.

At a simulated four-robot intersection the coordination layer cleared the jam in 4 of 5 episodes, 0 of 5 when off; in a second run a scripted arm running the grounder's default plan with no VLM call did as well as the live-VLM arm (scripted: 4 of 4 valid, 5 of 5 after a post hoc re-run); both are exploratory five-episode pilots. In a registered five-robot pilot no episode of either arm completed (0 of 10). In the first twelve illustrative demonstration takes the model always answered validly; its plan was recorded as accepted in 6 of 65 analyses (dispatched as written in 5 of the 61 with a plan) and changed execution once, by reordering two near-equivalent back-outs. In head-on scenes the feasibility gate, not the model, made the yielder correct; classification was scored only after the stall trigger. Safety evidence is robot-pair distance only; one robot-obstacle contact was confirmed, earlier reverses pinned robots on boxes, and the later reverse guard and stall abort were each validated live once in a scripted safety test. On physical TurtleBot3 robots the chain ran end to end in four staged arrangements: the model chose a bounded back-out each time and all but one robot recorded it complete (one run each, no goals, illustrative). All quantitative results come from simulation, small samples and one VLM in the live comparisons.

#v(0.5em)
#par(first-line-indent: 0pt)[*Keywords:* warehouse robotics, multi-robot systems, congestion management, deadlock recovery, vision-language model, TurtleBot3, ROS 2, Zenoh, ArUco, overhead perception, deterministic grounding.]
#pagebreak()
#outline(title: "Contents", indent: auto)

#pagebreak()
#outline(title: "List of Figures", target: figure.where(kind: image))

#pagebreak()
#outline(title: "List of Tables", target: figure.where(kind: table))

#pagebreak()
#heading(numbering: none, outlined: false)[List of Abbreviations]
#table(
  columns: (auto, 1fr),
  stroke: none,
  table.header([*Abbreviation*], [*Meaning*]),
  [AI], [Artificial Intelligence],
  [API], [Application Programming Interface],
  [ArUco], [Square fiducial marker system],
  [CBF], [Control Barrier Function],
  [CBS], [Conflict-Based Search],
  [DDS], [Data Distribution Service (ROS 2 middleware standard)],
  [DOF], [Degree of Freedom],
  [DWB], [Name of the Nav2 local trajectory controller plugin used here],
  [ER-2], [Gemini Robotics-ER 2, the hosted VLM of the live experiments],
  [F1], [F1 score, harmonic mean of precision and recall],
  [GNN], [Graph Neural Network],
  [GPU], [Graphics Processing Unit],
  [GT], [Ground truth],
  [HTTP], [Hypertext Transfer Protocol],
  [JSON], [JavaScript Object Notation],
  [Layer 1, Layer 2], [Local navigation and the coordination layer of the two-layer architecture],
  [LLM], [Large Language Model],
  [M1--M6], [Modules of the system: perception (M1), VLM reasoning (M2), grounder (M3), execution and safety monitor (M4), orchestrator (M5), simulation (M6)],
  [MAPD], [Multi-Agent Pickup and Delivery],
  [MAPF], [Multi-Agent Path Finding],
  [MD5], [Message-Digest Algorithm 5 (checksum)],
  [Nav2], [ROS 2 Navigation stack],
  [ORCA], [Optimal Reciprocal Collision Avoidance],
  [PDDL], [Planning Domain Definition Language],
  [PIBT], [Priority Inheritance with Backtracking],
  [RGB], [Red, green, blue (colour image)],
  [RHCR], [Rolling-Horizon Collision Resolution],
  [ROS 2], [Robot Operating System 2],
  [RQ], [Research Question],
  [RTX], [NVIDIA ray-tracing renderer used by Isaac Sim],
  [SHA-256], [Secure Hash Algorithm with a 256-bit digest],
  [UDP], [User Datagram Protocol],
  [URDF], [Unified Robot Description Format],
  [USD], [Universal Scene Description],
  [VLM], [Vision-Language Model],
)
