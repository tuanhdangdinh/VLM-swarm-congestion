#import "@preview/cetz:0.5.3": canvas, draw

#let ib10-figure() = {
  let acc = rgb("#e07b00")
  let rack = luma(200)
  let ink = luma(60)
  // (x, y, start yaw or none, start label, goal label, start-label side, goal-label side)
  let pts = (
    (-1.75, 0.0, 0.0, "R1", "G2", "n", "s"),
    (1.75, 0.0, calc.pi, "R2", "G1", "n", "s"),
    (0.0, -1.75, calc.pi / 2, "R3", "G4", "w", "e"),
    (0.0, 1.75, -calc.pi / 2, "R4", "G3", "w", "e"),
  )
  let hx = 3.0
  let hy = 2.2
  set text(size: 8pt)
  align(center, canvas(length: 24mm, {
    import draw: *
    rect((-hx, -hy), (hx, hy), stroke: 0.3pt + luma(150), fill: white)
    for (sx, sy) in ((1, 1), (-1, 1), (1, -1), (-1, -1)) {
      rect((sx * 0.6, sy * 0.6), (sx * hx, sy * hy), fill: rack, stroke: 0.5pt + luma(120))
    }
    rect((-2.5, -1.8), (2.5, 1.8), stroke: (paint: ink, thickness: 0.6pt, dash: "dashed"), fill: none)
    // dimension of the cross aisle (nominal_aisle_width_m = 1.2)
    line((2.9, -0.6), (2.9, 0.6), stroke: 0.6pt + ink, mark: (start: "stealth", end: "stealth", fill: ink, scale: 0.4))
    content((2.82, 0), anchor: "east", text(size: 7pt, fill: ink)[1.2 m])
    // start-to-goal pairs: R1 to G1, R2 to G2 along the E-W lane, R3 to G3, R4 to G4 along the N-S lane
    line((-1.75, 0.07), (1.75, 0.07), stroke: (paint: acc, thickness: 0.6pt, dash: "dotted"), mark: (end: "stealth", fill: acc, scale: 0.4))
    line((1.75, -0.07), (-1.75, -0.07), stroke: (paint: acc, thickness: 0.6pt, dash: "dotted"), mark: (end: "stealth", fill: acc, scale: 0.4))
    line((-0.07, -1.75), (-0.07, 1.75), stroke: (paint: acc, thickness: 0.6pt, dash: "dotted"), mark: (end: "stealth", fill: acc, scale: 0.4))
    line((0.07, 1.75), (0.07, -1.75), stroke: (paint: acc, thickness: 0.6pt, dash: "dotted"), mark: (end: "stealth", fill: acc, scale: 0.4))
    for (x, y, yaw, rl, gl, rs, gs) in pts {
      if gl != none {
        line((x - 0.14, y - 0.14), (x + 0.14, y + 0.14), stroke: 1.2pt + acc)
        line((x - 0.14, y + 0.14), (x + 0.14, y - 0.14), stroke: 1.2pt + acc)
      }
    }
    for (x, y, yaw, rl, gl, rs, gs) in pts {
      if yaw != none {
        line((x, y), (x + 0.45 * calc.cos(yaw), y + 0.45 * calc.sin(yaw)), stroke: 1pt + acc, mark: (end: "stealth", fill: acc, scale: 0.5))
        circle((x, y), radius: 0.09, fill: acc, stroke: 0.4pt + white)
      }
      let off(side) = if side == "n" { ((x, y + 0.2), "south") } else if side == "s" { ((x, y - 0.2), "north") } else if side == "w" { ((x - 0.2, y), "east") } else { ((x + 0.2, y), "west") }
      if rl != none {
        let (p, a) = off(rs)
        content(p, anchor: a, text(size: 7pt, fill: ink, weight: "bold")[#rl])
      }
      if gl != none {
        let (p, a) = off(gs)
        content(p, anchor: a, text(size: 7pt, fill: acc.darken(15%), weight: "bold")[#gl])
      }
    }
    let by = -hy - 0.35
    line((-hx, by), (-hx + 1, by), stroke: 1.2pt + ink)
    line((-hx, by - 0.06), (-hx, by + 0.06), stroke: 0.8pt + ink)
    line((-hx + 1, by - 0.06), (-hx + 1, by + 0.06), stroke: 0.8pt + ink)
    content((-hx + 1.1, by), anchor: "west", text(size: 7pt, fill: ink)[1 m])
    let lx = -hx + 1.7
    circle((lx, by), radius: 0.09, fill: acc, stroke: none)
    content((lx + 0.15, by), anchor: "west", text(size: 7pt, fill: ink)[start Rn])
    line((lx + 1.0, by - 0.1), (lx + 1.2, by + 0.1), stroke: 1.2pt + acc)
    line((lx + 1.0, by + 0.1), (lx + 1.2, by - 0.1), stroke: 1.2pt + acc)
    content((lx + 1.3, by), anchor: "west", text(size: 7pt, fill: ink)[goal Gn])
    rect((lx + 2.3, by - 0.07), (lx + 2.5, by + 0.07), fill: rack, stroke: 0.5pt + luma(120))
    content((lx + 2.6, by), anchor: "west", text(size: 7pt, fill: ink)[rack])
    line((lx + 3.3, by), (lx + 3.6, by), stroke: (paint: ink, thickness: 0.6pt, dash: "dashed"))
    content((lx + 3.7, by), anchor: "west", text(size: 7pt, fill: ink)[M1 band])
  }))
}
