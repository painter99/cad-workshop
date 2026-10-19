# Environment

## Requirements

- Python 3.10–3.13
- No display, no GUI toolkit, no containers. Everything runs headless.

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
| matplotlib | headless preview rendering |
| pytest | test runner |
| pyyaml | spec file parsing |

## Sanity check

```bash
python -c "from build123d import Box; b = Box(1, 2, 3); print(b.volume)"
```

Expected output: `6.0` (approximately; exact BREP volume of an axis-aligned 1×2×3 box).

## Running the loop locally

```bash
pytest                      # full suite: geometry tests + preview generation
pytest tests/test_<part>.py # single part
```

Previews land in `exports/` and are not versioned (see `.gitignore`).

## Versioning note

The build123d API changes between minor versions. Model code targets the pinned range in `requirements.txt`; when upgrading, re-run the full test suite — the tests, not memory, decide whether the models still hold.
