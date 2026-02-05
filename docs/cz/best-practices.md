# build123d – best practices (poznámky)

Tyto poznámky jsou moje shrnutí při studiu build123d. Ber je jako pracovní „cheat sheet“,
ne jako oficiální dokumentaci.

Rychlá definice (ať je jasné, o čem mluvím):
- build123d je parametrický CAD framework v Pythonu pro 2D/3D modelování.
- Je postavený na BREP přístupu (Boundary Representation) a běží nad OCCT (Open Cascade).
- Cíl: „CAD jako kód“ – čitelnost, udržovatelnost, parametrizace, možnost testů a automatizace.

Zdroje (upstream):
- build123d docs (hlavní rozcestník): https://build123d.readthedocs.io/en/latest/
- build123d GitHub: https://github.com/gumyr/build123d

---

## 0) Quick start (instalace + základní setup)

Požadavky:
- Python 3.10–3.13 (dle aktuální dokumentace)

Instalace:
- `pip install build123d`

Doporučený viewer / IDE:
- VS Code + OCP CAD Viewer (rychlý náhled + inspekce topologie)
- Pro interaktivní práci se hodí Jupyter (pokud chci iterovat tvar po malých krocích)

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
- „průběžný součet“ – operace uvnitř bloku mění aktuální geometrii

### Algebra mode (bezstavový, operátorový)
Princip:
- objekty jsou proměnné
- kombinuju je přes operátory (union/cut/intersect) a transformace

Základní operátory (prakticky):
- `+` union (sjednocení)
- `-` cut (odečet)
- `&` intersect (průnik)
- `*` transformace (typicky `Location` / `Pos` / `Rot`)

Kdy se mi hodí:
- rychlé skládání tvarů a „geometrické rovnice“
- vektorizované operace (např. více děr přes list locations)

Poznámka:
- v praxi se dají kombinovat oba přístupy – to je jedna z výhod build123d.

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
  - typicky osa/směr: např. `filter_by(Axis.Z)` (podle orientace k ose)
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

---

## 7) Export a Ekosystém

### 7.1 Exportní formáty (kdy co použít)
- **STL / 3MF**: pro 3D tisk (pozor na nastavení tesselace - `angular_tolerance`)
- **STEP**: "Master" formát. Pro přesný přenos do jiných CADů (Fusion, FreeCAD) a pro CAM (obrábění).
- **DXF**: pro 2D výrobu (laser, CNC řezání).
  - Tip: Používat vrstvy (Layers) pro odlišení řezu a gravírování.

### 7.2 Užitečné knihovny (Ekosystém)
Nesnažit se vše modelovat od nuly.
- `bd_warehouse`: Knihovna standardních dílů (šrouby, matice, profily).
- `gggears`: Generátor ozubených kol (evolventní profily).
- `ocp-freecad-cam`: Generování drah (G-code) přímo z modelu přes FreeCAD engine.

---

## 8) Nástroje (moje workflow)

- VS Code + OCP CAD Viewer (rychlý náhled + inspekce topologie)
- [t3.chat](https://t3.chat/) - pro [AI-Assisted Workflow](ai-assisted-workflow.md)
- **Testování & ladění (krátce):**
  - `pytest` – pro automatické testy (bbox, volume, počet prvků)
  - Visual debug – VS Code + OCP CAD Viewer, krokování kódu
  - Co testovat: rozměry, clearances, počet děr, objem/mass

---

## TODO (až budu mít čas)
- [ ] přidat konkrétní ukázku robustního výběru ploch (faces/filter/sort)
- [ ] přidat mini “template” pro nový díl (parametry → skica → extrude → features)
- [ ] poznámky k tolerancím a exportu STL (tesselace)