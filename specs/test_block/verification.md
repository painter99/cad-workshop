# Verification report — test_block

- Spec: `specs/test_block/spec.yaml` (synthetic, no source drawing — first loop test)
- Model: `models/test_block.py`
- Test run: 8 passed (local, build123d 0.13.x, Python 3.13)
- Exports: `exports/test_block.stl` (watertight), `exports/test_block.step`
- Previews: `exports/test_block_{iso,front,top,side}.png`

## Dimension check

| Quantity | Spec value | Measured | Result |
|---|---|---|---|
| Length (X) | 60 | 60.000 | PASS |
| Width (Y) | 30 | 30.000 | PASS |
| Thickness (Z) | 8 | 8.000 | PASS |
| Hole diameter | 6 | 6.000 | PASS |
| Hole spacing | 40 | 40.000 | PASS |
| Through holes | 2 | 2 | PASS |
| Solid validity | valid | valid | PASS |
| Volume (analytic) | 13947.61 | 13947.61 | PASS |
| STL watertight | required | true | PASS |
| STL volume vs BREP | ±2 % | +0.001 % | PASS |

## Notes and limits

- Spec is synthetic (loop proof), so there is no drawing to compare against; the approval gate was the spec itself.
- Preview renderer (matplotlib) shows depth-sorting artifacts on concave geometry — visible as shading between the holes in iso/top views. Geometry is proven by tests; renderer quality is a known limitation, upgrade candidate.
- Printability here = watertight mesh + volume agreement. Slicer-specific checks (wall thickness, overhangs) are out of scope for this report.
