#import "lib.typ": *

#show link: set text(fill: rgb("#0000FF"))
#show cite: set text(fill: blue)

#set page(
  paper: "a4",
  numbering: "1",
  margin: (left: 25mm, right: 25mm, top: 22mm, bottom: 25mm),
  header: context {
    if here().page() > 1 {
      block(width: 100%)[
        #grid(
          columns: (auto, 1fr),
          align: (bottom + left, bottom + left),
          gutter: 12pt,
          image("assets/images/vgu_logo.png", width: 10mm),
          [
            #set text(font: "DejaVu Sans Mono", weight: "bold", size: 9pt)
            Vietnamese-German University \
            Department of Computer Science
          ],
        )
        #v(-4pt)
        #line(length: 100%, stroke: 0.4pt)
      ]
    }
  },
  footer: context {
    if here().page() > 1 {
      block(width: 100%)[
        #set text(size: 8pt, font: "DejaVu Sans Mono")
        #line(length: 100%, stroke: 0.4pt)
        #v(2pt)
        #h(1fr) Page #counter(page).display(here().page-numbering())
      ]
    }
  },
)
#set math.equation(numbering: "(1)")
#show math.equation.where(block: true): set text(size: 1.3em)

#set text(font: "New Computer Modern", size: 11pt, lang: "en", region: "us")
#set par(first-line-indent: 1.8em, justify: true)
#set list(indent: 1.5em, body-indent: 1em)
#set terms(indent: 1.5em, hanging-indent: 1em)
#show heading.where(level: 1): set text(size: 14.4pt, weight: "bold")
#show heading.where(level: 1): it => { pagebreak(weak: true); it }
#show heading: set block(above: 1.5em, below: 1em)
#show table: set par(justify: false)
#show figure.where(kind: table): set figure.caption(position: top)
#show figure.where(kind: raw): set block(breakable: true)
#show outline: it => { in-outline.update(true); it; in-outline.update(false) }

#show raw: set text(font: "DejaVu Sans Mono", size: 9pt)
#show raw.where(block: true): it => block(
  width: 100%,
  stroke: 0.5pt,
  inset: 10pt,
  radius: 2pt,
  fill: luma(250),
  it,
)

#align(center)[
  #text(size: 15pt, weight: "bold")[Supplementary Evidence Index]
  #v(4pt)
  #text(size: 11pt)[to the project report "Leveraging Vision-Language Models (VLM) for Congestion Management in Warehouse Swarm Robotics"]
  #v(4pt)
  #text(size: 10pt)[Dang Dinh Tu Anh, Nguyen Khanh Tuong · Vietnamese-German University · 11/2026]
]

#v(1em)

This supplement belongs to the project report above. Every bracketed tag in the report, such as [6.02], is the identifier of a row in the Evidence Index below, which names the claim and the file, commit and section that support it. The supplementary tables hold detail moved out of the report's appendices.

#set heading(numbering: "S.1")
#set figure(numbering: "S.1")
#include "chapters/supp-evidence.typ"
#include "chapters/supp-tables.typ"
