#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge

#let pipeline-figure() = {
  let acc = rgb("#e07b00")
  let g1 = luma(90)
  let step(n, name, sub, pos, lbl) = node(
    pos,
    name: lbl,
    inset: 4pt,
    corner-radius: 2pt,
    stroke: 0.7pt + luma(60),
    fill: white,
    width: 24mm,
    align(center, text(size: 8pt)[*#n #name* \ #text(size: 7pt, fill: g1, sub)]),
  )
  let lab(t) = text(size: 6.5pt, fill: g1, t)
  set text(size: 8pt)
  set par(justify: false, first-line-indent: 0pt)
  diagram(
    spacing: (9mm, 14mm),
    edge-stroke: 0.7pt + luma(60),
    mark-scale: 70%,
    label-sep: 3pt,
    node-stroke: none,

    step("1", "Detect", [M1 scene state, M5 stall threshold], (0, 0), <detect>),
    step("2", "Decide", [M2 VLM decision, validated], (1, 0), <decide>),
    step("3", "Ground", [M3 feasibility and command], (2, 0), <ground>),
    step("4", "Act", [M4 dispatch to Nav2], (3, 0), <act>),
    step("5", "Resolve", [M1 observes, M5 closes], (4, 0), <resolve>),

    node((2, 1), name: <refuse>, inset: 4pt, corner-radius: 2pt, stroke: 0.7pt + acc, fill: acc.lighten(92%), width: 24mm, align(center, text(size: 7.5pt)[*M3 yield gate* \ #text(size: 7pt, fill: g1)[yielder cannot reach its park point]])),
    node((3, 1), name: <safety>, inset: 4pt, corner-radius: 2pt, stroke: 0.7pt + acc, fill: acc.lighten(92%), width: 24mm, align(center, text(size: 7.5pt)[*M4 safety monitor* \ #text(size: 7pt, fill: g1)[minimum-distance check]])),
    node((2, 2), name: <none>, inset: 4pt, corner-radius: 2pt, stroke: 0.7pt + luma(60), fill: white, width: 24mm, align(center, text(size: 7.5pt)[*No action* \ #text(size: 7pt, fill: g1)[if configured: nothing dispatched]])),
    node((3, 2), name: <hold>, inset: 4pt, corner-radius: 2pt, stroke: 0.7pt + luma(60), fill: white, width: 24mm, align(center, text(size: 7.5pt)[*Hold* \ #text(size: 7pt, fill: g1)[zero velocity, goal cancelled]])),

    edge(<detect>, <decide>, "-|>"),
    edge(<decide>, <ground>, "-|>"),
    edge(<ground>, <act>, "-|>"),
    edge(<act>, <resolve>, "-|>"),
    edge(<ground>, <refuse>, "-|>", stroke: 0.7pt + acc),
    edge(<refuse>, <act>, "-|>", stroke: 0.7pt + acc, label: lab[swap yielder], label-pos: 0.45, label-side: right),
    edge(<refuse>, <none>, "-|>", stroke: 0.7pt + acc, label: lab[none feasible], label-side: left, label-pos: 0.5),
    edge(<none>, (0, 2), <detect>, "-|>", stroke: (paint: g1, dash: "dashed", thickness: 0.7pt), label: lab[re-analysis on changed scene \ or cooldown expiry], label-side: right, label-pos: 0.78),
    edge(<act>, <safety>, "-|>", stroke: 0.7pt + acc),
    edge(<safety>, <hold>, "-|>", stroke: 0.7pt + acc, label: lab[violation], label-side: left),
  )
}
