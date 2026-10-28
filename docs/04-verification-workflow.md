# Verification workflow: spec → model → drawing → tests → report

## Purpose

This document defines how a drawing or sketch becomes a verified model, and what evidence is produced at each step.

## Step 1 — Transcription

1. The drawing (photo, scan, sketch) is stored at `specs/<part>/drawing.png`
   and versioned — **unless the owner keeps it private** (hand sketches and
   prototype photos do not belong in a public repository by default). In the
   private-sketch case the spec's `drawing:` field is set to `generated`, and
   a dimensioned drawing is generated after the model builds (views projected
   from the model, annotations from the spec; `tools/render_drawing.py` →
   `specs/<part>/visuals/drawing.png/svg`), so
   the public repository still shows a professional, dimension-bearing
   artifact without exposing the sketch.
2. Every dimension, tolerance, feature and note is transcribed into `specs/<part>/spec.yaml`.
3. Ambiguous or unreadable items are marked `uncertain: true` in the spec — never guessed.

## Step 2 — Approval gate

The transcription is reviewed against the drawing by a human. This gate exists because everything downstream (model, tests, report) inherits spec errors silently. Only after approval is the spec authoritative.

## Step 2.5 — Spec visualization before modeling (superseded 2026-10-23)

This step belonged to the earlier workflow, where a dimensioned drawing was
generated **from the spec** before modeling as a pre-model veto point. Since
the drawing views are now true projections of the built model (see
[01-workflow.md](01-workflow.md), stage 3, and
[06-lessons-learned.md](06-lessons-learned.md), lesson 10), generating them
before the model exists would mean hand-drawing the view geometry — the exact
defect class lesson 10 removed. The pre-model veto point is the spec approval
in Step 2; the drawing is generated after the model builds and is reviewed
against the sketch then (Step 3). When the sketch is private, the generated
drawing still serves as the public, dimension-bearing artifact of the part.

## Step 3 — Modeling, drawing and testing

The model reads the approved spec. The dimensioned drawing is generated from
the built model (views projected from the model, annotations from the spec)
and checked by the drawing-completeness gate; the test suite asserts every
dimension (see [03-testing.md](03-testing.md)).

## Step 4 — Preview before final build

Before running the final build and export, generate previews and **compare them
against the sketch**. M3 lesson: the first model passed the whole suite while
consisting of 5 disconnected bodies — the defect was visible in a preview and
caught by the human, not by tests. Preview-vs-sketch comparison is a mandatory
step, not a nicety (see [06-lessons-learned.md](06-lessons-learned.md), lesson 1).

## Step 5 — Verification report

`specs/<part>/verification.md` is generated/updated with a table:

```markdown
| Drawing dimension | Spec value | Measured | Result |
|---|---|---|---|
| Overall length 120 ±0.2 | 120 | 120.00 | PASS |
| Hole Ø8 ×2, spacing 60 | 8 / 60 | 8.00 / 60.00 | PASS |
```

The report also lists: spec version (git hash), model version (git hash), test run result, any `uncertain` items with their resolution, and the build123d API calls used — verified against the installed library version, which the report notes.

## Step 6 — Human acceptance

A human compares preview images and the report against the original drawing. Acceptance is recorded in the report (date + reviewer note). Only accepted parts are considered done.

## Limits, stated plainly

- Automated checks cover dimensions, topology, validity and export integrity.
- Visual checks (rib presence, shape, orientation) are human judgments supported by previews.
- Formal GD&T verification is out of scope; simplified geometric checks are labeled as simplified.
- A green suite proves "model matches spec", never "spec matches intent" — that is what the approval gate is for.
