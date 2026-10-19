# Testing: what the suite proves, and what it does not

## What every model test asserts

| Check | Method | Catches |
|---|---|---|
| Overall dimensions | bounding box vs. spec ± tolerance | wrong parameter, wrong unit |
| Volume | BREP volume vs. analytic expectation | bad cut/fillet/extrude direction |
| Validity | `is_valid()` on the solid | broken boolean, non-manifold result |
| Feature counts | number of holes, faces, edges vs. spec | missing or duplicated features |
| Positions | distances between feature centers vs. spec | misplaced holes, wrong spacing |
| Export round-trip | export STEP/STL, re-import, re-check | corrupted or empty export |
| Completeness | every spec dimension has ≥1 assertion | silently untested dimensions |

## How tests read the spec

Tests and the model both load `specs/<part>/spec.yaml`. The spec is the only shared source of truth; the tests never restate dimensions independently of it. This is deliberate: it makes a spec error a *review* problem (caught at the approval gate), not a *test* problem — and it keeps the two from drifting apart.

## What tests cannot prove

- **Visual correctness.** A model can pass every measurement and still look wrong (misplaced rib, mirrored part where orientation matters). Previews exist for this; a human judges them.
- **Full GD&T.** Flatness, perpendicularity, runout and similar formal tolerances are only approximated by simplified checks (e.g., concentricity as center distance). Formal tolerance analysis is out of scope and is never implied by a green suite.
- **Fitness for manufacturing.** Tests prove the geometry matches the spec; they do not prove the spec is manufacturable.

## CI role

GitHub Actions runs the suite on every push. CI green means: the code builds the model, the model matches the spec, exports round-trip. CI does not approve appearance — that gate is human, always.
