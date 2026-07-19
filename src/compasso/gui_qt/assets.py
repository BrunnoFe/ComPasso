"""Resolução do diretório de assets estáticos (ícones, beep) da GUI Qt.

Resolve ``assets/`` de forma **agnóstica de empacotador** (dev, PyInstaller e Nuitka) via
``compasso.utils.resources`` — ver aquele módulo para a lógica de detecção.
"""

from pathlib import Path

from compasso.utils.configs import ICON_FILENAME  # 'icon.ico' (janela no Windows)
from compasso.utils.resources import base_recursos

ICON_PNG_FILENAME = "icon.png"                     # ícone multiplataforma (QML/janela)
BEEP_FILENAME = "edit_beep_1000Hz.wav"             # beep de aviso na contagem regressiva

# Empacotado (PyInstaller/Nuitka): <raiz do bundle>/assets. Em dev:
# .../src/compasso/gui_qt/assets.py -> parents[3] = raiz do repo -> /assets.
_base = base_recursos()
if _base is not None:
    ASSETS_DIR = _base / "assets"
else:
    ASSETS_DIR = Path(__file__).resolve().parents[3] / "assets"

__all__ = ["ASSETS_DIR", "ICON_FILENAME", "ICON_PNG_FILENAME", "BEEP_FILENAME"]
