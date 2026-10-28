# Verification report — hub_flange

- Spec: `specs/hub_flange/spec.yaml` — transcribed from a public-domain (CC0)
  engineering drawing (Innerscene Drawing Library, "Hub flange drawing
  (dimensioned)", scale 1:1, mm; the input file stays private by owner
  decision — only generated outputs go to the repository). The interpretation
  was offered as 5 veto questions and approved by the owner in chat
  2026-10-28 (listed under Assumptions in the spec).
- Model: `models/hub_flange.py` (build123d 0.13.0, Python 3.13)
- Test run: **64 passed** (45 existing incl. the new clearance-gate test + 19 new), local run 2026-10-28;
  includes the mandatory single-body connectivity test and the
  drawing-completeness gate (flange probes: bolt circle, bore, keyway, hub
  silhouette, view envelopes, plan coverage, manifest).
- Exports: `exports/hub_flange.stl` (watertight), `exports/hub_flange.step`
- Drawing: `specs/hub_flange/visuals/drawing.png` + `.svg` + manifest
  (frame-clearance gate OK; drawn tags == dimension plan)
- Previews: `exports/hub_flange_{iso,front,top,side,bottom}.png`

## Dimension check (source drawing → spec → measured)

Scale calibration of the source raster: 12.43 px/mm, anchored on the
dimensioned Ø120; cross-checked on the PCD, hub and bore circles (all within
pixel noise, worst ~1.5 % on the smallest circle). After the transcription,
the source DXF geometry (exact coordinates, not pixels) was read back as
ground truth and confirmed every value below — see the keyway note for the
one intentional deviation.

| Quantity | Source drawing | Spec | Measured | Result |
|---|---|---|---|---|
| Flange Ø | 120 (dimensioned) | 120 | 120.000 | PASS |
| Flange thickness | 12 (dimensioned) | 12 | 12.000 | PASS |
| Hub Ø | 50 (dimensioned) | 50 | 50.000 | PASS |
| Hub length | 18 (= 30 − 12; exact in the DXF section) | 18 | 18.000 | PASS |
| Total height | 30 (dimensioned) | 30 | 30.000 | PASS |
| Bore Ø | 25 (dimensioned) | 25 | 25.000 | PASS |
| PCD Ø | not dimensioned (scaled: r 44.9) | 90 | 89.998 | PASS |
| Bolt holes | callout "6X Ø11 EQ. SP. ON Ø90 PCD" | 6 × Ø11 | 6 × 11.000 | PASS |
| Bolt hole positions | #1 at 12 o'clock, even spacing | start 90°, even | exact (0/±38.97, ±45/±22.5) | PASS |
| Keyway width | not dimensioned (scaled ~8.0) | 8 | 8.000 | PASS |
| Keyway depth | not dimensioned (scaled ~3.5) | 3.3 (DIN 6885) | 3.300 | PASS (owner decision, below) |
| Keyway / hole #1 clocking | both at 12 o'clock | 90° | exact | PASS |
| Connectivity (body count) | — | 1 | 1 | PASS |
| Solid validity | — | valid | valid | PASS |
| STL watertight | — | required | true | PASS |
| STL volume vs BREP | — | ±2 % | −0.042 % | PASS |
| Material volume | — | — | 148.6 cm³ (≈184 g PLA) | info |

BREP volume 148 647.1 mm³ vs analytic 148 699.1 mm³ (−0.035 %): the naive
keyway term (8 × 3.3 × 30) understates the cut — the slot's corners reach
into the bore circle, where the circle dips below the slot mouth. Covered by
the test's rel=0.001 tolerance; the STL-vs-BREP delta (−0.042 %) is the
tessellation error.

## Keyway depth: source 3.5 vs DIN 6885 3.3 (owner decision)

The source drawing does not dimension the keyway anywhere; its geometry
(exact in the DXF) puts the slot floor at 16.0 mm from the axis → depth 3.5.
The owner approved 8 × 3.3 per DIN 6885 (key 8×7, hub side t2 = 3.3) — the
standard value for a keyed Ø25 hub, preferred over the unscaled source
proportion. Consequence for the drawing: the depth is dimensioned per DIN
6885 as d + t2 = 28.3 (see Rendering notes).

## API surprise (also recorded as docs/06 lesson 11)

The bore wall — a cylindrical face trimmed by the keyway slot — reads
`Face.radius == None` in build123d 0.13.0, while every untrimmed cylinder
(plate, hub, bolt holes) reads its radius fine. A test keyed on radius would
silently skip exactly the face the new feature complicates. The test
identifies the bore face by invariants that survive trimming (full-height
z-span + envelope bbox) and takes all feature positions from bounding-box
centers, never `Face.center()` of a trimmed cylinder. The drawing gate
identifies the same features in the projected views by position and span
(`_vertical_lines`), not by face identity.

## Rendering notes (flange kind added to tools/render_drawing.py)

- The renderer now dispatches on the part kind (`features.flange_plate`):
  bolt-circle/bore/keyway probes and top/front/end annotations mirror the
  model the same way the pocket path mirrors the organizer model. This is
  the measured cost-of-a-new-part datum for the docs/08 framework track
  (renderer lines outside spec+model; see the session report).
- Visual corrections (two found by my own zoom review, the third round by
  the owner):
  1. The 8 mm keyway-width dimension got outside arrows (`_dim_h_narrow`) —
     two inside arrowheads (~3.4 mm each at 1:2) overlap on an 8 mm dim line.
  2. The keyway depth is dimensioned per DIN 6885 as d + t2 = 28.3 in the
     end view: the bore silhouette on the keyway side is cut away by the
     slot, and the slot-mouth line sits 0.66 mm from the wall line —
     ambiguous/illegible at 1:2. The d + t2 form references two drawn lines
     (the opposite bore wall and the slot floor).
  3. Owner review flagged the dimension numbers touching the part outlines
     (Ø25, 28.3). A new mechanical gate (`text_geometry_collisions`: every
     text ≥2 mm from the projected geometry, judged on the text alone —
     leader arrows point at geometry by design) confirmed those two and
     caught the same class on Ø90 and on rotated vertical-dim numbers; all
     placements fixed (dim lines moved below the part, the Ø90 leader text
     out of the Ø120 outline, left-side vertical dim numbers on the far
     side of their dim line). The organizer drawing had the same
     rotated-text class on two dims and was re-rendered with the fix.
- Manifest for a part without pockets: `pocket_labels: []`,
  `schedule_rows: 0` (no pocket table); probes carry a `flange` section.
- Seam edges (cylinder closure artifacts) follow the existing rule: dropped
  in the end view, coincident with silhouettes elsewhere.

## Printability notes (FDM)

- Print flat (plate on the bed), hub up: no supports needed (bore, keyway
  and bolt holes are all vertical through-features).
- Holes shrink ~0.1–0.2 mm in PLA: the Ø11 bolt holes have margin; the Ø25
  bore with keyway needs reaming or a +0.2 offset if a keyed shaft must fit.
- Sharp edges per the approved spec (the source drawing has none either).
  The source's `MATL: 6061-T6` describes the machined original — not
  applicable to an FDM print (PLA/PETG); recorded as provenance only.

## What the tests cannot prove

Appearance and drawing readability (owner zoom review), practical
printability, and the fitness of the DIN 6885 substitution for the intended
key.

## Owner acceptance

- Awaiting owner review of the drawing (`specs/hub_flange/visuals/drawing.png`)
  and the previews; verdict to be recorded here.