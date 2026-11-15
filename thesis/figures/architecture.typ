#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge

#let architecture-figure() = {
  let acc = rgb("#e07b00")
  let g1 = luma(90)
  let g2 = luma(235)
  let mod(code, name, ..a) = node(
    ..a,
    inset: 4pt,
    corner-radius: 2pt,
    stroke: 0.7pt + luma(60),
    fill: white,
    width: 25mm,
    align(center, text(size: 8pt)[*#code* \ #name]),
  )
  let lab(t) = text(size: 6.5pt, fill: g1, t)
  set text(size: 8pt)
  set par(justify: false, first-line-indent: 0pt)
  diagram(
    spacing: (17mm, 14mm),
    edge-stroke: 0.7pt + luma(60),
    mark-scale: 70%,
    label-sep: 4pt,
    node-stroke: none,

    node((2.5, 0.5), name: <l2>, box(width: 0pt, height: 8pt, place(center + horizon, box(width: 70mm, text(size: 7.5pt, fill: acc, weight: "bold")[Coordination layer (Layer 2), 0.5–2 Hz])))),
    node(enclose: (<m1>, <m5>, <m2>, <m3>, <l2>), inset: 8pt, stroke: 1pt + acc, fill: acc.lighten(94%), corner-radius: 3pt, snap: -1),
    node((1.2, 2.6), name: <l1>, box(width: 0pt, height: 16pt, place(center + horizon, box(width: 40mm, text(size: 7.5pt, weight: "bold")[Local navigation (Layer 1), \ 20–50 Hz])))),
    node(enclose: (<m4>, <nav>, <l1>), inset: 8pt, stroke: 1pt + luma(60), fill: g2, corner-radius: 3pt, snap: -1),

    mod("M1", [Perception], (0, 0), name: <m1>),
    mod("M5", [Orchestrator], (1, 0), name: <m5>),
    mod("M2", [VLM reasoning], (2, 0), name: <m2>),
    mod("M3", [Grounder], (3, 0), name: <m3>),
    mod("M4", [Execution and safety], (1, 2), name: <m4>),
    mod("Nav2", [per-robot navigation], (2, 2), name: <nav>),
    node((2, 3.9), name: <m6>, inset: 4pt, corner-radius: 2pt, stroke: (paint: luma(60), thickness: 0.7pt, dash: "dashed"), fill: white, width: 25mm, align(center, text(size: 8pt)[*M6* \ Isaac Sim: robots and overhead camera])),

    edge(<m1>, <m5>, "-|>", label: lab[/perception/ \ scene_state], label-side: right),
    edge(<m5>, <m2>, "-|>", label: lab[scene, image], label-side: left),
    edge(<m2>, <m3>, "-|>", label: lab[decision], label-side: left),
    edge(<m3>, (3, -0.7), (1, -0.7), <m5>, "-|>", label: lab[grounded command], label-pos: 0.5, label-side: left),
    edge(<m5>, <m4>, "-|>", shift: -7pt, label: lab[/coordination/ \ commands], label-side: right, label-pos: 0.5),
    edge(<m4>, <m5>, "-|>", shift: -7pt, label: lab[/coordination/ \ status], label-side: right, label-pos: 0.5),
    edge(<m4>, <nav>, "-|>", label: lab[goals], label-side: left),
    edge(<nav>, <m6>, "-|>", shift: -6pt, label: lab[/robot_N/ \ cmd_vel], label-side: right, label-pos: 0.8),
    edge(<m6>, <nav>, "-|>", shift: -6pt, label: lab[/robot_N/odom, \ /robot_N/scan], label-side: right, label-pos: 0.2),
    edge(<m6>, (0, 3.9), <m1>, "-|>", label: lab[/camera/image_raw], label-pos: 0.62, label-side: right),
  )
}
