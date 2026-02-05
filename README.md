# CAD Workshop

Experimentování s parametrickým CAD přes Python a **build123d**. Toto repo je vedené filosofií **code‑first**: zdrojem pravdy je kód, exporty jsou pouze výstupy.

## Proč build123d (motivace a cíle)

Tento workshop vznikl z kombinace praktické potřeby a chuti učit se věci „správně“. Můj přechod od klasického klikání v GUI k Pythonu má několik důvodů:

- **Efektivita a rychlost (AI Synergy):** U mnoha tvarů mi stačí popsat záměr přirozeným jazykem AI modelu, nechat vygenerovat základ kódu a ten následně iteračně ladit. Tento proces je pro mě u mnoha dílů řádově rychlejší a méně namáhavý než manuální kreslení ve [FreeCADu](https://www.freecad.org/index.php?lang=cs). Tento proces popisuji detailněji v sekci [ai-assisted-workflow](docs/cz/ai-assisted-workflow.md).

- **Python synergie:** Protože Python používám ve svém hlavním projektu [ai-workshop](https://github.com/painter99/ai-workshop), dává mi smysl využít stejný jazyk i pro CAD modelování. Je to ideální cesta, jak spojit programování s něčím hmatatelným.
- **Kód jako „Single Source of Truth“:**
  - **Verzování:** V Gitu přesně vidím evoluci modelu a historii změn.
  - **Parametrizace:** Změna rozměrů je otázkou úpravy proměnné, nikoliv překreslování modelu.
  - **Automatizace:** Možnost skriptovat exporty a generovat varianty bez otevírání editoru.

Použití **BREP** (OpenCascade) pod kapotou znamená přesné inženýrské CAD workflow.

## Struktura a navigace

- 📂 **[docs/](docs/)** – Dokumentace, metodika, AI workflow a vizuální výstupy.
- 📂 **[examples/](examples/)** – Izolované, čisté ukázky konkrétních funkcí.
- 📂 **[projects/](projects/)** – Komplexnější modely a sestavy (assemblies).
- 📂 **[sandbox/](sandbox/)** – "Pískoviště" pro rychlé experimenty.
- 📂 **[exports/](exports/)** – Výstupní soubory (STL, STEP).

## Nástroje a technologie

- **Jazyk:** Python 3.x
- **Jádro:** build123d
- **Editor:** VS Code + **OCP CAD Viewer** (nezbytné pro live náhled kódu)
- **AI Asistence:** Využití LLMs pro generování a iteraci prototypového CAD kódu

---
*Tento repozitář je osobní workshop pro CAD modelování postavený na: [build123d.readthedocs.io](https://build123d.readthedocs.io/en/latest/), [gumyr/build123d](https://github.com/gumyr/build123d)*
