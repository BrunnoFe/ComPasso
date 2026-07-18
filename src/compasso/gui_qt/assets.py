"""Resolução do diretório de assets estáticos (ícones, beep) da GUI Qt.

Resolve ``assets/`` a partir da localização deste arquivo (independente do diretório de
trabalho) — funciona em desenvolvimento e empacotado (PyInstaller, via ``sys._MEIPASS``).
"""

import sys
from pathlib import Path

from compasso.utils.configs import ICON_FILENAME  # 'icon.ico' (janela no Windows)

ICON_PNG_FILENAME = "icon.png"                     # ícone multiplataforma (QML/janela)
BEEP_FILENAME = "edit_beep_1000Hz.wav"             # beep de aviso na contagem regressiva

# Em dev: .../src/compasso/gui_qt/assets.py -> parents[3] = raiz do repo -> /assets.
# Empacotado: sys._MEIPASS/assets.
if getattr(sys, "frozen", False):
    ASSETS_DIR = Path(getattr(sys, "_MEIPASS", ".")) / "assets"
else:
    ASSETS_DIR = Path(__file__).resolve().parents[3] / "assets"

__all__ = ["ASSETS_DIR", "ICON_FILENAME", "ICON_PNG_FILENAME", "BEEP_FILENAME"]
