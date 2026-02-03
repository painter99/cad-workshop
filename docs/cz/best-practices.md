# build123d – best practices (poznámky)

Tyto poznámky jsou moje shrnutí při studiu build123d. Ber je jako pracovní „cheat sheet“,
ne jako oficiální dokumentaci.

Zdroje (upstream):
- build123d docs (hlavní rozcestník): https://build123d.readthedocs.io/en/latest/
- build123d GitHub: https://github.com/gumyr/build123d

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
- `faces()`, `edges()`, `vertices()` vrací `ShapeList` (list + metody navíc)

Užitečné operace na výběru:
- `filter_by(...)` – zúžení podle geometrie / orientace (např. podle osy)
- `sort_by(...)` – seřazení a výběr extrému (`[0]`, `[-1]`)
- `Select.LAST`, `Select.NEW` – „co vzniklo právě teď“

Co si hlídám:
- vyhýbat se „křehkým“ výběrům typu „vezmi první hranu“ bez kontextu
- radši filtrovat podle směru, polohy, typu geometrie, případně kombinovat
- po booleanech často dává smysl pracovat s `Select.LAST`

Mini checklist při ladění selektorů:
- nejdřív si vypsat/zkontrolovat počet prvků (`len(...)`)
- zkontrolovat orientaci/umístění (osa, normal)
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

## 6) Sestavy a výkon (pokud se k tomu dostanu)

- sestavy jsou strom (anytree) → transformace rodiče se přenáší na potomky
- pro opakující se díly používat mělké kopie (`copy()`), ne `deepcopy()`

---

## 7) Nástroje (moje workflow)

- VS Code + OCP CAD Viewer (rychlý náhled + inspekce topologie)
- exporty (dle potřeby): STL / STEP / DXF / SVG

---

## TODO (až budu mít čas)
- [ ] přidat konkrétní ukázku robustního výběru ploch (faces/filter/sort)
- [ ] přidat mini “template” pro nový díl (parametry → skica → extrude → features)
- [ ] poznámky k tolerancím a exportu STL (tesselace)
