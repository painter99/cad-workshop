#!/usr/bin/env python3
"""
Konzole pro postel - Refactored
Architektura: Pure Builder Mode
"""
from math import sqrt
from os import makedirs
from build123d import *

try:
    from ocp_vscode import show, show_object, set_port
    # set_port(3939) # Odkomentujte pokud používáte specifický port
except ImportError:
    show = None

# ---------- PARAMETRY ----------
hloubka_nasazeni = 30.0
vzdalenost_desek = 47.5
prumer_valce = 35.0
sirka_slotu_A = 16.3 
sirka_slotu_B = 18.5 

dira_prumer = 3.3
dira_r = dira_prumer / 2.0

# Poloměr zaoblení vnějších hran
fillet_rim_radius = 1.0  

# Odvozené hodnoty
delka_valce = hloubka_nasazeni + vzdalenost_desek + hloubka_nasazeni
r = prumer_valce / 2.0

# Výpočet pozice děr (zachována původní logika)
z_hole = (r + min(sirka_slotu_A, sirka_slotu_B) / 2.0) / 2.0
y_max = sqrt(max(0.0, r * r - z_hole * z_hole))
y_hole = min(6.0, y_max - dira_r - 0.5)

# ---------- MODELOVÁNÍ (Builder Mode) ----------
with BuildPart() as bp:
    # 1. Hlavní těleso - Válec
    # Používáme extrude kruhu z roviny YZ podél osy X.
    # To automaticky umístí začátek na X=0 a konec na X=delka_valce.
    with BuildSketch(Plane.YZ):
        Circle(radius=r)
    extrude(amount=delka_valce)

    # 2. Výřezy (Sloty)
    # Používáme Box s Mode.SUBTRACT.
    # Slot 1 (u začátku)
    with Locations((hloubka_nasazeni / 2.0, 0, 0)):
        Box(hloubka_nasazeni + 0.1, prumer_valce * 2, sirka_slotu_A, mode=Mode.SUBTRACT)
    
    # Slot 2 (u konce)
    pos_slot2 = hloubka_nasazeni + vzdalenost_desek + hloubka_nasazeni / 2.0
    with Locations((pos_slot2, 0, 0)):
        Box(hloubka_nasazeni + 0.1, prumer_valce * 2, sirka_slotu_B, mode=Mode.SUBTRACT)

    # 3. Díry
    # Vytvoříme pole lokací pro díry. Protože vrtáme kolmo na osu válce (X),
    # musíme díry orientovat (Hole vrtá podél Z lokálního systému).
    # Zde použijeme rotaci (0, 90, 0) pro vrtání ve směru X (pokud by byly axiální),
    # ale původní kód vrtal kolmo. Původní logika:
    # Location((x, y, z), (0, 90, 0)) -> Rotace 90 kolem Y otočí Z osy do X osy.
    # To by znamenalo, že díry jdou podél osy válce? 
    # Analýza původního kódu: Hole() vrtá podél Z. Rotace (0,90,0) otočí Z na X.
    # Původní záměr byl pravděpodobně vrtat skrz "stěny" zbylé po výřezu.
    # Zachovávám původní souřadnice a orientaci.
    
    hole_locs = [
        Location((delka_valce / 2.0, y_s * y_hole, z_s * z_hole), (0, 90, 0))
        for y_s in (1, -1) for z_s in (1, -1)
    ]
    
    with Locations(hole_locs):
        Hole(radius=dira_r)

    # 4. Zaoblení (Fillet)
    # Robustní selekce hran:
    # a) Vybereme hrany typu kružnice (GeomType.CIRCLE)
    # b) Vyfiltrujeme malé díry (chceme jen vnější obvod válce, r > 10)
    # c) Vybereme jen ty na koncích válce (X=0 a X=delka)
    
    hrany_k_zaobleni = (
        bp.edges()
        .filter_by(GeomType.CIRCLE)           # Jen kruhové hrany
        .filter_by(lambda e: e.radius > 10)   # Ignorovat malé díry pro šrouby
        .filter_by(                           # Jen konce válce
            lambda e: abs(e.center().X) < 0.1 or abs(e.center().X - delka_valce) < 0.1
        )
    )
    
    if hrany_k_zaobleni:
        fillet(hrany_k_zaobleni, radius=fillet_rim_radius)
        print(f"Zaobleno {len(hrany_k_zaobleni)} hran.")

# ---------- EXPORT A ZOBRAZENÍ ----------
final_part = bp.part

# Export
output_dir = "./exports/stl"
makedirs(output_dir, exist_ok=True)
export_stl(final_part, f"{output_dir}/konzole_final.stl")
print(f"Model uložen do {output_dir}/konzole_final.stl")

# Zobrazení ve VS Code (OCP CAD Viewer)
if show:
    show(
        final_part, 
        names=["Konzole"], 
        colors=["#FFAA00"], # Oranžová pro lepší kontrast
        alphas=[0.8], 
        grid=(True, True, True)
    )