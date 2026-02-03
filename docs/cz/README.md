# Dokumentace a metodika

V této sekci popisuji své postupy, poznámky k frameworku a způsoby, jak zefektivnit CAD modelování pomocí moderních nástrojů.

## AI-Assisted Workflow

Můj přístup k experimentování kombinuje lidský záměr a efektivitu AI:

1.  **Nápad a popis:** Slovně definuji tvar a technické parametry (např. "potřebuji držák na zeď pro router, vnitřní rozměry X, otvory pro šrouby Y").
2.  **AI Iterace:** LLM připraví základní skript v build123d. Kód je pro AI mnohem srozumitelnější formát než binární soubory GUI editorů.
3.  **Okamžitá validace:** Pomocí **OCP CAD Vieweru** vidím výsledek okamžitě po uložení souboru.
4.  **Ladění:** Manuálně doupravím detaily nebo požádám AI o refaktoring (např. "přidej zaoblení hran 2mm na všech vnějších rozích").

Tento cyklus mi umožňuje vytvořit hotový díl v čase, který bych jinak strávil jen nastavováním náčrtů ve FreeCADu.
