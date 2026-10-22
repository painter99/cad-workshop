# Roadmap: testing and workflow improvements

Living document. Each item lists what it adds, why it matters, and what it
depends on. Items move to `docs/06-lessons-learned.md` or `docs/03-testing.md`
once implemented.

## Now

- **Third part (pattern replication)** — build a new, functionally different
  part through the full loop and record how many correction rounds it needed.
  The strongest evidence that the workflow is a method, not a one-off.
  Reveals which improvements below are actually needed.

*(Shipped 2026-10-22: spec schema validation — `schemas/spec.schema.json`,
`tools/validate_spec.py`, CI step; documented in
[03-testing.md](03-testing.md).)*

## Next

- **Fit-check as a test** — virtual interference check (trimesh) of the
  intended contents against each pocket, with FDM tolerance applied
  (~0.1–0.2 mm). Tests function, not just geometry.

- **Visual diff in review** — render before/after previews for every model
  change so the human gate judges the change, not just the final state.

## Later

- **Printability in the loop** — headless slicer pass (e.g. PrusaSlicer CLI)
  over the exported STL: bridging spans, overhangs, time/material estimates.
  Turns the manual printability notes in verification reports into tests,
  calibrated against the first real print.

- **Property-based geometry tests** — invariant checks (validity, watertight,
  body count) across randomized spec parameters instead of fixed assertions;
  catches edge cases fixed assertions never touch.

- **Part families** — generate variants (pocket count, pitch) from one
  parametric spec; demonstrates the real power of spec-driven modeling.

## Infrastructure / housekeeping

- GitHub topics + description (requires a token; PATCH /repos is not
  possible without one).
- External FDM print of brush_organizer (PLA/PETG); calibrate the
  printability checks against the result.
- Presentation polish: render material color, optional hero variant.
