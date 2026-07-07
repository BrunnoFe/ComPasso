"""Resolução do diretório de assets estáticos (ícones) da GUI.

Resolve a pasta ``assets/`` a partir da localização deste arquivo (independente do
diretório de trabalho atual) — funciona tanto em desenvolvimento quanto empacotado
(PyInstaller, via ``sys._MEIPASS``).
"""

import sys
from pathlib import Path

# Em desenvolvimento: .../src/compasso/gui/assets.py -> parents[3] = raiz do repositório -> /assets.
# Empacotado (PyInstaller): os dados ficam em sys._MEIPASS/assets. O comportamento em
# desenvolvimento é idêntico ao anterior.
if getattr(sys, "frozen", False):
    ASSETS_DIR = Path(getattr(sys, "_MEIPASS", ".")) / "assets"
else:
    ASSETS_DIR = Path(__file__).resolve().parents[3] / "assets"
