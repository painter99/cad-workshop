# Verification report — brush_organizer

- Spec: `specs/brush_organizer/spec.yaml` — transcribed from a hand sketch,
  approved by Pavel in chat 2026-10-19 including stated assumptions
  (slot length 30 mm, X-web under all pockets, leg inset 15 mm).
- Model: `models/brush_organizer.py`
- Test run: 18 passed (8 test_block + 10 brush_organizer; local, build123d 0.13.x, Python 3.13)
- Exports: `exports/brush_organizer.stl` (watertight), `exports/brush_organizer.step`
- Previews: `exports/brush_organizer_{iso,front,top,side}.png`

## Dimension check

| Quantity | Spec value | Measured | Result |
|---|---|---|---|
| Length (X) | 250 | 250.000 | PASS |
| Width (Y) | 55 | 55.000 | PASS |
| Block height | 35 | 35.000 | PASS |
| Leg height | 5 | 5.000 | PASS |
| Leg diameter | 5 | 5.000 | PASS |
| Leg count | 6 | 6 | PASS |
| Pocket openings on top | 6 | 6 | PASS |
| Pocket positions (X) | -105/-63/-21/21/63/105 | all exact | PASS |
| Circle pockets Ø | 35 / 22 / 30 | 35 / 22 / 30 | PASS |
| Slot widths (X) | 12 / 15 | 12 / 15 | PASS |
| Pocket depths | 15/30/30/30/30/15 | void at mid-depth + wall beside each | PASS |
| X-web under pockets | open below, ribs on diagonals, open quarters | probe-verified (P4) | PASS |
| Solid validity | valid | valid | PASS |
| STL watertight | required | true | PASS |
| STL volume vs BREP | ±2 % | +0.01 % | PASS |

## Assumptions used (veto-friendly, one-parameter changes)

1. Slot length along Y = 30 mm — the sketch does not dimension it.
2. X-web under all six pockets, including the shallow end pockets (their
   open quarters are ~20 mm tall; the FDM print bridges them with the ribs).
3. Legs: 4 near corners + 2 at mid-length, inset 15 mm. Note: the end legs
   sit directly under the end pockets and are visible through the open
   X-quarters.

## Notes and limits

- The X-web structure was verified by point probes (open below the web,
  material on both diagonals, open quarter sectors), not by full GD&T.
- Preview renderer (matplotlib) shows depth-sorting artifacts; the top view
  is the reliable one for pocket layout.
- Print considerations: X-webs require bridging (largest span ~17 mm under
  the shallow pockets). For PLA/PETG FDM this is printable; expect cosmetic
  sag on the web undersides. Hole diameters may shrink ~0.1–0.2 mm on FDM;
  compensate in spec if a tight fit is needed.
