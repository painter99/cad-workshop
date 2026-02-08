# build123d – Osobní Poznámky & Best Practices Cheat Sheet

Tyto poznámky jsou moje shrnutí při studiu build123d. **Nejde o oficiální dokumentaci!**

Rychlá definice (ať je jasné, o čem mluvím):

- build123d je parametrický CAD framework v Pythonu pro 2D/3D modelování.
- Je postavený na BREP přístupu (Boundary Representation) a běží nad OCCT (Open Cascade).
- BREP = definice geometrie pomocí přesných matematických ploch, ne aproximací trojúhelníky (na rozdíl od mesh-modelářů typu OpenSCAD)
- Cíl: „CAD-as-code“ — čitelnost, udržovatelnost, parametrizace, možnost testů a automatizace.

Zdroje (upstream):

- build123d docs (hlavní rozcestník): <https://build123d.readthedocs.io/en/latest/>
- build123d GitHub: <https://github.com/gumyr/build123d>

Testováno s:

- build123d: `0.10.0`
- Python: `3.13.11`

---

## Obsah

- [0) Quick start](#0-quick-start-instalace--základní-setup)
- [1) Kontext: proč CAD-as-code](#1-kontext-proč-cad-as-code)
- [2) Builder vs Algebra](#2-dva-režimy-modelování-builder-vs-algebra)
- [3) Topologie](#3-topologie-jak-build123d-vidí-těleso)
- [4) Selectors](#4-selectors-robustní-výběr-prvků-praktické-poznámky)
- [5) Best practices](#5-best-practices-pro-robustní-modely)
- [6) Sestavy a mechanismy](#6-sestavy-a-mechanismy)
- [7) Export a Ekosystém](#7-export-a-ekosystém)
- [8) Struktura projektu](#8-struktura-projektu-pro-verzování)
- [9) AI-Assisted Workflow a Nástroje](#9-ai-assisted-workflow-a-nástroje)
- [10) Compatibility / Verze](#10-compatibility--verze-krátce)

---

## 0) Quick start (instalace + základní setup)

### Požadavky

- Python 3.10–3.13 (dle aktuální dokumentace)
- VS Code (doporučený editor pro integraci s OCP CAD Viewer)

### Instalace

Pro správné fungování postupuj podle těchto kroků:

#### 1. Rozšíření pro VS Code

Otevři příkazovou paletu (Ctrl+P) a postupně vlož a potvrď tyto příkazy:

```bash
ext install bernhard-42.ocp-cad-viewer
ext install ms-python.python
```

#### 2. Nastavení prostředí a instalace knihoven

V terminálu v adresáři projektu:

```bash
# Vytvoření virtuálního prostředí
python -m venv .venv

# Aktivace prostředí podle OS:
# pro Windows
.venv\Scripts\activate

# pro Linux/macOS
source .venv/bin/activate

# Aktualizace pip a instalace CAD knihoven
pip install --upgrade pip
pip install build123d ocp-vscode
```

#### 3. Ověření funkčnosti (Sanity Check)

Vytvoř soubor `test.py`, vlož do něj následující kód a spusť jej.

```python
from build123d import *
from ocp_vscode import show

# 1. Vytvoření geometrie (Algebra mód)
box = Box(1, 2, 3)

# 2. Sanity check: Výpis topologické struktury do konzole
print(box.show_topology(limit_class="Face"))

# 3. Zobrazení v OCP Vieweru
# Bez tohoto příkazu kód proběhne, ale okno prohlížeče zůstane prázdné
show(box, names=["sanity_box"])
```

Co by se mělo stát:

- V terminálu vidím textový výpis ploch (Faces) mého boxu.
- V pravém panelu VS Code se automaticky otevře okno **OCP CAD Viewer** s 3D modelem.

> **Tip na setup:** Na začátku každého souboru si dávám blok parametrů (hlavní rozměry, jednotky, tolerance).
> Změny jsou pak „jedním místem“ a model se lépe refaktoruje.

---

## 1) Kontext: proč CAD-as-code

### Motivace a cíle

Tento přístup jsem zvolil z praktické potřeby přechodu od klasického klikacího CADu z těchto důvodů:

1. **Rychlost návrhu díky AI:** Pro mnoho dílů stačí popsat záměr přirozeným jazykem, nechat vygenerovat kostru kódu a iterativně dolaďovat. U mnoha dílů je tento proces řádově rychlejší než manuální kreslení.
2. **Python a hmatatelný výsledek:** Spojení programovacího jazyka s CAD modelováním představuje přirozený most mezi světem logiky a fyzické tvorby. Kód zde přestává být jen abstraktním zápisem na obrazovce a stává se „stavebním materiálem“, který přímo definuje prostor a tvar. Kombinace programování a konstruování dává psaní skriptů hlubší praktický rozměr – každá změna v algoritmu má okamžitý a viditelný dopad, který lze následně převést do reálného objektu. Pro začínající tvůrce i zkušené inženýry to může být přirozený způsob, jak propojit digitální návrh s fyzickým výsledkem.
3. **Kód jako jediný zdroj pravdy:**
   - **Verzování:** V Gitu přesně vidím evoluci modelu a historii změn (rozdíly v kódu, ne v binárních souborech).
   - **Parametrizace:** Změna rozměrů je otázkou úpravy proměnné, nikoliv překreslování modelu.
   - **Automatizace:** Možnost skriptovat exporty a generovat varianty bez otevírání editoru.
   - **Testování:** Automatické ověření rozměrů, objemu nebo kolizí pomocí jednoduchých skriptů.
   - **Udržovatelnost:** Díky logické struktuře je model srozumitelný a snadno upravitelný i po delší pauze.

### Shrnutí benefitů

Co mi CAD-as-code dává:

- verzování modelu v Gitu
- hromadná automatizace (generování variant z parametrů)
- testovatelnost (rozměry, clearance, pravidla)
- precizní topologická kontrola (programatický přístup k hranám/plochám)

Co si hlídat:

- „kód je model“ → **čitelnost je stejně důležitá jako správná geometrie**
- při refaktoringu je snadné rozbít selekce (selectors) a navazující operace
- používej type hints a PEP 8 — chyby v logice modelu odhalíš v IDE, ne při renderování

---

## 2) Dva režimy modelování: Builder vs Algebra

### Builder mode (stavový, kontextový)

Typicky:

- `with BuildPart() as p: ...`
- `with BuildSketch(): ...`
- `with BuildLine(): ...`

Kdy ho použít:

- když chci jasnou hierarchii (skica → těleso → features)
- když mám hodně podmínek/smyček a chci mít „CAD historii“ čitelnou v kódu
- **debugging**: můžu vložit `print()` nebo `breakpoint` kamkoliv do procesu

Můj mentální model:

- „průběžný součet“ — operace uvnitř bloku mění aktuální geometrii

Mini ukázka (2D → extrude → cut na top face):

```python
from build123d import *
from ocp_vscode import show

# Definice parametrů (Best Practice)
L, W, T = 20, 20, 10
HOLE_R = 5
FILLET_R = 3

with BuildPart() as p:
    # 1. Základní profil s fillet ve 2D (stabilnější než 3D)
    with BuildSketch() as s:
        Rectangle(L, W)
        # Zaoblení všech vrcholů (vertices) v aktuální skice
        fillet(s.vertices(), radius=FILLET_R)
    extrude(amount=T)

    # 2. Výběr horní plochy pro novou skicu
    top_face = p.faces().sort_by(Axis.Z).last
    with BuildSketch(top_face):
        Circle(HOLE_R)
    extrude(amount=-T/2, mode=Mode.SUBTRACT)

show(p.part)
```

### Algebra mode (bezstavový, operátorový)

Princip:

- objekty jsou proměnné
- kombinuji je přes operátory (union/cut/intersect) a transformace

Základní operátory:

- `+` union (sjednocení)
- `-` cut (odečet)
- `&` intersect (průnik)
- `*` transformace (typicky `Location` / `Pos` / `Rot`)

**Performance Tip (Vektorizace):**  
Operace v Algebra módu jsou vektorizované. Zápis `part -= [list_of_holes]` je **výrazně efektivnější** než postupné odečítání v cyklu, protože OCCT provede fúzi nástrojů v jednom kroku.

Ukázka (geometrické rovnice + transformace):

```python
from build123d import *
from ocp_vscode import show

# Základní boolean operace
part = Box(1, 2, 3) - Cylinder(0.2, 5)

# Umístění/rotace (řetězení transformací)
part = Plane.XZ * Pos(1, 2, 3) * Rot(0, 100, 45) * Box(1, 2, 3)
show(part)
```

**Dodatek — práce s křivkami (snapping / navazování):**

```python
# Edge/Wire operátory (Algebra mode)
pos_vec = curve @ 0.5   # Vector: pozice na křivce (0.0 až 1.0)
tangent = curve % 0.5   # Vector: tečna ve stejném bodě
loc = curve ^ 0.5       # Location: umístění v bodě (pro placement)
```

> **Poznámka:** V praxi se dají kombinovat oba přístupy — to je jedna z výhod build123d.
> Můžeš začít v Builder módu a výsledek předat do Algebra operací.

---

## 3) Topologie: jak build123d "vidí" těleso

**Proč na tom záleží:**  
Většina „robustních“ postupů stojí na tom, že umím vybrat správnou plochu/hranu i po změně parametrů. Fixní indexování (`[0]`) selže při změně rozměrů — musím filtrovat podle geometrie.

**Topologická hierarchie (od nejmenšího):**

1. **Vertex** (0D) – bod, definuje konce hran
2. **Edge** (1D) – hrana/křivka (přímka, oblouk, spline), ohraničená vertexy
3. **Wire** – sekvence propojených hran (uzavřená nebo otevřená smyčka)
4. **Face** (2D) – plocha ohraničená jedním nebo více wires
5. **Shell** – kolekce propojených ploch (otevřený nebo uzavřený objem)
6. **Solid** (3D) – uzavřené, "vodotěsné" těleso
7. **Compound** – kontejner pro seskupení jakýchkoliv prvků

**Poznámka:**  
Většina entit je nějaká varianta `Shape` (společné chování: transformace, export, booleany).

---

## 4) Selectors: robustní výběr prvků (praktické poznámky)

Základ:

- `faces()`, `edges()`, `vertices()` (a často i `solids()`) vrací `ShapeList`
  (list + metody navíc)

**Pokročilé operátory selektorů:**

| Operátor    | Funkce                 | Příklad                                      |
| ----------- | ---------------------- | -------------------------------------------- |
| `>` / `<`   | Třídění (sort_by)      | `faces() > Axis.Z` (nejvyšší plocha)         |
| `>>` / `<<` | Seskupení (group_by)   | `edges() >> Axis.X` (poslední skupina)       |
| `\|`        | Filtrování (filter_by) | `edges() \| GeomType.CIRCLE` (kruhové hrany) |

**Užitečné operace na výběru:**

- `filter_by(...)` – zúžení podle geometrie / orientace / typu
  - typicky osa/směr: např. `filter_by(Axis.Z)`
  - typicky typ geometrie: např. `filter_by(GeomType.CIRCLE)` (kruhové hrany)
- `sort_by(...)` – seřazení a výběr extrému (`[0]`, `[-1]` nebo `.last`)
  - např. `sort_by(Axis.Z).last` → nejvyšší plocha
- **`Select.LAST`**, **`Select.NEW`** (KRITICKÉ pro řetězení operací)
  - `LAST` = „co vzniklo poslední operací“ (např. po `Hole()`)
  - `NEW` = „nově vzniklé prvky“ (po booleanech / průnicích)

**Pro Tip:**  
Po vytvoření otvoru příkazem `Hole()` použij `fillet(model.edges(Select.LAST), 0.5)` k okamžitému zaoblení hran právě vzniklého prvku — **bez nutnosti manuálního vyhledávání**.

**Co si hlídat:**

- vyhýbat se „křehkým“ výběrům typu „vezmi první hranu“ bez kontextu
- raději filtrovat podle směru, polohy, typu geometrie, případně kombinovat
- po booleanech často dává smysl pracovat s `Select.LAST` / `Select.NEW`

**Mini checklist při ladění selektorů:**

1. Vypsat/zkontrolovat počet prvků (`len(...)`)
2. Zkontrolovat orientaci/umístění (osa, normal, bounding box)
3. Teprve pak aplikovat `fillet/chamfer`

> **Pozor:** `GeomType.CIRCLE` patří typicky na `edges()`, ne na `faces()`.
> Pokud filtruješ plochy, hledej např. `GeomType.PLANE`, `GeomType.CYLINDER`, apod.

**Snippety pro ladění děr (Varianty A/B):**

**Varianta A — chci kruhové hrany:**

```python
from build123d import *
from ocp_vscode import show

# 1. Vytvoření testovacího dílu (předpoklad pro funkčnost)
with BuildPart() as p:
    Box(100, 50, 10)
    with Locations((20, 0, 0), (-20, 0, 0)):
        Cylinder(radius=5, height=20, mode=Mode.SUBTRACT)
part = p.part # Extrakce tělesa z builderu

# 2. Výběr ploch kolmých k ose Z
faces_z = part.faces().filter_by(Axis.Z)
print("Počet ploch na ose Z:", len(faces_z))

# 3. Ladění: Výběr hran typu CIRCLE z těchto ploch
# GeomType.CIRCLE patří hranám (Edge), nikoliv plochám (Face).
top_hole_edges = faces_z.edges().filter_by(GeomType.CIRCLE)
print("Počet nalezených kruhových hran:", len(top_hole_edges))

# 4. Zobrazení v OCP Vieweru (poloprůhledný model + zvýrazněné hrany)
show(part, top_hole_edges, names=["model", "vybrane_hrany"], alphas=[0.5, 1.0])
```

**Varianta B — chci plochy, které obsahují díry (inner wires):**

```python
from build123d import *
from ocp_vscode import show

# 1. Vytvoření testovacího dílu (předpoklad pro funkčnost)
with BuildPart() as p:
    Box(100, 50, 10)
    with Locations((0, 0, 0)):
        Cylinder(radius=10, height=20, mode=Mode.SUBTRACT)
part = p.part

# 2. Výběr ploch kolmých k ose Z
faces_z = part.faces().filter_by(Axis.Z)

# 3. Ladění: Filtrování ploch, které mají vnitřní dráty (díry)
# Lambda funkce vrací True, pokud seznam f.inner_wires() není prázdný.
faces_with_holes = faces_z.filter_by(lambda f: f.inner_wires())
print("Počet ploch s dírami:", len(faces_with_holes))

# 4. Zobrazení výsledku výběru
show(part, faces_with_holes, names=["model", "plochy_s_dirami"], alphas=[0.3, 1.0])
```

> **Tip:** Při ladění selektorů vždy začni `print(len(...))` a když si nejsi jistý,
> rozklikni topologii ve VS Code přes OCP CAD Viewer (interaktivní inspekce).

---

## 5) Best practices pro robustní modely

### 5.1 "2D před 3D" (strategie stability)

**Workflow:**

1. Definice kostry (`BuildLine`)
2. Plocha (`make_face()`)
3. Úprava skici (`BuildSketch`)
4. Transformace (`extrude`, `revolve`, `sweep`, `loft`)

**Proč:**

- 2D operace jsou matematicky stabilnější než 3D booleany
- Přímá manipulace s 3D tělesy (CSG) je v OCCT kernelu výpočetně náročná a náchylná k chybám
- **Fillet a Chamfer ve 2D skice**, kdykoliv je to možné — snižuje riziko selhání při 3D operacích

### 5.2 Parametrizace (žádná magická čísla)

- **Všechny kritické rozměry jako proměnné nahoře**
- Odvozené rozměry počítat z nich (např. `pitch_diameter = module * teeth`)
- Držet jednotky konzistentní (mm vs. m)
- Umožňuje to rychlé iterace a generování variant

```python
# ✅ DOBŘE
WIDTH, HEIGHT, THICKNESS = 100, 50, 10
HOLE_DIAMETER = WIDTH * 0.1

# ❌ ŠPATNĚ
Box(100, 50, 10)  # Co to znamená? Jaké jednotky?
```

### 5.3 Fillet/chamfer až na konec

- Zaoblení/zkosení často rozbije model při změnách
- Když je dělám pozdě, snížím počet "křehkých" závislostí

### 5.4 Workplanes z existující geometrie

- Místo ručního počítání souřadnic raději odvozovat roviny z ploch (`Face`)
- Model se pak „přilepí“ k tvaru a posouvá se s ním

```python
# Práce s horní plochou (automatická detekce)
from build123d import *
from ocp_vscode import show

with BuildPart() as model:
    Box(10, 10, 10)
    # Náčrt se vytvoří přesně na horní ploše krychle
    with BuildSketch(model.faces().sort_by(Axis.Z).last):
        Circle(2)
    extrude(amount=2) # Přidá válec na horní plochu

show(model)
```

---

## 6) Sestavy a mechanismy

### 6.1 Sestavy (Assemblies)

- Sestavy jsou strom (anytree) → transformace rodiče se přenáší na potomky
- **Pro opakující se díly používat `copy()` (mělké kopie), ne `deepcopy()`**
  - Výrazně to šetří paměť a velikost projektu u opakovaných komponentů (šrouby, profily)
  - `deepcopy()` vytváří zcela nezávislá data a dramaticky zvyšuje paměťovou náročnost

### 6.2 Klouby (Joints) - Kinematika

**Unikátní vlastnost build123d.** Definuj „chytré“ body připojení místo manuálního počítání souřadnic.

**Použití:**  
`part_a.joints['J1'].connect_to(part_b.joints['J2'])`  
Metoda `connect_to()` automaticky transformuje objekty tak, aby se klouby srovnaly.

**Typy kloubů:**

- `RigidJoint`: 0 DOF (pevné spojení - šrouby, sváry)
- `RevoluteJoint`: 1 DOF (rotace - panty, hřídele)
- `LinearJoint`: 1 DOF (posun - písty, pojezdy)
- `CylindricalJoint`: 2 DOF (rotace + posun)
- `BallJoint`: 3 DOF (kulový čep)

### 6.3 Umisťování prvků (location contexts) + bulk operace

```python
from build123d import *
from ocp_vscode import show

# 1. Definice parametrů (v dokumentaci zdůrazněno jako Best Practice)
radius, height = 0.5, 2.0

with BuildPart() as p:
    # 2. Vytvoření základního tělesa
    Box(10, 10, 2)

    # 3. Zachycení lokací pomocí "as locs" pro pozdější použití
    with GridLocations(x_spacing=5, y_spacing=5, x_count=2, y_count=2) as locs:
        # V Builder módu Sphere automaticky přibude k rozpracovanému dílu
        Sphere(1)

# 4. Extrakce vytvořeného tělesa z builderu do proměnné pro Algebra mód
part = p.part

# 5. Vektorizovaná operace v Algebra módu (nyní funkční)
# Využíváme lokace uložené v proměnné 'locs'
part -= [loc * Cylinder(radius, height) for loc in locs.locations]

# Zobrazení výsledku (vyžaduje OCP CAD Viewer)
show(part)
```

**Pozicování na křivce:**  
Operátor `@` (pozice 0.0–1.0) a `%` (tečna/tangent) umožňuje "přichytávat" objekty ke křivkám bez znalosti souřadnic.

---

## 7) Export a Ekosystém

### 7.1 Exportní formáty (kdy co použít)

| Formát        | Použití                                | Poznámka                                                                   |
| ------------- | -------------------------------------- | -------------------------------------------------------------------------- |
| **STEP**      | Master formát pro CNC, CAM, výměnu dat | Přesný, matematické plochy                                                 |
| **STL / 3MF** | 3D tisk                                | Kontroluj `angular_tolerance` (lineární a angulární deflekce) pro hladkost |
| **DXF / SVG** | Laser, CNC řezání                      | Třída `ExportDXF` podporuje vrstvy (hladiny) pro řez vs. gravírování       |

**Export / import reference:**

```python
from build123d import *
from ocp_vscode import show

# 1. Vytvoření geometrie (Algebra mód)
part = Box(10, 10, 10) # Definice tělesa (krychle)

# 2. Zobrazení v OCP Vieweru
# Tento příkaz vykreslí objekt v 3D okně VS Code
show(part, names=["moje_krychle"])

# 3. Exporty (vytvoří soubory v pracovním adresáři)
export_step(part, "model.step")  # Přesný přenos pro CAD systémy
export_stl(part, "print.stl")    # Aproximace sítě pro 3D tisk

# 4. Import (vyžaduje existující soubor "profile.svg" ve složce)
# svg_data bude obsahovat seznam drátů (Wires) nebo ploch (Faces)
try:
    svg_data = import_svg("profile.svg")
    show(svg_data, names=["svg_import"]) # Zobrazí i importovaná 2D data
except ValueError:
    print("Soubor profile.svg nebyl nalezen, import přeskočen.")
```

### 7.2 Užitečné knihovny (Ekosystém)

**Nesnažit se vše modelovat od nuly.**

- **`bd_warehouse`**: Knihovna standardních dílů (ISO šrouby, ložiska, profily)
- **`gggears`**: Generátor ozubených kol (evolventní profily)
- **`ocp-freecad-cam`**: Generování drah (G-code) přímo z modelu přes FreeCAD engine

---

## 8) Struktura projektu (pro verzování)

Na základě filozofie **„CAD-as-code“** by profesionální projekt měl být organizován tak, aby podporoval čitelnost, verzování a automatizaci.

### 8.1 Kořenový adresář (Root)

Obsahuje konfigurační soubory projektu a metadata:

```text
project/
├── README.md              # Popis projektu, instrukce k instalaci, ukázky
├── .gitignore             # __pycache__, *.step, *.stl (velké binárky)
├── pyproject.toml         # Závislosti (build123d, ocp_vscode, bd_warehouse)
│   nebo requirements.txt
├── LICENSE                # Licence (např. Apache-2.0 používaná build123d)
```

### 8.2 Adresářová struktura

Doporučený layout pro udržovatelnost:

```text
project/
├── src/ nebo models/      # Python skripty s geometrií dílů a sestav
├── tests/                 # Automatizované testy (pytest)
│   └── test_dimensions.py # Validace objemu, rozměrů, kolizí
├── assets/ nebo images/   # Screenshoty, schémata pro dokumentaci
├── exports/               # Vygenerované soubory (není nutné verzovat)
│   ├── step/              # Pro CAM a výměnu dat
│   ├── stl/ nebo 3mf/     # Pro 3D tisk
│   └── dxf/ nebo svg/     # Pro laser/CNC řezání
├── imports/               # Zdrojová data (koupené STEP, SVG profily)
└── docs/                  # Sphinx dokumentace (autogenerovaná z kódu)
    ├── source/
    │   ├── conf.py
    │   └── index.rst
    └── build/
```

**Poznámka k `exports/`:**  
Nemusí být v Gitu (typicky v `.gitignore`), ale je dobré mít strukturu — usnadní to automatizaci CI/CD.

### 8.3 Best practices pro kód v Gitu

- **Parametrizace:** Místo pevných hodnot proměnné → generování variant z jednoho souboru
- **Pojmenování kontextů:** `with BuildPart() as bracket:` → usnadňuje debugging v OCP CAD Vieweru a následnou manipulaci v sestavách
- **Mělké kopie:** Pro opakující se díly v sestavách používej `copy()`, ne `deepcopy()` (šetří paměť)
- **.gitignore klíčové:** Odfiltruj `__pycache__`, velké `*.step`, `*.stl` soubory

**Příklad `.gitignore`:**

```gitignore
# Python
__pycache__/
*.pyc
.venv/
*.egg-info/

# Build123d exports (velké binárky)
exports/
*.step
*.stl
*.3mf
*.dxf

# Sphinx build
docs/build/

# IDE
.vscode/
.idea/
```

### 8.4 Dokumentace kódu se Sphinxem (volitelné)

Pro větší projekty (nebo když chceš sdílet API s týmem) generuj technickou dokumentaci přímo z docstringů. Sphinx umí vytáhnout parametry, return typy a popisy přímo z kódu.

**Setup (v aktivovaném venv):**

```bash
pip install sphinx furo sphinx-autodoc-typehints myst-parser
sphinx-quickstart docs
```

Typické nastavení při `quickstart`:

- Separate source and build directories? → **Yes**
- Project name: `MyCADProject`
- Author: `<tvoje jméno>`

**Zapnutí autodoc v `docs/source/conf.py`:**

```python
import os
import sys

# Cesta k tvému kódu (např. src/ layout)
sys.path.insert(0, os.path.abspath("../../src"))

extensions = [
    "sphinx.ext.autodoc",           # Generování z docstringů
    "sphinx.ext.napoleon",          # Google/Numpy docstring styl
    "sphinx.ext.viewcode",          # [source] odkazy v HTML
    "sphinx_autodoc_typehints",     # Lepší práce s type hints
    "myst_parser",                  # Umožní psát .md místo .rst
]

html_theme = "furo"  # Modernější než default
```

**Build dokumentace:**

```bash
# Jednorázový build
sphinx-build -b html docs/source docs/build/html

# Nebo přes Makefile (pokud vygenerován)
make -C docs html

# Live-reload (doporučené pro iterace)
pip install sphinx-autobuild
sphinx-autobuild docs/source docs/build/html
# → otevře http://127.0.0.1:8000 a auto-refresh při změnách
```

**VS Code integrace (volitelné):**  
Přidej `.vscode/tasks.json` pro build na jedno kliknutí:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Sphinx: build HTML",
      "type": "shell",
      "command": "sphinx-build",
      "args": ["-b", "html", "docs/source", "docs/build/html"],
      "group": "build",
      "problemMatcher": []
    }
  ]
}
```

Pak stačí: `Ctrl+Shift+B` → výběr task → HTML se vygeneruje.

> **Tip pro build123d projekty:** V docstringu u generativních funkcí uveď parametry a jednotky.
> Sphinx to pak pěkně zobrazí v API referenci.

**Příklad docstringu (Google style):**

```python
def create_bracket(width: float, height: float, thickness: float = 5.0):
    """Vytvoří L-bracket s montážními otvory.

    Args:
        width: Šířka ramene v mm
        height: Výška ramene v mm
        thickness: Tloušťka materiálu v mm (default: 5.0)

    Returns:
        Part: Build123d Solid objekt připravený k exportu

    Example:
        >>> bracket = create_bracket(100, 80)
        >>> export_step(bracket, "bracket.step")
    """
    # ... tvůj kód
