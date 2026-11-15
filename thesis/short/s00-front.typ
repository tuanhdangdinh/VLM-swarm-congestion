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
Local navigation does not decide which robot yields, so warehouse robots jam. This report asks whether a vision-language model (VLM), given an annotated overhead frame and robot states, classifies such a jam, chooses a clearing strategy, and names an effective yielder and order. A coordination layer detects the stall and queries the VLM; a deterministic grounder repairs, replaces or refuses infeasible plans.

At a simulated four-robot intersection the coordination layer cleared the jam in 4 of 5 episodes (off: 0 of 5); a scripted default-plan arm with no VLM call matched the live-VLM arm (4 of 4 valid, 5 of 5 after a post hoc re-run). Both are exploratory five-episode pilots. A registered five-robot pilot completed no episode in either arm (0 of 10). In two-robot head-on scenes the grounder's feasibility gate, not the model, made the yielder correct (post hoc, decision-level). Classification was scored only after the stall trigger, and blocker kind was not evaluated. In illustrative demonstration takes the model's answers were all valid, but its plan was rarely accepted unchanged and, at the intersection, the only scene where this was checked, changed execution once, reordering two near-equivalent back-outs. Safety evidence is robot-pair centre distance plus an offline contact recompute; one robot-obstacle contact was confirmed. On physical TurtleBot3 robots, in the kept run of each of four staged arrangements the model chose a bounded back-out, completed by all robots but one; earlier attempts in which it chose `priority_override` or `reroute`, which gave only waits or timed-out backups, and two unparsable replies were not kept (illustrative, no navigation goals). The contribution is a way to measure the model's share: audit labels checked against dispatch, re-grounding without the plan, and a scripted default-plan arm. All quantitative results come from simulation, small samples and one VLM in the live comparisons.

#v(0.5em)
#par(first-line-indent: 0pt)[*Keywords:* warehouse robotics, multi-robot systems, congestion management, deadlock recovery, vision-language model, TurtleBot3, ROS 2, Zenoh, ArUco, overhead perception, deterministic grounding.]
#pagebreak()
#outline(title: "Contents", indent: auto)
