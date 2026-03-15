"""
Konzole pro dětskou zábranu - Heavy Duty Edice (Armovaná verze)
Architektura: Pure Builder Mode
"""
from os import makedirs
from build123d import *

try:
    from ocp_vscode import show
except ImportError:
    show = None

# ---------- 1. PARAMETRY ----------
# Rozměry slotů (kompatibilita)
hloubka_nasazeni = 30.0
vzdalenost_desek = 47.5
sirka_slotu_A = 16.3 
sirka_slotu_B = 18.5 

# Pevnostní parametry
prumer_valce = 40.0         
dira_prumer = 4.3           # Pro M4 závitové tyče (zmenšeno z 5.3 mm)
fillet_rim_radius = 2.0     
fillet_slot_radius = 1.5    

# Parametry výztuh (Gussets)
vyztuha_tloustka = 4.0
vyztuha_delka = 15.0
vyztuha_vyska = 10.0

# Odvozené hodnoty
delka_valce = hloubka_nasazeni + vzdalenost_desek + hloubka_nasazeni
r = prumer_valce / 2.0
stred_x = delka_valce / 2.0

# 🎯 DOKONALE VYVÁŽENÉ POZICE DĚR (Matematický kompromis pro M4)
# Zajišťuje min. 2.6 mm k vnitřnímu slotu, 3.0 mm k vnější stěně a 5.7 mm mezi dírami
y_hole = 5.0
z_hole = 14.0

# ---------- 2. MODELOVÁNÍ ----------
with BuildPart() as bp:
    # 1. Hlavní těleso - Válec
    with BuildSketch(Plane.YZ):
        Circle(radius=r)
    extrude(amount=delka_valce)

    # 2. Výřezy (Sloty)
    with Locations((hloubka_nasazeni / 2.0, 0, 0)):
        Box(hloubka_nasazeni + 0.1, prumer_valce * 2, sirka_slotu_A, mode=Mode.SUBTRACT)
    
    pos_slot2 = hloubka_nasazeni + vzdalenost_desek + hloubka_nasazeni / 2.0
    with Locations((pos_slot2, 0, 0)):
        Box(hloubka_nasazeni + 0.1, prumer_valce * 2, sirka_slotu_B, mode=Mode.SUBTRACT)

    # 3. Zaoblení přechodů slotů
    slot_edges = (
        bp.edges()
        .filter_by(Axis.Y)
        .filter_by(lambda e: abs(e.center().X - hloubka_nasazeni) < 1.0 or 
                             abs(e.center().X - (hloubka_nasazeni + vzdalenost_desek)) < 1.0)
    )
    if slot_edges:
        fillet(slot_edges, radius=fillet_slot_radius)

    # 4. Výztuhy (Gussets)
    with BuildSketch(Plane.XZ):
        with Locations((hloubka_nasazeni, sirka_slotu_A/2 - 0.5)):
            Polygon([(0,0), (vyztuha_delka, 0), (0, vyztuha_vyska)])
        with Locations((hloubka_nasazeni + vzdalenost_desek, sirka_slotu_B/2 - 0.5)):
            Polygon([(0,0), (-vyztuha_delka, 0), (0, vyztuha_vyska)])
        
        with Locations((hloubka_nasazeni, -sirka_slotu_A/2 + 0.5)):
            Polygon([(0,0), (vyztuha_delka, 0), (0, -vyztuha_vyska)])
        with Locations((hloubka_nasazeni + vzdalenost_desek, -sirka_slotu_B/2 + 0.5)):
            Polygon([(0,0), (-vyztuha_delka, 0), (0, -vyztuha_vyska)])
            
    extrude(amount=vyztuha_tloustka/2, both=True, mode=Mode.ADD)

    # 5. Armovací díry (4 průchozí díry)
    hole_locs = [
        Location((stred_x, y_s * y_hole, z_s * z_hole), (0, 90, 0))
        for y_s in (1, -1) for z_s in (1, -1)
    ]
    
    with Locations(hole_locs):
        Hole(radius=dira_prumer/2, depth=delka_valce)

    # 6. Zaoblení vnějších hran
    hrany_k_zaobleni = (
        bp.edges()
        .filter_by(GeomType.CIRCLE)
        .filter_by(lambda e: e.radius > 10)
        .filter_by(lambda e: abs(e.center().X) < 0.1 or abs(e.center().X - delka_valce) < 0.1)
    )
    
    if hrany_k_zaobleni:
        fillet(hrany_k_zaobleni, radius=fillet_rim_radius)

# ---------- 3. EXPORT A ZOBRAZENÍ ----------
final_part = bp.part

if __name__ == "__main__":
    output_dir = "./exports/stl"
    makedirs(output_dir, exist_ok=True)
    
    export_stl(final_part, f"{output_dir}/konzole_armovana_M4.stl")
    
    print(f"✅ Model úspěšně uložen do {output_dir}/")
    print(f"📊 Objem materiálu: {final_part.volume / 1000:.2f} cm3")

    if show:
        show(
            final_part, 
            names=["Konzole_Armovana_M4"], 
            colors=["#3498db"], 
            alphas=[0.8], 
            grid=(True, True, True)
        )