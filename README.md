# CAD Workshop

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Build123d](https://img.shields.io/badge/build123d-0.10.0-orange.svg)](https://build123d.readthedocs.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Parametrické CAD modelování v Pythonu | Code‑first přístup

> Osobní pracovna pro experimenty s frameworkem **build123d**.
> Místo manuálního kreslení se definují tvary pomocí kódu.

## Účel a obsah

Tento repozitář slouží jako **kolekce návodů, best practices a experimentů**. Jde o živou znalostní bázi pro práci s frameworkem build123d, kde shromažďuji funkční kódy, exporty a metodiku pro efektivní učení principů "CAD-as-code" s podporou AI.

Detailní popis mého workflow a technické poznámky jsem shrnul do samostatného dokumentu:

👉 **[Metodika, Best Practices & AI Workflow](docs/cz/best-practices.md)**

## Struktura repozitáře

- 📂 **[docs/](docs/)** – Dokumentace, metodika, vizuální výstupy a poznámky.
- 📂 **[examples/](examples/)** – **Ukázky.** Jednoduché skripty demonstrující konkrétní funkce.
- 📂 **[projects/](projects/)** – **Reálné modely.** Komplexnější sestavy a hotové díly.
- 📂 **[sandbox/](sandbox/)** – Prostor pro rychlé experimenty a prototypy.
- 📂 **[exports/](exports/)** – Vygenerované výstupy (STL pro 3D tisk, STEP pro CNC).

## Nástroje a technologie

Jádrem je **BREP** (Boundary Representation) workflow postavené na OpenCascade, což zaručuje matematickou přesnost geometrie.

| Kategorie      | Nástroj                                                       |
| -------------- | ------------------------------------------------------------- |
| **Jazyk**      | Python 3.10+                                                  |
| **Framework**  | [build123d](https://github.com/gumyr/build123d)               |
| **Editor**     | VS Code + OCP CAD Viewer                                      |
| **AI Support** | LLMs (např. t3.chat) jako "pair-programmer" pro prototypování |

---

_Tento repozitář slouží jako studijní materiál a osobní archiv. Postaveno na skvělé práci komunity kolem [build123d docs](https://build123d.readthedocs.io)._
