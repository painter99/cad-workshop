# Verification report — brush_organizer (final)

- Spec: `specs/brush_organizer/spec.yaml` — transcribed from a hand sketch,
  corrected and approved by Pavel in chat 2026-10-19 (three correction rounds,
  each applied and re-verified; final X-fill choice and leg placement confirmed
  by Pavel, remaining assumptions listed below are veto-friendly).
- Model: `models/brush_organizer.py` (build123d 0.13.0, Python 3.13)
- Test run: **19 passed** (8 test_block + 11 brush_organizer), local run
  2026-10-19; includes the mandatory single-body connectivity test.
- Exports: `exports/brush_organizer.stl` (watertight), `exports/brush_organizer.step`
- Previews: `specs/brush_organizer/drafts/final_{top,iso,bottom}.png`
  (visually inspected and compared against the sketch before this report)

## Dimension check

| Quantity | Spec value | Measured | Result |
|---|---|---|---|
| Length (X) | 250 | 250.000 | PASS |
| Width (Y) | 55 | 55.000 | PASS |
| Block height | 35 (+5 legs = 40) | 40.000 | PASS |
| Leg count | 4 (corners only) | 4 | PASS |
| Leg centers | ±120 / ±22.5 (inset 5) | exact | PASS |
| Leg diameter / height | 5 / 5 | 5 / 5 | PASS |
| Pocket openings on top | 6 | 6 | PASS |
| Pocket positions (X) | -105/-63/-21/21/63/105 | all exact | PASS |
| Circle pockets Ø | 35 / 22 / 30 / 35 | exact | PASS |
| Rectangular pockets | 15 along X × 12 across Y | 15 × 12 | PASS |
| Pocket depths | 15/30/30/30/30/15 | void at mid-depth + wall beside each | PASS |
| X ribs | in ALL pockets, from block bottom to pocket floor | probe-verified near bottom AND near floor, every pocket | PASS |
| Open quarters | through to the bottom face | probe-verified, every pocket | PASS |
| Connectivity (body count) | 1 | 1 | PASS |
| Solid validity | valid | valid | PASS |
| STL watertight | required | true | PASS |
| STL volume vs BREP | ±2 % | +0.009 % | PASS |
| Material volume | — | 377 cm³ (~468 g PLA) | info |

## History of corrections (all applied and re-verified)

1. First attempt had 5 disconnected bodies (legs detached by the open
   quarters) — caught visually by Pavel, tests missed it → mandatory
   `body_count == 1` test added.
2. Rectangular pockets re-read as 12×15 mm (12 across the block, 15 along it),
   30 mm deep, centered in Y; the full-width channel reading was rejected.
3. Legs reduced to the 4 corner ones, then pushed almost flush into the
   corners (inset 5 mm, leg edge 2.5 mm from the block edge) for stability.
4. X ribs: span the full under-region height (block bottom → pocket floor)
   in ALL pockets incl. the shallow 35 mm ones — the crosses sit at the
   lowest point of the block, no recessed floating web. Pavel offered a
   cheaper 5–10 mm cross at the bottom; rejected because it would turn the
   shallow 15 mm pockets into ~25–30 mm deep ones (the brush rests on the
   ribs, so rib height = resting depth). Each rib end is embedded 2 mm into
   the wall (`rib_embed`) for a solid union.

## Assumptions still open (veto-friendly, one-parameter changes)

1. Slot orientation: 12 mm across the block (Y) × 15 mm along it (X).
2. Leg inset 5 mm from the edges (2.5 mm leg-edge margin).
3. Rib width 4 mm, rib embed 2 mm.

## Notes and limits

- The X structure was verified by point probes (rib material near the bottom
  and near the floor on the diagonal, open quarter sectors), not by full GD&T.
- The 35 mm end pockets leave a 2.5 mm wall to the block end face over the
  full height; the diagonal ribs brace it. Watch this wall on the first print.
- Preview renderer (matplotlib) shows depth-sorting artifacts; the top and
  bottom views are the reliable ones.
- Print considerations: the tall ribs print as vertical walls (no bridging
  over the open quarters is required for the ribs themselves; the pocket
  floors above the open quarters are bridged only where a quarter spans
  between ribs — largest ~17 mm). For PLA/PETG FDM this is printable.
  Hole diameters may shrink ~0.1–0.2 mm on FDM; compensate in spec if a
  tight fit is needed.
