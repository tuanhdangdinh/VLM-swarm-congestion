#import "@preview/cetz:0.5.3": canvas, draw

#let ib10-figure() = {
  let acc = rgb("#e07b00")
  let rack = luma(200)
  let ink = luma(60)
  // (id, spawn x, spawn y, yaw rad, goal x, goal y)
  let robots = (
    (1, -1.75, 0.0, 0.0, 1.75, 0.0),
    (2, 1.75, 0.0, calc.pi, -1.75, 0.0),
    (3, 0.0, -1.75, calc.pi / 2, 0.0, 1.75),
    (4, 0.0, 1.75, -calc.pi / 2, 0.0, -1.75),
  )
  let hx = 3.0
  let hy = 2.2
  set text(size: 8pt)
  align(center, canvas(length: 24mm, {
    import draw: *
    rect((-hx, -hy), (hx, hy), stroke: 0.3pt + luma(150), fill: white)
    // rack blocks fill the four quadrants outside the 1.2 m cross aisle; clipped to the drawn window
    for (sx, sy) in ((1, 1), (-1, 1), (1, -1), (-1, -1)) {
      rect((sx * 0.6, sy * 0.6), (sx * hx, sy * hy), fill: rack, stroke: 0.5pt + luma(120))
    }
    rect((-2.5, -1.8), (2.5, 1.8), stroke: (paint: ink, thickness: 0.6pt, dash: "dashed"), fill: none)
    content((-2.45, -1.75), anchor: "south-west", text(size: 7pt, fill: ink)[M1 tracked band])
    content((2.0, -0.38), text(size: 7pt, fill: ink)[1.2 m aisle])
    for (id, x, y, yaw, gx, gy) in robots {
      line((x, y), (gx, gy), stroke: (paint: acc, thickness: 0.6pt, dash: "dotted"))
    }
    for (id, x, y, yaw, gx, gy) in robots {
      line((gx - 0.28, gy - 0.28), (gx + 0.28, gy + 0.28), stroke: 1.6pt + acc)
      line((gx - 0.28, gy + 0.28), (gx + 0.28, gy - 0.28), stroke: 1.6pt + acc)
    }
    for (id, x, y, yaw, gx, gy) in robots {
      line((x, y), (x + 0.5 * calc.cos(yaw), y + 0.5 * calc.sin(yaw)), stroke: 1.2pt + acc, mark: (end: "stealth", fill: acc, scale: 0.6))
      circle((x, y), radius: 0.17, fill: acc, stroke: 0.6pt + white)
      content((x, y), text(size: 7.5pt, fill: white, weight: "bold")[#id])
    }
    // scale bar
    let by = -hy - 0.35
    line((-hx, by), (-hx + 1, by), stroke: 1.2pt + ink)
    line((-hx, by - 0.06), (-hx, by + 0.06), stroke: 0.8pt + ink)
    line((-hx + 1, by - 0.06), (-hx + 1, by + 0.06), stroke: 0.8pt + ink)
    content((-hx + 1.1, by), anchor: "west", text(size: 7pt, fill: ink)[1 m])
    // legend
    let lx = hx - 2.9
    circle((lx, by), radius: 0.1, fill: acc, stroke: none)
    content((lx + 0.15, by), anchor: "west", text(size: 7pt, fill: ink)[start and heading])
    line((lx + 1.55, by - 0.1), (lx + 1.75, by + 0.1), stroke: 1.2pt + acc)
    line((lx + 1.55, by + 0.1), (lx + 1.75, by - 0.1), stroke: 1.2pt + acc)
    content((lx + 1.85, by), anchor: "west", text(size: 7pt, fill: ink)[goal])
    rect((lx + 2.4, by - 0.08), (lx + 2.6, by + 0.08), fill: rack, stroke: 0.5pt + luma(120))
    content((lx + 2.7, by), anchor: "west", text(size: 7pt, fill: ink)[rack block])
  }))
}