```

---

## 9) AI-Assisted Workflow a Nástroje

Můj přístup k experimentování kombinuje lidský záměr a rychlost generativní AI. Tento proces nejčastěji využívám v `sandbox/` pro rychlé prototypování:

1. **Záměr a vstup:** Slovně definuji tvar a technické parametry, případně modelu poskytnu jednoduchý nákres či výkres.
2. **AI Generování:** Nechám LLM připravit základní skript v build123d. Generování kódu je pro AI mnohem přirozenější a přesnější než snaha suplovat vizuální klikání v GUI.
3. **Okamžitá validace:** Díky **OCP CAD Vieweru** ve VS Code vidím geometrii okamžitě po spuštění skriptu.
4. **Iterace a Export:** Rychle doladím detaily (např. tolerance, sražení hran) a jakmile model sedí, skript automaticky vygeneruje finální STL pro 3D tisk.

### Nástroje pro AI asistenci (Experimentální)

Sleduji možnosti, jak zapojit AI agenty přímo do procesu tvorby. Zajímavým kandidátem je **[VibeCAD](https://github.com/rawwerks/vibecad)** (dostupný na [MCP Market](https://mcpmarket.com/tools/skills/build123d-cad-modeling)).

Tato sada nástrojů umožňuje Claudovi vystupovat v roli **strojního inženýra** se specializovanou znalostí build123d. Cílem je zrychlit "rapid prototyping" díky těmto schopnostem:

- **Pokročilá geometrie:** Tvorba složitých 3D těles, booleovské operace a parametrické sestavy (bez složitého nastavování díky `uv`).
- **Průmyslové exporty:** Generování výstupů přímo do formátů STEP, STL a GLB.
- **Specializované knihovny:** Přímé využití hotových modulů pro ozubená kola, závity a spojovací materiál.

_Poznámka: Jde o externí tooling třetí strany, který zatím pouze mapuji pro budoucí integraci do workflow._

### Základní nástroje (Standardní)

- **VS Code + OCP CAD Viewer** – rychlý náhled + inspekce topologie (interaktivní 3D)
- **[t3.chat](https://t3.chat/)** – pro AI-Assisted Workflow
- **Jupyter** – iterace po malých krocích (výborné pro prototyping)

### Testování & ladění

- **pytest** – automatické testy (bbox, volume, počet prvků)
- **Visual debug** – VS Code + OCP CAD Viewer, krokování kódu
- **Co testovat:** rozměry, clearances, počet děr, objem/mass

**Příklad testu (pytest):**

```python
from build123d import *

