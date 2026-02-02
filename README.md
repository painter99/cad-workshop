# CAD Workshop

Experimentování s parametrickým CAD přes Python a **build123d** (CAD‑as‑code nad OpenCascade). Repo je vedené **code‑first**: zdroj pravdy je kód, exporty (STL, obrázky) jsou jen výstupy.

## Oficiální zdroje (build123d)

- Dokumentace: https://build123d.readthedocs.io/en/latest/
- Upstream GitHub: https://github.com/gumyr/build123d

Z oficiálního “About” vyplývá, že build123d je Python‑based parametrický **BREP** modelovací framework postavený na **OpenCascade**, s důrazem na čisté „Pythonic“ API, čitelné CAD‑as‑code workflow a exporty pro výrobu (např. STL/STEP).

## Struktura repozitáře

- **[`docs/cz/`](docs/cz/)** – moje poznámky (CZ)
- **[`docs/images/`](docs/images/)** – screenshoty a obrázky do dokumentace
- **[`examples/`](examples/)** – menší, čisté ukázky
- **[`exports/stl/`](exports/stl/)** – exportované STL soubory (artefakty)
- **[`sandbox/`](sandbox/)** – rychlé experimenty a rozpracované skripty (aktuálně zde mám 2 Python soubory)

## Nástroje / workflow

- Python 3.x
- build123d + OpenCascade
- VS Code + **OCP viewer** (rychlý náhled modelů při iteraci)

## Poznámky k obsahu

Tento repozitář je osobní workshop. V `sandbox/` můžou být věci „neuklizené“ nebo ve stavu pokus/omyl. Pokud něco začnu používat opakovaně nebo to bude dobrý příklad, přesunu to do `examples/` a doplním k tomu krátké vysvětlení do `docs/cz/`.