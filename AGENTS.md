# AGENTS.md

Standing instructions for AI coding agents working in this repository.
`README.md` is written for humans; this file is the agent-facing entry point.
It follows the cross-tool [AGENTS.md](https://agents.md) convention.

## Precedence rule (read first)

If any instruction in this file or in `docs/` conflicts with the observed
state of the repository (actual files, actual test results, actual git
history), verify the observed state first and prefer it; report the conflict
instead of silently following either source. Stale instructions are a known
failure mode for coding agents.

## What this repository is

A headless, spec-driven CAD framework: parts are built from written,
human-approved specs, verified by automated tests, and accepted only by a
human. Built on [build123d](https://github.com/gumyr/build123d)
(Python + OpenCascade). The machine proves correctness; the human judges
appearance and intent. There is no GUI dependency and no container.

Entry points, in reading order:

1. [docs/01-workflow.md](docs/01-workflow.md) — the normative loop: spec → model → drawing →
   tests → previews → human acceptance.
2. [docs/07-new-part-checklist.md](docs/07-new-part-checklist.md) — the step-by-step procedure for adding
   a part; follow it top to bottom.
3. [docs/06-lessons-learned.md](docs/06-lessons-learned.md) — the catalog of observed failure modes;
   treat it as binding working rules, not anecdotes.

The repository-independent, agent-side version of the procedure is maintained
as the Skill `cad-spec-driven-workflow` in
[agora-pro-setup](https://github.com/painter99/agora-pro-setup) (the pattern
itself is docs/26 there). That Skill governs the workflow anywhere; this file
governs work inside this repository.

## Repository map

- `docs/` — numbered working documents (01 workflow, 02 environment,
  03 testing, 04 verification, 05 modeling rules, 06 lessons learned,
  07 new-part checklist, 08 roadmap); `docs/legacy/` is preserved,
  superseded study notes.
- `schemas/spec.schema.json` — JSON Schema contract for every `spec.yaml`.
- `specs/<part>/` — one folder per part: `spec.yaml`, `verification.md`,
  previews, visuals.
- `models/` — build123d model scripts; each exposes `build(spec)` and reads
  every parameter from the spec.
- `tests/` — pytest suite: dimensions, topology, validity, export
  round-trip, drawing completeness.
- `tools/` — spec validation, preview rendering, drawing generation,
  Blender render pipeline (`tools/README-render_blender.md`).
- `exports/` — generated output (STEP/STL/PNG); rebuilt by the tools, never
  versioned.

Search with `grep -rn` instead of reading directories file by file. Do not
use web search for repository-internal questions — read the repository;
web search is for build123d/OCCT behavior and external standards.

## Binding rules (the invariants of the loop)

1. **The spec is the only source of truth.** Model scripts read parameters
   from `specs/<part>/spec.yaml`; never hard-code dimensions, never rely on
   remembered values.
2. **A human approves the spec before modeling starts.** Never modify an
   approved spec without explicit owner approval. Transcribe ambiguity as an
   explicit, veto-friendly assumption (`uncertain: true`), never as a guess.
3. **Drawing views come from the model; annotations come from the spec.**
   Never hand-draw or duplicate geometry in a renderer (background: docs/06,
   the geometry-duplication lesson).
4. **Every spec dimension gets an assertion, and a completeness test fails
   if any dimension has none.** Include the mandatory connectivity test —
   per-dimension tests cannot see disconnected bodies (background: docs/06,
   the connectivity lesson).
5. **Verify every build123d API call against the installed version**
   (`help()`, `inspect.signature`, or that version's documentation) — never
   from memory; record surprises in docs/06.
6. **Nothing is done on confidence.** A part is done when the suite is
   green, CI is green, and a human has accepted it (recorded in
   `specs/<part>/verification.md`).

## Conventions

- **Environment.** Python venv at `.venv`; the build123d version is pinned
  in `requirements.txt` — do not upgrade casually, the drawing stack depends
  on exact behavior. Details: docs/02. Presentation renders use the
  standalone Blender pipeline
  ([tools/README-render_blender.md](tools/README-render_blender.md)).
- **Validation gate.** `python tools/validate_spec.py` and then `pytest`
  must pass before any commit; CI runs the same on every push to `main`
  (docs-only changes are excluded via `paths-ignore`).
- **Language and privacy.** Repository content is English, anonymized and
  generic: no personal names, contacts, workshop photos, or sketches of
  private parts. The sole exception is the `LICENSE` copyright line. Before
  every push to the public remote, run a personal-identifier grep over the
  changed files (procedure: docs/07, the privacy step; anonymization is part
  of the workflow, docs/06, the anonymization lesson).
- **Git discipline.** Work on a topic branch (`<topic>-YYYYMMDD`); show the
  diff stat before committing; every push and every merge to `main` requires
  explicit owner approval; merges are `--no-ff` (docs/01, Git discipline).
- **Docs numbering.** Never renumber existing documents; a new document
  takes the next free number.

## Boundaries

Do not modify without explicit owner approval:

- an approved `specs/<part>/spec.yaml` — the human-approved source of truth;
  propose the change, never apply it silently;
- `LICENSE` — the copyright line names the owner; never "correct" it to an
  anonymized value;
- generated visuals under `specs/<part>/visuals/` — appearance is judged by
  the owner;
- `docs/legacy/` — preserved history, superseded; do not modernize it.

## Definition of done

A change is done when: the validation gate passes locally; affected
cross-references and checklist steps are updated in the same change; the
diff is minimal — findings outside the task scope are reported, not silently
fixed and not silently dropped; and after a merge to `main`, CI is green or
provably absent (docs-only under `paths-ignore`).

## Last verified

2026-10-28 against `main`. If this file is older than recent merges,
re-verify its claims (file map, commands, conventions) before relying on
them.