def test_box_volume():
    box = Box(10, 10, 10)
    assert abs(box.volume - 1000) < 0.01, "Objem neodpovídá"

def test_hole_count():
    with BuildPart() as p:
        Box(100, 50, 10)
        with GridLocations(20, 20, 2, 2):
            Cylinder(5, 10, mode=Mode.SUBTRACT)

    holes = p.part.faces().filter_by(GeomType.CYLINDER)
    assert len(holes) == 4, f"Očekávány 4 válcové plochy, nalezeno {len(holes)}"
```

---

## 10) Compatibility / Verze (krátce)

Build123d se rychle vyvíjí. Pokud snippet přestane fungovat:

**Zkontroluj verzi (Python – spolehlivé):**

```python
import importlib.metadata as md
print(md.version("build123d"))
```

**Zkontroluj verzi (terminál):**

```bash
pip show build123d
```

> **Pozn.:** `build123d.__version__` může fungovat, ale nemusí být vždy k dispozici.

**Co hlídat:**

- Existují různé vrstvy API (např. `Box(...)` vs `Solid.make_box(...)`)
- Helpery/aliasy se mohou časem upřesňovat (`Pos`, `Rot`, `GridLocations`, ...)
- Zkontroluj aktuální docs: <https://build123d.readthedocs.io>

> **Tip:** Pokud chceš stabilitu v CI/projektech, připni verzi build123d v `requirements.txt`:
>
> ```text
> build123d==0.10.0
> ```

---

## Rychlá referenční příručka (Syntax Cheat Sheet)

**Robustní struktura BuildPart (Parametrický vzor):**

```python
from build123d import *
from ocp_vscode import show

