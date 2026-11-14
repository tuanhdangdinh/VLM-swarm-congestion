#import "@preview/cetz:0.5.3": canvas, draw

#let s1b-figure() = {
  let acc = rgb("#e07b00")
  let rack = luma(200)
  let ink = luma(60)
  // (id, spawn x, spawn y, yaw rad, goal x, goal y)
  let robots = (
    (1, -0.25, 1.35, -calc.pi / 2, 2.3, 0.0),
    (2, -2.3, 1.35, 0.0, -0.25, 1.35),
    (3, -0.25, -1.35, calc.pi / 2, -2.3, 1.35),
    (4, -2.3, -1.35, 0.0, -0.25, 1.35),
    (5, 2.3, 0.0, calc.pi, -0.25, -1.35),
  )
  // (x, y, robots with this first goal, label anchor, label dx, dy)
  let goals = (
    (2.3, 0.0, "1", "north", 0.0, 0.3),
    (-0.25, 1.35, "2, 4", "west", 0.28, 0.0),
    (-2.3, 1.35, "3", "south", 0.0, -0.3),
    (-0.25, -1.35, "5", "north", 0.0, -0.28),
  )
  let hx = 3.0
  let hy = 2.4
  set text(size: 8pt)
  align(center, canvas(length: 24mm, {
    import draw: *
    rect((-hx, -hy), (hx, hy), stroke: 0.3pt + luma(150), fill: white)
    // rack remnants outside the 5.0 x 3.6 m band; the two aisle stubs stay open; clipped to the drawn window
    for (sx, sy) in ((1, 1), (-1, 1), (1, -1), (-1, -1)) {
      rect((sx * 2.5, sy * 0.6), (sx * hx, sy * hy), fill: rack, stroke: 0.5pt + luma(120))
      rect((sx * 0.6, sy * 1.8), (sx * 2.5, sy * hy), fill: rack, stroke: 0.5pt + luma(120))
    }
    // the two rack islands, 0.55 x 1.60 m
    rect((-1.30, -0.70), (-0.75, 0.90), fill: rack, stroke: 0.5pt + luma(120))
    rect((0.25, -0.90), (0.80, 0.70), fill: rack, stroke: 0.5pt + luma(120))
    rect((-2.5, -1.8), (2.5, 1.8), stroke: (paint: ink, thickness: 0.6pt, dash: "dashed"), fill: none)
    content((0, 1.8), anchor: "south", padding: 2pt, text(size: 7pt, fill: ink)[M1 tracked band, 5.0 × 3.6 m])
    for (gx, gy, who, anc, dx, dy) in goals {
      content((gx + dx, gy + dy), anchor: anc, padding: 1pt, text(size: 6.5pt, fill: ink)[goal #who])
      line((gx - 0.2, gy - 0.2), (gx + 0.2, gy + 0.2), stroke: 1.6pt + acc)
      line((gx - 0.2, gy + 0.2), (gx + 0.2, gy - 0.2), stroke: 1.6pt + acc)
    }
    for (id, x, y, yaw, gx, gy) in robots {
      line((x, y), (x + 0.5 * calc.cos(yaw), y + 0.5 * calc.sin(yaw)), stroke: 1.2pt + acc, mark: (end: "stealth", fill: acc, scale: 0.6))
      circle((x, y), radius: 0.17, fill: acc, stroke: 0.6pt + white)
      content((x, y), text(size: 7.5pt, fill: white, weight: "bold")[#id])
    }
    let by = -hy - 0.35
    line((-hx, by), (-hx + 1, by), stroke: 1.2pt + ink)
    line((-hx, by - 0.06), (-hx, by + 0.06), stroke: 0.8pt + ink)
    line((-hx + 1, by - 0.06), (-hx + 1, by + 0.06), stroke: 0.8pt + ink)
    content((-hx + 1.1, by), anchor: "west", text(size: 7pt, fill: ink)[1 m])
    let lx = hx - 2.9
    circle((lx, by), radius: 0.1, fill: acc, stroke: none)
    content((lx + 0.15, by), anchor: "west", text(size: 7pt, fill: ink)[start and heading])
    line((lx + 1.55, by - 0.1), (lx + 1.75, by + 0.1), stroke: 1.2pt + acc)
    line((lx + 1.55, by + 0.1), (lx + 1.75, by - 0.1), stroke: 1.2pt + acc)
    content((lx + 1.85, by), anchor: "west", text(size: 7pt, fill: ink)[first goal])
    rect((lx + 2.45, by - 0.08), (lx + 2.65, by + 0.08), fill: rack, stroke: 0.5pt + luma(120))
    content((lx + 2.75, by), anchor: "west", text(size: 7pt, fill: ink)[rack])
  }))
}
