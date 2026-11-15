#import "lib.typ": *

#show link: set text(fill: rgb("#0000FF"))
#show cite: set text(fill: blue)

#set page(
  paper: "a4",
  numbering: "i",
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
  #set text(size: 12pt)
  VIETNAMESE - GERMAN UNIVERSITY \
  DEPARTMENT OF COMPUTER SCIENCE

  #v(1cm)
  #image("assets/images/vgu_logo.png", width: 3cm)
  #v(2cm)

  #text(size: 13pt, weight: "bold")[Project Report]
  #v(1cm)
  #text(size: 15pt, weight: "bold")[Leveraging Vision-Language Models (VLM) for Congestion Management in Warehouse Swarm Robotics]
  #v(1cm)
  #text(size: 12pt)[Instructor: Dr. Vo Bich Hien]

  #v(2.5cm)
  #grid(
    columns: (auto, auto),
    column-gutter: 10pt,
    row-gutter: 8pt,
    align: left,
    [_Students:_], [Dang Dinh Tu Anh - 10422086],
    [], [Nguyen Khanh Tuong - 10422121],
  )

  #v(1fr)
  #text(size: 8pt)[HO CHI MINH CITY, 11/2026]
]

#pagebreak()

#include "short/s00-front.typ"

#set heading(numbering: "1.1")
#pagebreak()
#set page(numbering: "1")
#counter(page).update(1)

#include "short/s01-introduction.typ"
#include "short/s02-background.typ"
#include "short/s03-system-design.typ"
#include "short/s04-implementation.typ"
#include "short/s05-methodology.typ"
#include "short/s06-results.typ"
#include "short/s07-discussion-conclusion.typ"

// Template APA style with name disambiguation off: Typst 0.15 drops author lists when it disambiguates by name; year suffixes (2023a/b) are used instead.
#bibliography("bibliography/refs.bib", style: "bibliography/apa.csl", title: "References")

#set heading(numbering: "A.1")
#counter(heading).update(0)
#include "short/s08-sources.typ"
