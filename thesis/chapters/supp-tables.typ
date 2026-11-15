#import "../lib.typ": *

= Detail Tables <sec:supp-tables>

== Safety-Exemption Key <sec:supp-sx>

@tab:res-sx lists what the scoped safety-exemption key changes in the coordination exemption (report, Safety Findings).

#figure(
  table(
    columns: (1.4fr, 1.2fr, 1.4fr),
    align: left,
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([*Exemption path*], [*Key off (evaluated runtime)*], [*Key on*]),
    [Robots the plan marks `continue`], [exempt, also in other clusters], [not honoured],
    [A leg rejected before it started], [still a member, still exempt], [not a partner],
    [Bystander waiver at command start], [unhonoured partner counts as own], [both count as third robots; the waiver ends once the gap closes by more than 0.05 m on 3 readings],
    [Mutual waivers, own-command scope], [unchanged], [unchanged],
  ),
  caption: flex-caption([What the safety-exemption key changes.], [The execution and safety monitor's (M4) coordination exemption with the scoped-exemption key off and on (report, Safety Findings). Unit tests and offline replay; on in intersection run 2 (never fired) and in the demonstration takes (firings not counted); not validated live.#fig-source("6.50")]),
) <tab:res-sx>

== Offline Contact Recompute <sec:supp-contacts>

@tab:app-contacts lists the offline recompute of footprint gaps over 44 recorded bundles: the demonstration takes, both intersection runs and the registered five-robot pilot#ev("6.12"). For every ground-truth row the URDF collision shapes are placed at the logged pose, and the signed planar gap to every box (walls, racks, barrier blocks and declared obstacles) and to every other robot is measured. A gap of 5 mm or less is a contact entry. The values are a geometric footprint proximity at 10 Hz, not a physics contact. *The method was validated live once:* the validation take could not show entries at a pin#ev("6.17"), but in a scripted safety test the live logger recorded a real contact and matched this recompute row by row#ev("6.86")\; the bundle values themselves remain offline. The one sustained contact in the table is independently confirmed from the demonstration record#ev("6.42"). Gaps are in millimetres, rounded to 0.1 mm (so the five-robot minimum of −0.16 mm reads −0.2), times in simulated seconds, and r$n$ stands for `robot_`$n$.

#[
#set text(size: 8pt)
#show raw: set text(size: 6.5pt)
#figure(
  table(
    columns: (0.75fr, 1.55fr, 0.5fr, 0.75fr, 1.7fr, 0.7fr, 1.3fr),
    align: left,
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    inset: 3pt,
    table.header([*Group*], [*Bundle*], [*Rows*], [*Static verdict*], [*Min static gap (robot, box, time)*], [*Robot–robot verdict*], [*Min robot–robot gap (pair, time)*]),
    [Demo campaign], [`cvD_t01_a1`], [2601], [clear], [103.0 (r4, `aisle_barrier/north`, 65.0)], [clear], [195.0 (r1/r2, 67.2)],
    [Demo campaign], [`cvD_t02_a1`], [2601], [clear], [137.3 (r1, `rack/NW`, 53.9)], [clear], [176.3 (r1/r2, 25.7)],
    [Demo campaign], [`cvD_t03_a1`], [2601], [clear], [96.8 (r4, `aisle_barrier/north`, 65.5)], [clear], [190.1 (r1/r2, 26.1)],
    [Demo campaign], [`hoD_t01_a1`], [3001], [clear], [44.5 (r2, `aisle_barrier/north`, 121.0)], [clear], [138.8 (r1/r2, 22.3)],
    [Demo campaign], [`ibD_t01_a1`], [585], [clear], [511.0 (r1, `rack/NW`, 0.0)], [clear], [2302.5 (r2/r3, 34.3)],
    [Demo campaign], [`ibD_t01_a2`], [3001], [clear], [136.4 (r1, `rack/NW`, 56.3)], [clear], [191.6 (r1/r2, 76.1)],
    [Demo campaign], [`ibD_t02_a1`], [3001], [clear], [131.0 (r1, `rack/SW`, 74.9)], [clear], [135.6 (r2/r4, 28.7)],
    [Demo campaign], [`ibD_t03_a1`], [3001], [clear], [93.6 (r1, `rack/NW`, 130.5)], [clear], [153.8 (r2/r3, 28.0)],
    [Demo campaign], [`ibD_t04_a1`], [3001], [clear], [129.3 (r1, `rack/SW`, 72.8)], [clear], [147.6 (r2/r3, 28.2)],
    [Demo campaign], [`ibD_t05_a1`], [3001], [clear], [129.4 (r1, `rack/SW`, 73.8)], [clear], [149.0 (r1/r4, 27.9)],
    [Demo campaign], [*`m5D_t01_a1`*], [6001], [*sustained contact*], [*−0.2 (r3, `obstacle_2`, 191.4)*], [clear], [85.0 (r1/r4, 42.6)],
    [Intersection run 1], [`ib10L_e01_armA_a1`], [3001], [clear], [103.5 (r1, `rack/NW`, 131.9)], [clear], [152.0 (r1/r3, 28.2)],
    [Intersection run 1], [`ib10L_e01_armA_a2`], [3001], [clear], [132.3 (r1, `rack/SW`, 72.8)], [clear], [156.8 (r2/r3, 27.7)],
    [Intersection run 1], [`ib10L_e02_armB_a1`], [3001], [clear], [504.9 (r3, `rack/SE`, 23.3)], [clear], [140.0 (r1/r4, 27.6)],
    [Intersection run 1], [`ib10L_e03_armA_a1`], [3001], [clear], [128.5 (r1, `rack/SW`, 126.6)], [clear], [145.0 (r2/r4, 26.5)],
    [Intersection run 1], [`ib10L_e04_armB_a1`], [3001], [clear], [496.5 (r3, `rack/SE`, 24.1)], [clear], [126.8 (r2/r3, 27.7)],
    [Intersection run 1], [`ib10L_e05_armA_a1`], [3001], [clear], [108.7 (r1, `rack/NW`, 131.4)], [clear], [139.5 (r1/r4, 28.6)],
    [Intersection run 1], [`ib10L_e06_armB_a1`], [3001], [clear], [487.6 (r3, `rack/SE`, 23.4)], [clear], [157.5 (r2/r3, 27.4)],
    [Intersection run 1], [`ib10L_e07_armA_a1`], [3001], [clear], [101.3 (r1, `rack/NW`, 130.4)], [clear], [172.9 (r2/r3, 28.1)],
    [Intersection run 1], [`ib10L_e08_armB_a1`], [3001], [clear], [497.2 (r3, `rack/SE`, 24.6)], [clear], [151.1 (r1/r4, 27.3)],
    [Intersection run 1], [`ib10L_e09_armA_a1`], [3001], [clear], [121.9 (r1, `rack/NW`, 57.5)], [clear], [82.1 (r1/r2, 295.4)],
    [Intersection run 1], [`ib10L_e10_armB_a1`], [3001], [clear], [490.1 (r3, `rack/SE`, 21.8)], [clear], [163.1 (r2/r3, 27.5)],
    [Intersection run 2], [`ib10S_e01_armA_a1`], [3001], [clear], [95.9 (r1, `rack/NW`, 129.7)], [clear], [121.7 (r3/r4, 109.4)],
    [Intersection run 2], [`ib10S_e02_armC_a1`], [3001], [clear], [171.0 (r1, `rack/SW`, 283.6)], [clear], [1772.2 (r2/r3, 43.7)],
    [Intersection run 2], [`ib10S_e02_armC_a2`], [3001], [clear], [115.8 (r1, `rack/NW`, 131.9)], [clear], [149.6 (r1/r4, 27.5)],
    [Intersection run 2], [`ib10S_e03_armA_a1`], [3001], [clear], [125.0 (r1, `rack/SW`, 71.8)], [clear], [155.0 (r2/r3, 27.3)],
    [Intersection run 2], [`ib10S_e04_armC_a1`], [3001], [clear], [130.2 (r1, `rack/SW`, 74.1)], [clear], [157.3 (r2/r3, 27.0)],
    [Intersection run 2], [`ib10S_e05_armA_a1`], [3001], [clear], [125.0 (r1, `rack/SW`, 73.6)], [clear], [162.3 (r2/r3, 28.1)],
    [Intersection run 2], [`ib10S_e06_armC_a1`], [3001], [clear], [128.1 (r1, `rack/SW`, 74.2)], [clear], [159.8 (r2/r3, 27.3)],
    [Intersection run 2], [`ib10S_e07_armA_a1`], [3001], [clear], [130.7 (r1, `rack/SW`, 71.0)], [clear], [134.9 (r2/r3, 26.1)],
    [Intersection run 2], [`ib10S_e08_armC_a1`], [3001], [clear], [129.4 (r1, `rack/SW`, 73.5)], [clear], [201.5 (r1/r2, 89.8)],
    [Intersection run 2], [`ib10S_e09_armA_a1`], [3001], [clear], [110.0 (r1, `rack/NW`, 132.3)], [clear], [185.0 (r1/r3, 29.4)],
    [Intersection run 2], [`ib10S_e10_armC_a1`], [3001], [clear], [130.5 (r1, `rack/SW`, 75.0)], [clear], [142.3 (r2/r3, 27.9)],
    [Registered pilot], [`E27 A a1`], [6001], [clear], [34.8 (r1, `obstacle_1`, 99.8)], [clear], [221.9 (r1/r5, 581.7)],
    [Registered pilot], [`E27 B a1` (bring-up abort)], [670], [clear], [97.9 (r4, `rack/SW_west`, 37.8)], [clear], [1922.8 (r1/r2, 29.4)],
    [Registered pilot], [`E27 B a2`], [6001], [clear], [34.7 (r5, `obstacle_2`, 50.4)], [clear], [215.8 (r3/r4, 46.9)],
    [Registered pilot], [`E28 A a1`], [6001], [clear], [28.1 (r5, `rack/SE_east`, 104.4)], [clear], [223.5 (r1/r5, 45.5)],
    [Registered pilot], [`E28 B a1`], [6001], [clear], [41.1 (r1, `obstacle_2`, 42.5)], [clear], [101.1 (r1/r5, 44.8)],
    [Registered pilot], [`E29 A a1`], [6001], [clear], [7.1 (r2, `obstacle_2`, 42.8)], [clear], [133.4 (r1/r4, 46.4)],
    [Registered pilot], [`E29 B a1`], [6001], [clear], [14.0 (r1, `obstacle_1`, 38.8)], [clear], [119.4 (r1/r4, 46.1)],
    [Registered pilot], [*`E30 A a1`*], [6001], [*brief graze*], [*1.0 (r2, `obstacle_1`, 48.9)*], [clear], [231.7 (r3/r4, 44.9)],
    [Registered pilot], [`E30 B a1`], [6001], [clear], [10.0 (r2, `obstacle_1`, 47.9)], [clear], [169.1 (r3/r4, 43.3)],
    [Registered pilot], [`E31 A a1`], [6001], [clear], [19.3 (r2, `obstacle_2`, 44.3)], [clear], [178.9 (r1/r5, 577.2)],
    [Registered pilot], [`E31 B a1`], [6001], [clear], [8.7 (r2, `obstacle_2`, 42.0)], [clear], [209.3 (r1/r5, 41.2)],
  ),
  caption: flex-caption([Offline contact recompute over 44 bundles.], [Offline footprint-gap recompute over 44 recorded bundles, by a method validated live once. Robot–static: one bundle with a sustained contact (which also contains a 3.79 mm brief graze), one bundle with a brief graze, 42 bundles clear; both grazes are within noise. Robot–robot: closest footprint gap 82.1 mm. Two short bundles (a bring-up abort and an early-ended take) and one run that formed no jam have robot–robot minima above 1.7 m.#fig-source("6.12")]),
) <tab:app-contacts>
]
