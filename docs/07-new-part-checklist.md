# Checklist: adding a new part

The practical, step-by-step version of the workflow in
[01-workflow.md](01-workflow.md). Follow it top to bottom; every step
produces an artifact that the next step consumes.

## 1. Spec

- [ ] Create `specs/<part>/spec.yaml` with every dimension, tolerance,
      feature count and note (units: mm).
- [ ] Mark anything ambiguous or unreadable as `uncertain: true` — never guess.
- [ ] Write every interpretation of a hand sketch as an **explicit,
      veto-friendly assumption** (a comment in the spec), so a veto costs one
      parameter change, not re-modeling.
- [ ] **Gate:** a human reviews the transcription against the original
      sketch/drawing. Only after approval is the spec authoritative.
- [ ] Validate the spec against `schemas/spec.schema.json`
      (`python tools/validate_spec.py`) — CI runs the same gate.

## 2. Model

- [ ] Create `models/<part>.py` exposing `build(spec: dict) -> Solid` (or
      `Compound`), reading every parameter from `spec.yaml` — no magic numbers.
- [ ] Follow [05-modeling-rules.md](05-modeling-rules.md): 2D before 3D,
      fillet/chamfer last, explicit selections with size assertions.
- [ ] Verify every build123d call against the installed version (`help()`,
      `inspect.signature`, or that version's documentation) — never from
      memory; record any surprise in [06-lessons-learned.md](06-lessons-learned.md).

## 3. Drawing

- [ ] Generate the drawing from the built model:
      `python tools/render_drawing.py specs/<part>/spec.yaml` — the views are
      **projected from the model** (`project_to_viewport`, OCCT hidden-line
      removal; hidden edges dotted), while dimensions, labels, the schedule
      and the title block come from the spec (`dimension_plan`).
- [ ] Check the drawing-completeness gate passes
      (`pytest tests/test_drawing_completeness.py`): every spec feature must
      appear in the drawing — openings at spec position/size, ribs where the
      fill requires them, hidden profiles for internal features (M4 lessons
      9–10).
- [ ] Compare the drawing against the original sketch and **zoom into
      features** (ribs, holes, walls) — rendering defects hide at full-sheet
      scale (M4: three zoom-caught correction rounds).
- [ ] Commit `drawing.png`, `drawing.svg` and `drawing.manifest.json`.

## 4. Tests

- [ ] Create `tests/test_<part>.py` asserting **every** spec dimension
      against measured geometry (bounding box, volume, feature counts,
      positions, validity, export round-trip).
- [ ] Include the mandatory **connectivity test** (`body_count == 1` or the
      expected count) — per-dimension tests cannot see disconnected bodies.
- [ ] Include the completeness check: the suite fails if any spec dimension
      has no assertion.
- [ ] Run `pytest` locally until green (includes the drawing gate).

## 5. Preview and compare

- [ ] Generate previews (`pytest` renders them into `exports/`, or
      `tools/render_preview.py` directly).
- [ ] **Compare the preview against the sketch before the final build.**
      This step caught the one defect the whole suite missed (M3: legs
      silently disconnected by open quarter sectors).
- [ ] For presentation images, use the Blender pipeline
      ([tools/README-render_blender.md](../tools/README-render_blender.md)).

## 6. Verification report

- [ ] Write `specs/<part>/verification.md`: drawing dimension → spec value →
      measured value → result, plus spec/model git hashes, test result, and
      the resolution of every `uncertain` item.
- [ ] Add printability notes (FDM bridging spans, hole shrinkage ~0.1–0.2 mm)
      where relevant.
- [ ] Record the build123d API calls used and that they were verified against
      the installed version (note the version number).

## 7. Human acceptance

- [ ] A human compares previews and the report against the original intent.
- [ ] Record acceptance (date + reviewer note) in `verification.md`.
- [ ] Only then is the part done; exports (STEP/STL) come from the verified
      model, never from an earlier draft.

## 8. Privacy (public repository)

- [ ] Run the privacy scan before every push: personal names, contacts and
      identifiers anonymized in files and commit messages; hand sketches and
      photos of prototypes stay private by default — the public repository
      shows the spec, the generated drawing and renders, not the workshop
      desk (see [01-workflow.md](01-workflow.md), Git discipline).