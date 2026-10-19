# Modeling rules

Distilled working rules for build123d models in this repository. They are constraints for writing models, not a tutorial. (Derived from hands-on study notes; see `docs/legacy/` for the full original text.)

## Parameters

- All critical dimensions live in `spec.yaml` and are read at build time. No magic numbers in model code.
- Derived values are computed from base parameters, never re-stated.
- Units are millimeters, stated once, everywhere.

## Geometry strategy

- **2D before 3D.** Sketch, fillet and chamfer in 2D where possible; 3D booleans on raw solids are the fragile path.
- **Fillet/chamfer last.** Late features break less often when parameters change.
- **Workplanes from geometry.** Derive planes from existing faces instead of computing coordinates by hand.
- **Vectorize bulk operations.** Subtract a list of tools in one operation instead of looping.
- **Assemblies: shallow copies.** Use `copy()` for repeated components; `deepcopy()` multiplies memory for no benefit.

## Selection discipline

- Never select by bare index (`edges()[0]`). Filter by axis, geometry type or position, then sort explicitly.
- After booleans, prefer `Select.LAST` / `Select.NEW` over re-searching.
- Before applying fillet/chamfer to a selection, assert the selection size — a silent empty selection produces a silently wrong model.

## Code quality

- Type hints and docstrings; the model script is read by humans and agents.
- One part per script; the script exposes a single build function returning the solid.
- The script must run headless: no viewer imports at module level, no display dependency.

## What the tests expect from a model script

- `build(spec: dict) -> Solid` (or Compound for assemblies) as the entry point.
- Deterministic output: same spec in, same geometry out.
- No side effects at import time (no exports on import; export happens in the test/render harness).
