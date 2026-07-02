"""Carregamento centralizado das imagens da GUI.

Resolve a pasta ``assets/`` a partir da localização deste arquivo (independente do
diretório de trabalho atual) e carrega todas as imagens uma única vez em objetos
``CTkImage``. Deve ser instanciado **após** a criação do root Tk (ex.: dentro de
``ComPasso.__init__``), pois ``CTkImage`` depende do root.
"""

import sys
from pathlib import Path

from .widgets import load_image

# Em desenvolvimento: .../src/gui/assets.py -> parents[2] = raiz do repositório -> /assets.
# Empacotado (PyInstaller): os dados ficam em sys._MEIPASS/assets. O comportamento em
# desenvolvimento é idêntico ao anterior.
if getattr(sys, "frozen", False):
    ASSETS_DIR = Path(getattr(sys, "_MEIPASS", ".")) / "assets"
else:
    ASSETS_DIR = Path(__file__).resolve().parents[2] / "assets"


def _asset(name: str) -> str:
    return str(ASSETS_DIR / name)


class AppImages:
    """Cache de todas as imagens da GUI, carregadas uma vez após o root existir."""

    def __init__(self):
        self.logo = load_image(_asset("logo.png"))