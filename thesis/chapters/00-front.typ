#import "../lib.typ": *

#heading(numbering: none, outlined: false)[Declaration of Authorship]
#todo[Declaration of authorship text, to be provided by the owner.]

#pagebreak()
#[
  #set par(first-line-indent: 0pt)

  #align(center)[
    #heading(numbering: none, outlined: false)[Acknowledgements]
  ]

  #v(1.2cm)

  We would like to express our sincere gratitude to our supervisor, *Dr. Vo Bich Hien*, for his valuable guidance, constructive feedback, and continuous support throughout this project. His expertise and direction greatly helped us shape the research approach and improve the quality of this report.

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
#todo[Abstract: problem, approach, evaluation, outcome. Held until results are final.]

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
  [A$n$], [Numbered amendment (prereg-v1) or addendum (prereg-v3), e.g. A33],
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
  [IB10], [Name of the four-robot intersection scene (Chapter 5)],
  [JSON], [JavaScript Object Notation],
  [LLM], [Large Language Model],
  [M1--M6], [Modules 1 to 6 of the system],
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
  [S1b], [Name of the five-robot task-stream scene (Chapter 5)],
  [SHA-256], [Secure Hash Algorithm with a 256-bit digest],
  [UDP], [User Datagram Protocol],
  [USD], [Universal Scene Description],
  [VLM], [Vision-Language Model],
)
