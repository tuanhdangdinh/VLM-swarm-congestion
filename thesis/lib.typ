// Shared macros for the thesis. Every chapter starts with #import "../lib.typ": *
//
// Diagram package versions (Typst Universe, looked up 2026-11-14; import them in diagram files, not here):
//   fletcher 0.5.8  https://typst.app/universe/package/fletcher  (needs Typst >= 0.13.0)
//   cetz     0.5.3  https://typst.app/universe/package/cetz      (needs Typst >= 0.15.0)
//
// Evidence appendix design: the "table" is a grid of 3 columns (ID, claim, source). #evidence-header
// emits the header row; each #evidence(id, claim, source) emits one grid row labelled <ev:id>, so an
// empty chN.typ contributes nothing and still compiles. (A real table cannot be assembled across
// #include boundaries, which return content, not cells.)
//
// API (positional arguments):
//   #todo[body]                  orange-bordered TODO box, works in block and inline position
//   #ev("3.04")                  renders [3.04] as a link to <ev:3.04>
//   #evidence("3.04", [claim], [source])   one appendix row, used only in evidence/chN.typ
//   #fig-source("3.04")          caption suffix " Source: [3.04]." (hidden in outlines)
//   #flex-caption([short], [long]) short caption in the List of Figures/Tables, long one under the figure

#let accent = rgb("#e07b00")

#let todo(body) = box(
  stroke: 1pt + accent,
  inset: (x: 4pt, y: 3pt),
  radius: 2pt,
  fill: accent.lighten(92%),
)[#text(weight: "bold", fill: accent, size: 0.85em)[TODO] #body]

// True while an outline (contents, figure or table list) is being laid out; set by a show rule in main.typ.
#let in-outline = state("in-outline", false)

// Caption with a short form for the List of Figures/Tables and the full form under the figure.
#let flex-caption(short, long) = context if in-outline.get() { short } else { long }

// Evidence tags stay in the source (every number keeps its Evidence Index id, checked by check.sh) but are not printed;
// set show-evidence-tags to true to print them again. A hidden tag is a weak space, so it also swallows the space before it.
#let show-evidence-tags = false
#let ev(id) = context if in-outline.get() { none } else if not show-evidence-tags { h(0pt, weak: true) } else {
  let l = label("ev:" + id)
  if query(l).len() > 0 { link(l)[\[#id\]] } else [\[#id\]]
}

#let ev-cols = (14mm, 1fr, 1fr)

#let evidence-header = grid(
  columns: ev-cols,
  column-gutter: 6pt,
  inset: (y: 4pt),
  stroke: (bottom: 0.8pt),
  [*ID*], [*Claim*], [*Source*],
)

#let evidence(id, claim, source) = [#block(breakable: true, width: 100%, above: 0pt, below: 0pt)[#set par(justify: false, first-line-indent: 0pt)
#set block(spacing: 0pt)
#grid(
  columns: ev-cols,
  column-gutter: 6pt,
  inset: (y: 4pt),
  align: left,
  [#id], claim, text(font: "DejaVu Sans Mono", size: 8pt)[#source],
)#line(length: 100%, stroke: 0.3pt + luma(180))]#label("ev:" + id)]

#let fig-source(id) = context if in-outline.get() or not show-evidence-tags { none } else [ Source: #ev(id).]
