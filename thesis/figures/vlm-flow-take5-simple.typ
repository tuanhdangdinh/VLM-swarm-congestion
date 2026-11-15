// Simplified decision flow of intersection demonstration take 5 (request df397030…), for the main text.
// The detailed figure (vlm_flow_take5.typ, next to this file) stays the traceable reference in the appendix.
// Every value is copied from the run bundles or the demo campaign report; SOURCES_simple.md names each source.
//
// Use in the thesis: copy this file to thesis/figures/vlm-flow-take5-simple.typ and write
//   #import "../figures/vlm-flow-take5-simple.typ": vlm-flow-simple-figure
// at the top of the chapter (see INSERT_simple.md). An import takes only the bindings; the standalone preview at
// the bottom of this file is evaluated but not rendered.
// The #figure call must pass `kind: image`: the body contains raw text, so the default kind would be a listing.
// Drawn with Typst built-ins only (grid, block, box); no package needed.

#let vlm-flow-simple-figure() = {
  let acc = rgb("#e07b00")
  let ink = luma(30)
  let g1 = luma(85)
  let monof = "DejaVu Sans Mono"
  let fs = 8.5pt
  let ms = 8pt

  // Only the order comparison carries the accent: tinted fill and a solid 1.2 pt border. Every other block is
  // unfilled with a thin grey border, so the fill alone marks the VLM's contribution, also in greyscale.
  let afill = acc.lighten(70%)
  let astroke = 1.2pt + acc.darken(15%)
  let nstroke = 0.6pt + luma(110)

  let mono(s) = text(font: monof, size: ms, s)
  let r(s) = text(font: monof, size: ms, s)

  let row(n, name, owner, body) = block(
    width: 100%,
    stroke: nstroke,
    radius: 2pt,
    breakable: false,
    above: 0pt,
    below: 0pt,
    grid(
      columns: (30mm, 1fr),
      grid.cell(inset: (x: 5pt, y: 5pt), stroke: (right: 0.4pt + luma(170)), align: left + top)[
        #text(size: 9pt, weight: "bold")[#n #h(2pt) #name] \
        #v(0.5pt)
        #text(size: 8pt, fill: g1, owner)
      ],
      grid.cell(inset: (x: 6pt, y: 5pt), align: left + top, body),
    ),
  )
  let down = block(above: 0pt, below: 0pt, height: 3.4mm, pad(left: 13.5mm, align(horizon, text(size: 10pt, fill: luma(80))[$arrow.b$])))
  let arr = [ #sym.arrow.r ]

  set text(size: fs, fill: ink)
  set par(justify: false, first-line-indent: 0pt, leading: 0.5em, spacing: 0.6em)
  show raw: set text(font: monof, size: ms)

  let legend = block(width: 100%, below: 5pt, grid(
    columns: (auto, auto, auto, auto),
    column-gutter: 5pt,
    align: left + horizon,
    box(width: 8mm, height: 3.6mm, fill: afill, stroke: astroke, radius: 1.5pt),
    [the VLM's contribution to the executed commands #h(10pt)],
    box(width: 8mm, height: 3.6mm, stroke: nstroke, radius: 1.5pt),
    [proposed by the VLM or computed by the system],
  ))

  let b1 = row("1", "VLM proposed", "M2 VLM", [
    Model #r("gemini-robotics-er-2-preview"), key fields of its answer, condensed:
    #v(1pt)
    #mono("strategy: junction_clear") \
    #mono("plan: robot_3 reverse, robot_4 reverse, robot_1 yield, robot_2 cross")
  ])

  let b2 = row("2", "M3 verified", "plan verifier", [
    Plan accepted unchanged, no edits.
    #block(width: 100%, fill: afill, stroke: astroke, radius: 1.5pt, inset: (x: 6pt, y: 5pt), above: 5pt, below: 1pt, grid(
      columns: (auto, 1fr),
      column-gutter: 8pt,
      row-gutter: 5pt,
      [*Back-out order* (model):], [#r("robot_3") #arr #r("robot_4") #h(4pt) (dispatched)],
      [Default order (system):], [#r("robot_4") #arr #r("robot_3")],
      [Recede-cost difference:], [*0.010 m*, within the 0.15 m tolerance: a near-tie],
    ))
  ])

  let b3 = row("3", "Grounding computed", "M3, system", [
    The back-out set (#r("robot_3"), #r("robot_4")) comes from the scene geometry and the yielder #r("robot_1") is M3’s own. Grounding computed the commanded back-out distances (0.781 m, 0.971 m), the waits, and the crossing and release phases.
  ])

  let b4 = row("4", "Dispatched and executed", "M5 to M4, Nav2", [
    #r("robot_3") backed out first (from sim 32.9 s), then #r("robot_4") (from 41.9 s). The crossing and release phases then ran as in the default plan. In this run, all four robots reached their goals between sim 95.1 s and 146.4 s.
  ])

  let note = block(width: 100%, inset: (top: 6pt), text(size: 8pt, fill: g1)[
    Safety monitor (M4) in this run: robot-pair distance only (0.45 m latch, with robots in the same reverse or yield command exempt; 0.20 m hard floor on centre distance). It has no obstacle check, and the escort path was not checked against obstacles.
  ])

  block(width: 100%, align(left, stack(dir: ttb, legend, b1, down, b2, down, b3, down, b4, note)))
}

// Standalone preview: the thesis page setup (thesis/main.typ) and stand-ins for the caption helpers of thesis/lib.typ.
#set page(paper: "a4", margin: (left: 25mm, right: 25mm, top: 22mm, bottom: 25mm))
#set text(font: "New Computer Modern", size: 11pt, lang: "en", region: "us")
#set par(first-line-indent: 1.8em, justify: true)
#show raw: set text(font: "DejaVu Sans Mono", size: 9pt)
#let flex-caption(short, long) = long
#let fig-source(id) = [ Source: \[#id\].]

#figure(
  vlm-flow-simple-figure(),
  kind: image,
  caption: flex-caption([Simplified decision flow of one live intersection take.], [One live run (four-robot intersection, demonstration take 5 of 5, selected because it is the only take labelled VLM-driven execution): what the VLM proposed, what M3 verified, what grounding computed and what was executed. The model's contribution to execution was the back-out order only (filled box), `robot_3` before `robot_4` instead of the default `robot_4` before `robot_3`, and it was a near-tie: the recede costs differ by 0.010 m, within the verifier's 0.15 m tolerance. This is an end-to-end execution example, not controlled evidence of improved performance: the four arrivals do not show that the VLM outperforms the default plan, which resolved the same scene in takes 2 to 4 (take 1 was unresolved). Only robot-pair distance was checked for safety; there was no obstacle verification. The detailed figure in the appendix gives the full trace.#fig-source("NEW-DC")]),
) <fig:ch6-flow-take5-simple>
