// Decision flow of intersection demonstration take 5 (request df397030…), annotated with the run's real output,
// plus a contrast strip with the head-on take (decision 2, request f40c0537…).
// Every value is copied from the run bundles; SOURCES.md (next to this file) names the file and field for each.
//
// Use in the thesis: copy this file to thesis/figures/vlm-flow-take5.typ and write
//   #import "../figures/vlm-flow-take5.typ": vlm-flow-figure
// at the top of the chapter (see INSERT.md). An import takes only the bindings; the standalone preview at the
// bottom of this file (page setup, stand-in caption helpers, the figure) is evaluated but not rendered.
// The #figure call must pass `kind: image`: the body contains raw text, so the default kind would be a listing.
// Drawn with Typst built-ins only (grid, block, box, table, rotate); no package needed.

#let vlm-flow-figure() = {
  let acc = rgb("#e07b00")
  let ink = luma(40)
  let g1 = luma(90)
  let unused = luma(120)
  let monof = "DejaVu Sans Mono"
  let fs = 7.5pt
  let ms = 7pt

  // Model class: tinted fill and a solid 1.2 pt border. System class: no fill and a dashed border.
  // The two stay distinct in greyscale through fill and border style, not only through colour.
  let mfill = acc.lighten(72%)
  let mstroke = 1.2pt + acc.darken(15%)
  let sstroke = (paint: luma(70), thickness: 0.6pt, dash: "dashed")

  let mono(s, size: ms, fill: ink) = text(font: monof, size: size, fill: fill, s)
  let mdl(body) = box(fill: mfill, stroke: mstroke, inset: (x: 2pt, y: 0pt), outset: (top: 2pt, bottom: 3.2pt), radius: 1.5pt, body)
  let sys(body) = box(stroke: sstroke, inset: (x: 2pt, y: 0pt), outset: (top: 2pt, bottom: 3.2pt), radius: 1.5pt, body)
  let mdl-block(body) = block(width: 100%, fill: mfill, stroke: mstroke, inset: (x: 3pt, y: 2.5pt), radius: 1.5pt, above: 2pt, below: 2pt, body)
  let sys-block(body) = block(width: 100%, stroke: sstroke, inset: (x: 3pt, y: 2.5pt), radius: 1.5pt, above: 3pt, below: 3pt, body)
  // One monospace line, indented by `ind` levels, with a hanging indent if it wraps.
  let jl(ind, s, fill: ink) = block(above: 2.6pt, below: 2.6pt, inset: (left: ind * 8pt), par(hanging-indent: 8pt, mono(s, fill: fill)))
  let logline(s) = block(width: 100%, fill: luma(246), stroke: 0.4pt + luma(170), inset: (x: 3pt, y: 2.5pt), radius: 1pt, above: 3pt, below: 3pt, par(hanging-indent: 8pt, mono(s)))
  let note(body) = text(size: 7pt, fill: g1, body)

  let stage(n, name, owner, body) = block(
    width: 100%,
    stroke: 0.6pt + luma(60),
    radius: 2pt,
    clip: true,
    breakable: false,
    above: 0pt,
    below: 0pt,
    grid(
      columns: (22mm, 1fr),
      grid.cell(fill: luma(235), inset: (x: 3pt, y: 3.5pt), align: left + top)[
        #text(size: 8pt, weight: "bold")[#n #h(1pt) #name] \
        #text(size: 7pt, fill: g1, owner)
      ],
      grid.cell(inset: (x: 4pt, y: 3.5pt), body),
    ),
  )
  let down = block(above: 0pt, below: 0pt, height: 2mm, pad(left: 8mm, align(horizon, text(size: 8pt, fill: luma(60))[$arrow.b$])))

  set text(size: fs, fill: ink)
  set par(justify: false, first-line-indent: 0pt, leading: 0.42em, spacing: 0.5em)
  show raw: set text(font: monof, size: ms)

  let legend = block(width: 100%, below: 4pt, grid(
    columns: (auto, auto, auto, auto, auto, auto),
    column-gutter: 4pt,
    align: left + horizon,
    box(width: 7mm, height: 3.2mm, fill: mfill, stroke: mstroke, radius: 1.5pt),
    [decided by the *model* (ER-2) #h(8pt)],
    box(width: 7mm, height: 3.2mm, stroke: sstroke, radius: 1.5pt),
    [decided by the *system* (M3, M5, M4) #h(8pt)],
    box(height: 3.2mm, align(center + horizon, mono("\"…\"", fill: unused))),
    text(fill: unused)[model output, not used],
  ))

  let s1 = stage("1", "Trigger", "M5 orchestrator", [
    #logline("starting analysis request=df397030… robots=['robot_3'] reason=1 robot(s) stalled >= 12.0s order=id_asc …")
    #v(1pt)
    #sys[stall threshold 12.0 s] #h(3pt) scene snapshot at sim 30.33 s; robots listed in ascending id order
  ])

  let s2 = stage("2", "Request", "M2 prompt", [
    Annotated overhead camera frame + prompt version 3 (user prompt 7,363 characters) with robot states, pairwise geometry and, per robot, the actions the verifier accepts:
    #sys-block[
      #jl(0, "Plan actions the system's verifier accepts for each robot … (…):")
      #jl(0, "- robot_1: yield, cross, wait, reroute")
      #jl(0, "- robot_2: yield, cross, wait, reroute")
      #jl(0, "- robot_3: yield, reverse (south arm), cross, wait, reroute")
      #jl(0, "- robot_4: yield, reverse (north arm), cross, wait, reroute")
      #note[Only `robot_3` and `robot_4` are offered `reverse`: the geometry fixes the recede set.]
    ]
  ])

  let s3 = stage("3", "Response", "M2 VLM", [
    `gemini-robotics-er-2-preview`, latency 7,728 ms, 1 attempt. Raw text, trimmed:
    #block(width: 100%, stroke: 0.4pt + luma(170), fill: luma(250), inset: (x: 3pt, y: 2pt), radius: 1pt, above: 3pt, below: 0pt)[
      #jl(0, "{ … \"type\": \"deadlock\", …")
      #block(above: 4pt, below: 4.5pt, inset: (left: 8pt), mdl(mono("\"strategy\": \"junction_clear\",")))
      #jl(1, "\"justification\": \"A junction clear strategy is required to have robots 3 and 4 back out of the intersection, allowing robot 2 to cross while robot 1 yields.\",")
      #jl(1, "\"yield_robot\": null, …")
      #block(above: 2.6pt, below: 2.6pt, inset: (left: 8pt), [#mono("\"crossing_order\": [\"robot_2\", \"robot_1\", \"robot_3\", \"robot_4\"],", fill: unused) #h(3pt) #text(size: 7pt, fill: unused, style: "italic")[← not used by the system]])
      #block(above: 2pt, below: 2pt, inset: (left: 6pt), mdl-block(grid(
        columns: (auto, 1fr),
        column-gutter: 4pt,
        row-gutter: 2.6pt,
        mono("\"proposed_plan\": ["), mono("{\"robot_id\": \"robot_3\", \"action\": \"reverse\"},"),
        [], mono("{\"robot_id\": \"robot_4\", \"action\": \"reverse\"},"),
        [], mono("{\"robot_id\": \"robot_1\", \"action\": \"yield\"},"),
        [], mono("{\"robot_id\": \"robot_2\", \"action\": \"cross\"} ]"),
      )))
      #jl(0, "}")
    ]
  ])

  let s4 = stage("4", "Check", "M2 parser, M3 plan verifier", [
    `parse_status=valid`. Verifier: `provenance=vlm_verbatim`, `edits=[]`, `rejection_reason=null`, `order_equivalent=true` #sym.arrow.r `dispatch_order_source=model`.
    #v(2pt)
    #mdl[back-out order `robot_3` #sym.arrow.r `robot_4` accepted]
    #v(3.5pt)
    #sys[default order `robot_4` #sym.arrow.r `robot_3`, computed offline]
    #v(3.5pt)
    #sys[margin 0.010 m < tolerance 0.15 m: near-tie]
  ])

  let ph(n, name) = [*#n* #name]
  let s5 = stage("5", "Grounding", "M3 phase queue", [
    #sys-block[
      #table(
        columns: (14mm, 1fr),
        stroke: none,
        inset: (x: 2pt, y: 2.8pt),
        align: left + horizon,
        table.hline(stroke: 0.4pt + luma(150)),
        text(fill: g1)[phase], text(fill: g1)[commanded moves],
        table.hline(stroke: 0.4pt + luma(150)),
        ph("1", "recede"), [#mdl[`robot_3`] `reverse` 0.781 m],
        ph("2", "recede"), [#mdl[`robot_4`] `reverse` 0.971 m],
        ph("3", "cross"), [`robot_1` `yield` (back 0.789 m, pull-off −0.36 m, hold 45 s); `robot_2` passes, escorted 2.024 m],
        ph("4", "release"), [`robot_3` `yield` for passer `robot_4`; `robot_1` `yield`, crossing chain `robot_4` #sym.arrow.r `robot_3`],
        table.hline(stroke: 0.4pt + luma(150)),
      )
    ]
    #note[Phases run in sequence; in phases 1–3 robots without a move hold a `temporary_wait` of 120 s. The model's order sets only which recede runs first (filled); the yielder `robot_1` is M3’s and matches the plan's `yield` leg.]
  ])

  let s6 = stage("6", "Dispatch, execution", "M5 to M4, Nav2", [
    First command executed (M4 command bus):
    #logline("command received command=df397030…-junction-recede-robot_3 robot=robot_3 action=reverse")
    Ground truth: `robot_3` backs out from sim 32.9 s, `robot_4` from 41.9 s. Arrivals: `robot_2` 95.1 s, `robot_4` 115.3 s, `robot_3` 131.9 s, `robot_1` 146.4 s #note[(not the model's `crossing_order`)].
  ])

  // Side rail: the safety monitor runs beside every stage. Rotated so it spans the stack in a narrow column.
  let rail-text = [
    #set par(leading: 0.5em, spacing: 0.5em)
    #text(size: 8.5pt, weight: "bold")[M4 safety monitor] #h(4pt) #note[beside every stage; reads M1’s scene state and the command topics, not M2 or M3] \
    *0.45 m latch:* a pair closer than 0.45 m, centre to centre, is held. #h(4pt)
    *Exempt pairs:* during `reverse` and `yield`, the robot and its partners in the same command are exempt from the latch (scoped exemption on in this run). #h(4pt)
    *0.20 m hard floor* on centre distance, exempt pairs included. #h(4pt)
    *This take:* 0 floor stops; closest pair 0.329 m (`robot_1`–`robot_4`, sim 27.9 s), before any command.
  ]
  let rail = grid.cell(rowspan: 11, stroke: sstroke, inset: (x: 2pt, y: 4pt), align: center + horizon,
    rotate(-90deg, reflow: true, block(width: 162mm, rail-text)))

  let main = grid(
    columns: (1fr, 16mm),
    column-gutter: 2mm,
    s1, rail,
    down, s2, down, s3, down, s4, down, s5, down, s6,
  )

  let strip = block(width: 100%, stroke: 0.6pt + luma(60), radius: 2pt, clip: true, breakable: false, grid(
    columns: (1fr, 1.55fr),
    grid.cell(colspan: 2, fill: luma(235), inset: (x: 4pt, y: 2.5pt))[*Stage 4, two possible outcomes* #h(4pt) #note[(left: plan verifier; right: a different take, yield feasibility gate, off for the take 5 request)]],
    grid.cell(inset: 4pt, stroke: (right: 0.4pt + luma(150)))[
      *Accepted unchanged* #h(2pt) #note[intersection, take 5]
      #v(1.5pt)
      #mdl[plan `robot_3 reverse`, `robot_4 reverse`, `robot_1 yield`, `robot_2 cross`]
      #v(2.5pt)
      `provenance=vlm_verbatim`, `edits=[]`: the model's back-out order was dispatched.
    ],
    grid.cell(inset: 4pt)[
      *Corrected* #h(2pt) #note[head-on corridor with obstacle, take 1, decision 2]
      #v(1pt)
      #mdl[model chose `yield_robot` `robot_1`] #sym.arrow.r
      #v(3.5pt)
      #sys[gate swapped to `robot_2` (0.70 m < 1.08 m required)]
      #logline("yield re-grounded request=f40c0537… from=robot_1 to=robot_2 reason=yield re-grounded: robot_1 has 0.70 m retreat room < 1.08 m required; robot_2 feasible")
      Dispatched `yield` to `robot_2`, `temporary_wait` to `robot_1`; both reached their goals (ground truth: `robot_1` 112.5 s, `robot_2` 136.1 s).
    ],
  ))

  block(width: 100%, align(left, stack(dir: ttb, legend, main, v(3mm), strip)))
}

// Standalone preview: the thesis page setup (thesis/main.typ) and stand-ins for the caption helpers of thesis/lib.typ.
#set page(paper: "a4", margin: (left: 25mm, right: 25mm, top: 22mm, bottom: 25mm))
#set text(font: "New Computer Modern", size: 11pt, lang: "en", region: "us")
#set par(first-line-indent: 1.8em, justify: true)
#show raw: set text(font: "DejaVu Sans Mono", size: 9pt)
#let flex-caption(short, long) = long
#let fig-source(id) = [ Source: \[#id\].]

#figure(
  vlm-flow-figure(),
  kind: image,
  caption: flex-caption([Decision flow of one live take, annotated with its real output.], [Decision flow of one live run, annotated with its real output (four-robot intersection, demonstration take 5); text is copied from the run and trimmed (…). Illustrative, not controlled evidence: take 5 of 5, selected because it is the only take labelled VLM-driven execution. Only the back-out order was the model's, and it was a near-tie: it differed from the default order by 0.010 m in recede cost, within the verifier's 0.15 m tolerance. The bottom strip is from a different take (head-on corridor with an obstacle, decision 2, n = 1), in which the feasibility gate replaced the model's yielder.#fig-source("NEW-DC")]),
) <fig:ch6-flow-take5>
