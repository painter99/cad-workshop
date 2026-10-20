# Verification workflow: drawing → spec → model → report

## Purpose

This document defines how a drawing or sketch becomes a verified model, and what evidence is produced at each step.

## Step 1 — Transcription

1. The drawing (photo, scan, sketch) is stored at `specs/<part>/drawing.png`
   and versioned — **unless the owner keeps it private** (hand sketches and
   prototype photos do not belong in a public repository by default). In the
   private-sketch case the spec's `drawing:` field is set to `generated`, and
   a dimensioned drawing is generated from the approved spec instead
   (`tools/render_drawing.py` → `specs/<part>/visuals/drawing.png/svg`), so
   the public repository still shows a professional, dimension-bearing
   artifact without exposing the sketch.
2. Every dimension, tolerance, feature and note is transcribed into `specs/<part>/spec.yaml`.
3. Ambiguous or unreadable items are marked `uncertain: true` in the spec — never guessed.

## Step 2 — Approval gate

The transcription is reviewed against the drawing by a human. This gate exists because everything downstream (model, tests, report) inherits spec errors silently. Only after approval is the spec authoritative.

## Step 3 — Modeling and testing

The model reads the approved spec; the test suite asserts every dimension (see [03-testing.md](03-testing.md)).

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

The report also lists: spec version (git hash), model version (git hash), test run result, and any `uncertain` items with their resolution.

## Step 6 — Human acceptance

A human compares preview images and the report against the original drawing. Acceptance is recorded in the report (date + reviewer note). Only accepted parts are considered done.

## Limits, stated plainly

- Automated checks cover dimensions, topology, validity and export integrity.
- Visual checks (rib presence, shape, orientation) are human judgments supported by previews.
- Formal GD&T verification is out of scope; simplified geometric checks are labeled as simplified.
- A green suite proves "model matches spec", never "spec matches intent" — that is what the approval gate is for.
