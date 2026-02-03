## AI-Assisted Workflow

Můj přístup k experimentování kombinuje lidský záměr a rychlost generativní AI. Tento proces nejčastěji využívám v `sandbox/` pro rychlé prototypování:

1.  **Záměr a vstup:** Slovně definuji tvar a technické parametry, případně modelu poskytnu jednoduchý nákres či výkres.
2.  **AI Generování:** Nechám LLM připravit základní skript v build123d. Generování kódu je pro AI mnohem přirozenější a přesnější než snaha suplovat vizuální klikání v GUI.
3.  **Okamžitá validace:** Díky **OCP CAD Vieweru** ve VS Code vidím geometrii okamžitě po spuštění skriptu.
4.  **Iterace a Export:** Rychle doladím detaily (např. tolerance, sražení hran) a jakmile model sedí, skript automaticky vygeneruje finální STL pro 3D tisk.

## Nástroje pro AI asistenci (Experimentální)

Sleduji možnosti, jak zapojit AI agenty přímo do procesu tvorby. Zajímavým kandidátem je **[VibeCAD](https://github.com/rawwerks/vibecad)** (dostupný na [MCP Market](https://mcpmarket.com/tools/skills/build123d-cad-modeling)).

Tato sada nástrojů umožňuje Claudovi vystupovat v roli **strojního inženýra** se specializovanou znalostí build123d. Cílem je zrychlit "rapid prototyping" díky těmto schopnostem:

- **Pokročilá geometrie:** Tvorba složitých 3D těles, booleovské operace a parametrické sestavy (bez složitého nastavování díky `uv`).
- **Průmyslové exporty:** Generování výstupů přímo do formátů STEP, STL a GLB.
- **Specializované knihovny:** Přímé využití hotových modulů pro ozubená kola, závity a spojovací materiál.

*Poznámka: Jde o externí tooling třetí strany, který zatím pouze mapuji pro budoucí integraci do workflow.*