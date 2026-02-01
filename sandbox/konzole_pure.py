#!/usr/bin/env python3
"""
Konzole pro postel - Převod z OpenSCAD
"""
from build123d import *
from ocp_vscode import show

# ========== PARAMETRY ==========
deska_sirka = 16
hloubka_nasazeni = 30
vzdalenost_desek = 47.5
prumer_valce = 35
tolerance = 0.5

# ========== VÝPOČET ==========
delka_valce = hloubka_nasazeni + vzdalenost_desek + hloubka_nasazeni
sirka_slotu = deska_sirka + tolerance * 2

print(f"Výsledné rozměry:")
print(f"  Délka válce: {delka_valce:.1f} mm")
print(f"  Šířka slotu: {sirka_slotu:.1f} mm")

# ========== MODEL ==========

# 1. HLAVNÍ VÁLEC
# DŮLEŽITÉ: Align.MIN na ose Z simuluje chování OpenSCADu (základna na 0)
valec = Cylinder(
    radius=prumer_valce / 2,
    height=delka_valce,
    align=(Align.CENTER, Align.CENTER, Align.MIN) 
)
# Rotace 90° kolem Y -> Nyní válec začíná na X=0 a končí na X=107.5
valec = valec.rotate(Axis.Y, 90)

# 2. DOLNÍ SLOT
# Pozice v OpenSCAD: [15, 0, 0]
slot1 = Box(
    hloubka_nasazeni + 0.1,
    prumer_valce + 2,
    sirka_slotu,
    align=(Align.CENTER, Align.CENTER, Align.CENTER) # Center=true
)
slot1 = slot1.move(Location((hloubka_nasazeni / 2, 0, 0)))

# 3. HORNÍ SLOT
# Pozice v OpenSCAD: [92.5, 0, 0]
slot2_pos = hloubka_nasazeni + vzdalenost_desek + hloubka_nasazeni / 2
slot2 = Box(
    hloubka_nasazeni + 0.1,
    prumer_valce + 2,
    sirka_slotu,
    align=(Align.CENTER, Align.CENTER, Align.CENTER) # Center=true
)
slot2 = slot2.move(Location((slot2_pos, 0, 0)))

# 4. ROZDÍL
result = valec - slot1 - slot2

# Export
export_stl(result, "./stl/konzole_pure.stl")
print("\nExportováno: konzole_pure.stl")

# ZOBRAZENÍ V OCP CAD VIEWER
show(result)