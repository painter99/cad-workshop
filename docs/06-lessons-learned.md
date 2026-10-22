# Lessons learned (M3 — brush organizer)

Distilled from the first full spec → model → test → preview → review cycle on a
multi-feature part (2026-10-19/20). These are working rules now, not anecdotes;
where a lesson changed the workflow, the affected doc is linked.

## 1. Tests do not see feature-to-feature disconnection

The first model passed every dimension, volume and validity test while
consisting of **5 disconnected bodies** — the corner legs were silently cut off
by the open quarter sectors. Nothing in a per-dimension test suite catches
that. Countermeasures, now mandatory:

- a **connectivity test** (`body_count == 1`, or the expected count) for every
  model — see [03-testing.md](03-testing.md);
- a **visual preview before the final build**, compared against the sketch —
  see [04-verification-workflow.md](04-verification-workflow.md).

## 2. The human gate catches what the machine cannot

The disconnection above was caught **visually by the owner**, not by tests or
the agent. Twice in one part (disconnected legs, unusable hero render) the
human review was the only effective gate. Never treat a green suite as
acceptance; the review step is where the part actually gets judged.

## 3. Assumed dimensions from a sketch are the biggest error source

Every reading of a hand sketch is an interpretation. The rectangular pocket
orientation was read wrong once and corrected in a later round. Rule: state
every interpretation as an **explicit, veto-friendly assumption** (one-parameter
change if vetoed) instead of silently picking one. Ambiguity is a review
problem, not a modeling problem — surface it at the approval gate.

## 4. Rib height = resting depth

A cheap "low cross" (5–10 mm ribs at the bottom of deep pockets) was rejected:
the part rests on the ribs, so rib height defines how deep an item sits. In
shallow pockets a low cross turns a 15 mm pocket into a ~25–30 mm one. Model
the *function*, not just the shape.

## 5. Ribs need embed into walls

Ribs ending exactly at a wall face produce a tangent, fragile union. Each rib
end is embedded ~2 mm into the wall (`rib_embed`) for a solid connection —
this is also what interacts with the connectivity lesson above.

## 6. Know your renderer's failure modes

The matplotlib preview renderer has **depth-sorting artifacts**: top/bottom
views are reliable, iso/side are not, and a staged "hero" scene was rejected as
unusable. Rules:

- judge geometry from top/bottom views plus measured probes, never from an
  iso render alone;
- presentation-quality rendering is a **separate pipeline**, not something to
  bolt onto the preview step — this is now solved: a headless Blender Cycles
  renderer ([tools/render_blender.py](../tools/render_blender.py)) produces
  the presentation images from the verified STL, while matplotlib stays the
  quick preview tool.

## 6b. Verify geometry by measurement, not by eye

When a render "looked mirrored", ray-probing the STL against the spec showed
the model was exactly right — the camera roll was wrong. Judge the *model* by
measured probes and the *render* by camera conventions; never conclude the
geometry is wrong from a single suspicious image. The Blender renderer
documents its camera gotchas (top-view roll degeneration, deterministic
look-at) in [tools/README-render_blender.md](../tools/README-render_blender.md).

## 7. Printability is a spec-level concern (FDM/PLA)

Checked during M3 and recorded in the verification report:

- tall ribs print as vertical walls — no bridging needed for the ribs;
- pocket floors above open quarters bridge only between ribs, largest gap
  ~17 mm — printable in PLA/PETG;
- **hole diameters shrink ~0.1–0.2 mm on FDM** — compensate in the spec when a
  tight fit matters.

## 8. Anonymization before push is part of the workflow

Before pushing to a public repository, a privacy scan replaces personal names
and contacts (contributor names, emails, commit messages). Doing it as a
pre-push step — not as a later cleanup — keeps the public history clean from
the first commit. See [01-workflow.md](01-workflow.md), Git discipline.

## 9. Every spec feature must appear in the drawing

The M4 dimensioned drawing omitted the X-web ribs entirely — the generator
had no `x_fill` logic, and the drawing review checked dimensions, not
feature completeness. The owner caught it. The model itself was correct
(probe-verified); the *review artifact* was incomplete. Rules:

- the drawing must show every feature the spec defines (fill, ribs,
  holes...) or explicitly note what it does not render;
- drawing review = dimensions AND feature completeness, checked against the
  spec's feature list — not against memory of the sketch.

## Meta-lesson: correction rounds are cheap when the spec is the truth

M3 went through three correction rounds (pocket re-read, leg placement, rib
direction) with zero re-modeling cost, because every change was a parameter or
flag in `spec.yaml` and the tests re-verified automatically. This is the payoff
of spec-driven modeling: iterate on the spec, not on the geometry.
