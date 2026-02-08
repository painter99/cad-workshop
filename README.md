# CAD Workshop

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Build123d](https://img.shields.io/badge/build123d-0.10.0-orange.svg)](https://build123d.readthedocs.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Parametrické CAD modelování v Pythonu | Code‑first přístup**

> Osobní pracovna pro experimenty s frameworkem **build123d**. 
> Kód zde není jen nástroj, ale **zdroj pravdy** — exporty jsou pouze vygenerované výstupy.

## Proč modelovat kódem (motivace a cíle)

Tento workshop jsem vytvořil z praktické potřeby přechodu od klasického klikacího CADu z těchto důvodů:

### 1. Rychlost návrhu díky AI
Pro mnoho dílů stačí popsat záměr přirozeným jazykem, nechat vygenerovat kostru kódu a iterativně dolaďovat. U mnoha dílů je tento proces řádově rychlejší než manuální kreslení.

📖 Popis workflow: [AI Assisted Workflow](docs/cz/ai-assisted-workflow.md)  
📋 Praktické tipy a cheat sheet: [Best Practices](docs/cz/best-practices.md)

### 2. Python ekosystém
- Protože Python používám ve svém hlavním projektu [ai-workshop](https://github.com/painter99/ai-workshop), dává mi smysl využít stejný jazyk i pro CAD modelování. Je to ideální cesta, jak spojit programování s něčím hmatatelným.

### 3. CAD-as-code: Kód jako jediný zdroj pravdy
  - **Verzování:** V Gitu přesně vidím evoluci modelu a historii změn.
  - **Parametrizace:** Změna rozměrů je otázkou úpravy proměnné, nikoliv překreslování modelu.
  - **Automatizace:** Možnost skriptovat exporty a generovat varianty bez otevírání editoru.
  - **Testování:** Automatické ověření rozměrů, objemu nebo kolizí pomocí jednoduchých skriptů.
  - **Udržovatelnost**: Díky logické struktuře je model srozumitelný a snadno upravitelný i po delší pauze.


## Struktura a navigace

- 📂 **[docs/](docs/)** – Dokumentace, metodika, AI workflow a vizuální výstupy.
- 📂 **[examples/](examples/)** – Izolované, čisté ukázky konkrétních funkcí.
- 📂 **[projects/](projects/)** – Komplexnější modely a sestavy (assemblies).
- 📂 **[sandbox/](sandbox/)** – "Pískoviště" pro rychlé experimenty.
- 📂 **[exports/](exports/)** – Výstupní soubory (STL, STEP).

## Nástroje a technologie

Jádrem je **BREP** (Boundary Representation) workflow postavené na OpenCascade, což zaručuje matematickou přesnost na rozdíl od meshových modelářů.

| Kategorie | Nástroj |
|-----------|---------|
| **Jazyk** | Python 3.10+ |
| **Framework** | [build123d](https://github.com/gumyr/build123d) |
| **Editor** | VS Code |
| **AI** | LLMs (např. t3.chat) jako "pair-programmer" pro prototypování |

---

*Tento repozitář slouží jako studijní materiál a osobní archiv. Postaveno na skvělé práci komunity kolem [build123d docs](https://build123d.readthedocs.io).*