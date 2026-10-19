# CAD Workshop

Headless parametric CAD workspace: models are built from written specs, verified by automated tests, and reviewed through generated previews. Built on [build123d](https://github.com/gumyr/build123d) (Python + OpenCascade), designed for AI-assisted modeling where the machine — not memory — proves correctness.

## Why code-first, headless

- **Code is the single source of truth.** Every model is a readable, versioned Python script. Geometry changes are diffs, not redraws.
- **Verification over confidence.** Dimensions, volumes, topology and export integrity are checked by automated tests. A model is "done" when the tests pass, not when it looks plausible.
- **No GUI required.** Modeling, testing, export and preview rendering all run headless. Interactive viewers are optional, never a dependency.

## The core loop

```text
spec (approved dimensions) → model (build123d) → tests (pytest) → previews (PNG) → human review
```

1. A drawing or sketch is transcribed into a machine-readable `spec.yaml` and **approved by a human** before any modeling starts.
2. The model script reads parameters from the spec — never from memory or hard-coded magic numbers.
3. Tests assert every dimension in the spec against the measured geometry, and a completeness check ensures no dimension is silently untested.
4. Headless previews are rendered for visual review; a verification report compares drawing dimensions to measured values.
5. Changes are reviewed as diffs and merged only after CI and human approval.

Details: [docs/01-workflow.md](docs/01-workflow.md), [docs/04-verification-workflow.md](docs/04-verification-workflow.md).

## Repository map

```text
cad-workshop/
├── README.md            # this file
├── docs/                # workflow, environment, testing, verification, modeling rules
│   └── legacy/          # original study notes (preserved, superseded)
├── specs/               # one folder per part: drawing, spec.yaml, verification report
├── models/              # build123d model scripts (read spec.yaml)
├── tests/               # pytest suite: dimension, topology, validity, export checks
├── examples/            # small scripts demonstrating specific build123d features
└── exports/             # generated output (STEP/STL/PNG), not versioned
```

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest                # run the verification suite
```

Environment details: [docs/02-environment.md](docs/02-environment.md).

## Continuous integration

Every push runs the full test suite on GitHub Actions. CI is the single source of truth for code correctness; visual correctness is judged by a human against the original drawing. See [docs/03-testing.md](docs/03-testing.md).

## Status

Early stage. The first verified model is being built to prove the loop end-to-end before more parts are added.

## License

MIT — see [LICENSE](LICENSE).
