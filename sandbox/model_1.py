from build123d import *
from ocp_vscode import show

# Nastavení rozměrů
delka = 20
sirka = 20
vyska = 10

# Vytvoření objektu (kvádru)
with BuildPart() as krychle:
    Box(delka, sirka, vyska)

# Zobrazení objektu ve vieweru
show(krychle)