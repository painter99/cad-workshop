# Environment

## Requirements

- Python 3.10–3.13
- Runs headless: no display or GUI toolkit is required; interactive viewers are optional, never a dependency. No containers.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Installed packages:

| Package | Role |
|---|---|
| build123d | parametric BREP modeling on OpenCascade |
| trimesh | mesh loading and geometry checks |
| matplotlib | headless preview rendering and dimensioned drawing generation |
| pytest | test runner |
| pyyaml | spec file parsing |
| jsonschema | spec structural validation (schemas/spec.schema.json) |

## Sanity check

```bash
python -c "from build123d import Box; b = Box(1, 2, 3); print(b.volume)"
```

Expected output: `6.0` (approximately; exact BREP volume of an axis-aligned 1×2×3 box).

## Running the loop locally

```bash
python tools/validate_spec.py # structural spec check (also a CI step)
pytest                      # full suite: geometry tests + preview generation
pytest tests/test_<part>.py # single part
```

Previews land in `exports/` and are not versioned (see `.gitignore`).

## Presentation rendering (Blender, optional)

The quick matplotlib previews are for the verification loop. Presentation
images use a separate headless Blender Cycles pipeline — Blender is a
standalone download, deliberately not a pip dependency:

```bash
blender --background --python tools/render_blender.py -- \
    exports/<part>.stl specs/<part>/visuals iso,top,front,side
```

Details and camera conventions: [tools/README-render_blender.md](../tools/README-render_blender.md).

## Versioning note

The build123d API changes between minor versions. Model code targets the pinned version in `requirements.txt`; when upgrading, re-run the full test suite — the tests, not memory, decide whether the models still hold.