# Parametrické zadání
L, W, T = 100.0, 50.0, 10.0
FILLET_R = 2.0

with BuildPart() as model:
    # 1. Základní profil s fillet ve 2D
    with BuildSketch() as profil:
        Rectangle(L, W)
        fillet(profil.vertices(), radius=5)
    extrude(amount=T)

    # 2. Práce s horní plochou
    top = model.faces().sort_by(Axis.Z).last
    with BuildSketch(top) as diry:
        with GridLocations(L/2, W/2, 2, 2):
            Circle(radius=5)
    extrude(amount=-T, mode=Mode.SUBTRACT)

    # 3. Fillet na právě vytvořených hranách (Select.LAST)
    fillet(
        model.edges(Select.LAST).filter_by(Axis.Z),
        radius=FILLET_R
    )

show(model.part)
```

**Klíčové Enumy:**

- **Align:** `Align.MIN`, `Align.CENTER`, `Align.MAX`
- **Mode:** `Mode.ADD`, `Mode.SUBTRACT`, `Mode.INTERSECT`, `Mode.PRIVATE` (pomocná geometrie)
- **Select:** `Select.LAST`, `Select.NEW`, `Select.ALL`

**Selektory v praxi:**

```python
# Nejvyšší plocha
top = model.faces().sort_by(Axis.Z).last

# Pouze kruhové hrany (např. pro sražení hran děr)
circles = model.edges().filter_by(GeomType.CIRCLE)

# Všechny body na základně (minimální Z)
base_vertices = model.vertices().group_by(Axis.Z)[0]
```

---

**Konec poznámek.** Pravidelně aktualizuji při objevování nových patterns.
