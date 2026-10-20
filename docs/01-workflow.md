# Workflow: spec → model → test → preview → review

The workshop runs a closed loop. Nothing is "done" because it was written confidently; it is done when the machine and a human both confirm it.

## Stages

### 1. Spec (human-approved, machine-readable)

- Source: a drawing, sketch or verbal description from the requester.
- The spec file `specs/<part>/spec.yaml` holds every dimension, tolerance, feature count and note.
- **Gate:** the transcription is reviewed against the original drawing by a human before modeling starts. A misread drawing digit would otherwise be verified "correctly" by every downstream test.

### 2. Drawing (from the approved spec)

- A dimensioned drawing is generated **from the spec** (`tools/render_drawing.py`
  → `specs/<part>/visuals/drawing.png/svg`) — never from the model.
- The drawing visualizes the *interpretation*: a human compares it against the
  original sketch before any modeling starts. A misread dimension is caught
  here, at the cost of one drawing generation — not later, in geometry.
- When the sketch is private, this drawing is also the public, dimension-bearing
  artifact of the part (see [04-verification-workflow.md](04-verification-workflow.md)).

### 3. Model (build123d)

- `models/<part>.py` reads parameters from `spec.yaml` — never hard-codes them, never relies on remembered values.
- Modeling rules that keep models robust are in [docs/05-modeling-rules.md](05-modeling-rules.md).

### 4. Tests (pytest)

- One assertion per spec dimension: bounding box, volume, hole counts, validity, export round-trip.
- A completeness test fails if any spec dimension has no matching assertion.
- Details and limits: [docs/03-testing.md](03-testing.md).

### 5. Preview (headless render)

- The test suite renders PNG previews from the built model (several views) into `exports/`.
- The preview is evidence for human review, not a substitute for it.

### 6. Verification report and review

- `specs/<part>/verification.md` records: drawing dimension → spec value → measured value → result.
- A human compares the preview and the report against the original drawing. Only then is the part accepted.

## Git discipline

- Work happens on a branch; every push and merge requires explicit human approval.
- CI must be green before merge; CI verifies code, the human verifies appearance.
- The original drawing is versioned together with the spec **when the owner
  agrees to publish it**; when the sketch must stay private, the spec's
  `drawing:` field points to a generated dimensioned drawing instead, and the
  public repository shows only generated artifacts (see
  [04-verification-workflow.md](04-verification-workflow.md)).
- **Privacy scan before every push to a public remote**: personal names, contacts and identifiers are anonymized in files and commit messages (M3: done via history rewrite before the first public push). Anonymization is part of the workflow, not a later cleanup — see [06-lessons-learned.md](06-lessons-learned.md), lesson 8.

## What this workflow deliberately does not do

- It does not drive machines, robots or production equipment. It produces verified geometry and documentation.
- It does not replace full GD&T inspection. Simplified geometric checks (positions, distances, counts) are covered; formal tolerance analysis is out of scope and labeled as such.
