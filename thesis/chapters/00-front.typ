#import "../lib.typ": *

#heading(numbering: none, outlined: false)[Declaration of Authorship]
#todo[Declaration of authorship text, to be provided by the owner.]

#pagebreak()
#heading(numbering: none, outlined: false)[Acknowledgements]
#todo[Acknowledgements, to be written by the owner.]

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
  [M1--M6], [Modules 1 to 6 of the system],
  [VLM], [Vision-Language Model],
  [RAG], [Retrieval-Augmented Generation],
  [MAPF], [Multi-Agent Path Finding],
  [CBS], [Conflict-Based Search],
  [ORCA], [Optimal Reciprocal Collision Avoidance],
  [ROS 2], [Robot Operating System 2],
  [Nav2], [ROS 2 Navigation stack],
  [ArUco], [Square fiducial marker system],
  [GT], [Ground truth],
)
#todo[Extend the abbreviation list once chapters 1 to 5 are final.]
