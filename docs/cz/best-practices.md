# build123d – best practices (poznámky)

Tyto poznámky jsou moje shrnutí při studiu build123d. Ber je jako pracovní „cheat sheet“,
ne jako oficiální dokumentaci.

Rychlá definice (ať je jasné, o čem mluvím):
- build123d je parametrický CAD framework v Pythonu pro 2D/3D modelování.
- Je postavený na BREP přístupu (Boundary Representation) a běží nad OCCT (Open Cascade).
- Cíl: „CAD-as-code“ — čitelnost, udržovatelnost, parametrizace, možnost testů a automatizace.

Zdroje (upstream):
- build123d docs (hlavní rozcestník): https://build123d.readthedocs.io/en/latest/
- build123d GitHub: https://github.com/gumyr/build123d

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
- [8) Nástroje](#8-nástroje-moje-workflow)
- [9) Compatibility / Verze](#9-compatibility--verze-krátce)

---

## 0) Quick start (instalace + základní setup)

Požadavky:
- Python 3.10–3.13 (dle aktuální dokumentace)

Instalace:
```bash
python -m venv .venv
# aktivace venv: .venv\Scripts\activate (Win) nebo source .venv/bin/activate
pip install --upgrade pip
pip install build123d
```

Sanity check (rychle ověřím, že import funguje a něco se vykreslí/vypíše):
```python
from build123d import *

print(Box(1, 2, 3).show_topology(limit_class="Face"))
# Pozn.: u některých verzí může být potřeba Solid.make_box(1, 2, 3)
```

Doporučený viewer / IDE:
- VS Code + OCP CAD Viewer (rychlý náhled + inspekce topologie)
- Pro interaktivní práci se hodí Jupyter (iterace po malých krocích)

> Tip: na začátku každého souboru si dávám blok parametrů (hlavní rozměry, jednotky, tolerance).
> Změny jsou pak „jedním místem“ a model se líp refaktoruje.

---

## 1) Kontext: proč CAD-as-code

Co mi CAD-as-code dává:
- verzování modelu v Gitu (diffy v kódu, ne v binárních CAD souborech)
- generování variant z parametrů (velikosti, konfigurace)
- možnost testovat/validovat (rozměry, clearance, pravidla)

Na co si dát pozor:
- „kód je model“ → čitelnost je stejně důležitá jako správná geometrie
- při refaktoringu je snadné rozbít selekce (selectors) a navazující operace

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

Můj mentální model:
- „průběžný součet“ — operace uvnitř bloku mění aktuální geometrii

Mini ukázka (2D → extrude → cut na top face):
```python
from build123d import *

with BuildPart() as p:
    with BuildSketch():
        Rectangle(20, 20)
    extrude(amount=10)  # základní blok

    top_face = p.faces().sort_by(Axis.Z)[-1]
    with BuildSketch(top_face):
        Circle(5)
    extrude(amount=-5, mode=Mode.SUBTRACT)  # odečtení válce
```

### Algebra mode (bezstavový, operátorový)
Princip:
- objekty jsou proměnné
- kombinuju je přes operátory (union/cut/intersect) a transformace

Základní operátory (prakticky):
- `+` union (sjednocení)
- `-` cut (odečet)
- `&` intersect (průnik)
- `*` transformace (typicky `Location` / `Pos` / `Rot`)

Ukázka (geometrické rovnice + transformace):
```python
from build123d import *

part = Box(1, 2, 3) + Cylinder(0.2, 5)
part = Box(1, 2, 3) - Cylinder(0.2, 5)

# umístění/rotace (ověř syntaxi ve své verzi build123d)
part = Plane.XZ * Pos(1, 2, 3) * Rot(0, 100, 45) * Box(1, 2, 3)
```

Dodatek — práce s křivkami (snapping / navazování):
```python
# Edge/Wire operátory (Algebra mode)
pos_vec = curve @ 0.5   # Vector: pozice na křivce (0.0 až 1.0)
tangent = curve % 0.5   # Vector: tečna ve stejném bodě
loc = curve ^ 0.5       # Location: umístění v bodě (užitečné pro placement)
```

Poznámka:
- v praxi se dají kombinovat oba přístupy — to je jedna z výhod build123d.

---

## 3) Topologie: jak build123d “vidí” těleso

Poznámka:
- většina entit je nějaká varianta `Shape` (společné chování, transformace, export, …)

Hierarchie (od nejmenšího):
1. `Vertex` (bod)
2. `Edge` (hrana/křivka)
3. `Wire` (spojené hrany)
4. `Face` (plocha)
5. `Shell` (skořepina – kolekce ploch)
6. `Solid` (uzavřené těleso)
7. `Compound` (kontejner pro více tvarů)

Proč mi to není jedno:
- většina „robustních“ postupů stojí na tom, že umím vybrat správnou plochu/hranu
  i po změně parametrů.

---

## 4) Selectors: robustní výběr prvků (praktické poznámky)

Základ:
- `faces()`, `edges()`, `vertices()` (a často i `solids()`) vrací `ShapeList`
  (list + metody navíc)

Užitečné operace na výběru:
- `filter_by(...)` – zúžení podle geometrie / orientace / typu
  - typicky osa/směr: např. `filter_by(Axis.Z)`
  - typicky typ geometrie: např. `filter_by(GeomType.CIRCLE)` (kruhové hrany)
- `sort_by(...)` – seřazení a výběr extrému (`[0]`, `[-1]`)
  - např. `sort_by(Axis.Z)` a pak vzít „nejvyšší“ / „nejnižší“
- `Select.LAST`, `Select.NEW`
  - `LAST` = „co vzniklo poslední operací“
  - `NEW` = „nově vzniklé prvky“ (často po booleanech / průnicích)

Co si hlídat:
- vyhýbat se „křehkým“ výběrům typu „vezmi první hranu“ bez kontextu
- radši filtrovat podle směru, polohy, typu geometrie, případně kombinovat
- po booleanech často dává smysl pracovat s `Select.LAST` / `Select.NEW`

Mini checklist při ladění selektorů:
- nejdřív si vypsat/zkontrolovat počet prvků (`len(...)`)
- zkontrolovat orientaci/umístění (osa, normal, bounding box)
- teprve pak aplikovat `fillet/chamfer`

> Pozor: `GeomType.CIRCLE` patří typicky na `edges()`, ne na `faces()`.
> Pokud filtruješ plochy, hledej např. `GeomType.PLANE`, `GeomType.CYLINDER`, apod.

Snippety pro ladění děr (Varianty A/B):

Varianta A — chci kruhové hrany:
```python
from build123d import *

faces_z = part.faces().filter_by(Axis.Z)
print("faces_z:", len(faces_z))

top_hole_edges = faces_z.edges().filter_by(GeomType.CIRCLE)
print("top_hole_edges:", len(top_hole_edges))
```

Varianta B — chci plochy, které obsahují díry (inner wires):
```python
from build123d import *

faces_z = part.faces().filter_by(Axis.Z)
faces_with_holes = faces_z.filter_by(lambda f: len(f.inner_wires()) > 0)
print("faces_with_holes:", len(faces_with_holes))
```

> Tip: při ladění selektorů vždy začni `print(len(...))` a když si nejsi jistý,
> rozklikni topologii ve VS Code přes OCP CAD Viewer.

---

## 5) Best practices pro robustní modely

### 5.1 “2D před 3D”
Preferovaný workflow:
- skica v 2D (`BuildSketch`)
- pak teprve `extrude` / `revolve` / `sweep` / `loft`

Proč:
- 2D operace bývají stabilnější
- méně problémů s geometrií než složité 3D booleany

### 5.2 Parametrizace (žádná magická čísla)
- klíčové rozměry jako proměnné nahoře
- odvozené rozměry počítat z nich
- držet jednotky konzistentní (mm vs. m)

### 5.3 Fillet/chamfer až na konec
- zaoblení/zkosení často rozbije model při změnách
- když je dělám pozdě, snížím počet “křehkých” závislostí

### 5.4 Workplanes z existující geometrie
- místo ručního počítání souřadnic radši odvozovat roviny z ploch (`Face`)
- model se pak „přilepí“ k tvaru a posouvá se s ním

---

## 6) Sestavy a mechanismy

### 6.1 Sestavy (Assemblies)
- sestavy jsou strom (anytree) → transformace rodiče se přenáší na potomky
- pro opakující se díly používat **mělké kopie** (`copy()`), ne `deepcopy()`
  - výrazně to šetří paměť a velikost projektu u opakovaných komponent (šrouby, profily)

### 6.2 Klouby (Joints) - Kinematika
- Slouží k "chytrému" spojování dílů, nejen polohování.
- Použití: `part_a.joints['J1'].connect_to(part_b.joints['J2'])`
- Typy:
  - `RigidJoint`: 0 DOF (pevné spojení, šrouby, svary)
  - `RevoluteJoint`: 1 DOF (rotace - panty)
  - `LinearJoint`: 1 DOF (posun - písty, pojezdy)
  - `CylindricalJoint`: 2 DOF (rotace + posun)
  - `BallJoint`: 3 DOF (kulový čep)

Umisťování prvků (location contexts) + bulk operace:
```python
from build123d import *

with BuildPart():
    # rozmístění 2x2 objektů na aktivní rovině
    with GridLocations(x_spacing=5, y_spacing=5, x_count=2, y_count=2):
        Sphere(1)

# vektorizované operace (efektivní pro hodně děr / řezů)
part -= [loc * Cylinder(radius, height) for loc in locations]
```

---

## 7) Export a Ekosystém

### 7.1 Exportní formáty (kdy co použít)
- **STL / 3MF**: pro 3D tisk (pozor na nastavení tesselace - `angular_tolerance`)
- **STEP**: "Master" formát. Pro přesný přenos do jiných CADů (Fusion, FreeCAD) a pro CAM (obrábění).
- **DXF**: pro 2D výrobu (laser, CNC řezání).
  - Tip: používat vrstvy (Layers) pro odlišení řezu a gravírování.

### 7.2 Užitečné knihovny (Ekosystém)
Nesnažit se vše modelovat od nuly.
- `bd_warehouse`: Knihovna standardních dílů (šrouby, matice, profily).
- `gggears`: Generátor ozubených kol (evolventní profily).
- `ocp-freecad-cam`: Generování drah (G-code) přímo z modelu přes FreeCAD engine.

Export / import reference:
```python
from build123d import *

export_step(part, "model.step")  # CAD exchange / CAM
export_stl(part, "print.stl")    # 3D tisk (tesselace!)
svg_data = import_svg("profile.svg")
```

---

## 8) Nástroje (moje workflow)

- VS Code + OCP CAD Viewer (rychlý náhled + inspekce topologie)
- [t3.chat](https://t3.chat/) - pro [AI-Assisted Workflow](ai-assisted-workflow.md)

**Testování & ladění (krátce):**
- `pytest` – pro automatické testy (bbox, volume, počet prvků)
- Visual debug – VS Code + OCP CAD Viewer, krokování kódu
- Co testovat: rozměry, clearances, počet děr, objem/mass

---

## 9) Compatibility / Verze (krátce)

Build123d se rychle vyvíjí. Pokud snippet přestane fungovat:
- zkontroluj verzi:
```python
import build123d
print(getattr(build123d, "__version__", "unknown"))
```
- zkontroluj aktuální docs: https://build123d.readthedocs.io
- počítej s tím, že existují různé vrstvy API (např. `Box(...)` vs `Solid.make_box(...)`)
  a že helpery/aliasy se mohou časem upřesňovat (`Pos`, `Rot`, `GridLocations`, ...)

> Tip: pokud chceš stabilitu v CI/projektech, pinni verzi build123d v requirements.
