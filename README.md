# CAD Workshop

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Build123d](https://img.shields.io/badge/build123d-0.10.0-orange.svg)](https://build123d.readthedocs.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Parametrické CAD modelování v Pythonu | Code‑first přístup**

> Osobní pracovna pro experimenty s frameworkem **build123d**. 
> Místo manuálního kreslení zde definuji tvary pomocí kódu, který slouží jako jediný zdroj pravdy.

## O projektu

Tento repozitář vznikl z potřeby opustit limity klasického "klikacího" CADu. Cílem je využít sílu Pythonu a AI k tvorbě modelů, které jsou plně parametrické, snadno verzovatelné v Gitu a automatizovatelné. Exporty do STL nebo STEP jsou zde chápány pouze jako vedlejší produkt kompilace, nikoliv jako zdrojová data.

Detailní popis mého workflow, včetně zapojení umělé inteligence do procesu návrhu, jsem shrnul do samostatného dokumentu:

👉 **[Metodika, Best Practices & AI Workflow](docs/cz/best-practices.md)**

## Struktura repozitáře

- 📂 **[docs/](docs/)** – Dokumentace, metodika, vizuální výstupy a poznámky.
- 📂 **[examples/](examples/)** – **Ukázky.** Jednoduché skripty demonstrující konkrétní funkce.
- 📂 **[projects/](projects/)** – **Reálné modely.** Komplexnější sestavy a hotové díly.
- 📂 **[sandbox/](sandbox/)** – Prostor pro rychlé experimenty a prototypy.
- 📂 **[exports/](exports/)** – Vygenerované výstupy (STL pro 3D tisk, STEP pro CNC).

## Nástroje a technologie

Jádrem je **BREP** (Boundary Representation) workflow postavené na OpenCascade, což zaručuje matematickou přesnost geometrie.

| Kategorie | Nástroj |
|-----------|---------|
| **Jazyk** | Python 3.10+ |
| **Framework** | [build123d](https://github.com/gumyr/build123d) |
| **Editor** | VS Code + OCP CAD Viewer |
| **AI Support** | LLMs (např. t3.chat) jako "pair-programmer" pro prototypování |

---

*Tento repozitář slouží jako studijní materiál a osobní archiv. Postaveno na skvělé práci komunity kolem [build123d docs](https://build123d.readthedocs.io).*
