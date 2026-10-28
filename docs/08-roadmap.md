# Roadmap: testing and workflow improvements

Living document. Each item lists what it adds, why it matters, and what it
depends on. Items move to `docs/06-lessons-learned.md` or `docs/03-testing.md`
once implemented.

## Framework track

Guiding principle: a framework proves itself not by what it can do, but by
**how little a new part costs**. Maturity metric — *cost of a new part*:
new lines of code outside spec + model, number of correction rounds, how
many tools needed changes. Falling = the framework matures; rising = it is
a collection of scripts. Items below are ordered to reduce this metric, and
nothing is built "for reserve" — only on a real trigger (minimal
maintenance).

### Phase 1 — Proof (highest priority)

- **Third part with different features** — the "Now" item below, plus one
  addition: record every edit this part forces in the tools
  (`render_drawing.py`, `validate_spec.py`, tests). That map shows exactly
  where the framework ends and manual work begins. The feature mix must
  differ from pockets + legs (e.g. a mount with holes and ribs, a bracket,
  a box with screw bosses) — that is what exposes gaps in generality.
- **"Use this template"** — enable in the GitHub UI (one minute, zero
  maintenance); reuse becomes one click for anyone.

### Phase 2 — Generalization, driven by the proof

Starts only after Phase 1 shows what actually generalizes (rule of three):

- **Annotation plan in `render_drawing.py` → spec-driven feature
  vocabulary.** The part declares features in the spec
  (`type: pocket|hole|rib|leg|…` + parameters); the renderer draws from the
  declaration. Today the annotation plan hardcodes pocket/leg/rib (about
  144 references) — the largest known gap.
- **Shared test harness in `conftest.py`** — helpers such as
  `assert_spec_dimensions`, a connectivity check, an export round-trip. A
  new part = spec + model + a thin test file. Today `conftest.py` has 6
  lines and tests are written from scratch.
- **Fit-check as a test** — see "Next" below.

### Phase 3 — Framework as a product (only with an audience or a second instance)

- **Getting-started for an outside reader** — docs/02 and docs/07 are
  written for the owner and agents; an adopter needs a "clone → first part
  in 30 minutes" path.
- **Versioned contract** — `spec.schema.json` is the framework's API; today
  it has `$id` + title but no version. Add `schema_version` (in the schema
  and as a required spec field); contract changes stay backward-compatible,
  breaking changes = new major version.
- **Tags + CHANGELOG at milestones** — rejected for now (minimal
  maintenance); revisit when the repo has adopters.
- **Framework vs. content separation** — `parts/` convention or a separate
  template repo; at a second instance, not speculatively.

### Anti-goals

- Abstraction or refactoring "for reserve" before the third use.
- pip package, plugin system — pure cost without an audience.
- Renaming or a new brand (decided 2026-10-28; the option stays open
  additively).
- Anything that raises ongoing maintenance without a measurable reduction
  in the cost of a new part.

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
  possible without one; or set both manually in the GitHub UI).
- External FDM print of brush_organizer (PLA/PETG); calibrate the
  printability checks against the result.
- Presentation polish: render material color, optional hero variant.
