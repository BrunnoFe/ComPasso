"""Carregamento centralizado das imagens da GUI.

Resolve a pasta ``assets/`` a partir da localização deste arquivo (independente do
diretório de trabalho atual) e carrega todas as imagens uma única vez em objetos
``CTkImage``. Deve ser instanciado **após** a criação do root Tk (ex.: dentro de
``Compasso.__init__``), pois ``CTkImage`` depende do root.
"""

from pathlib import Path

from .widgets import load_image

# .../src/gui/assets.py -> parents[2] = raiz do repositório -> /assets
ASSETS_DIR = Path(__file__).resolve().parents[2] / "assets"


def _asset(name: str) -> str:
    return str(ASSETS_DIR / name)


class AppImages:
    """Cache de todas as imagens da GUI, carregadas uma vez após o root existir."""

    def __init__(self):
        self.logo = load_image(_asset("logo.png"))

        self.conect_bitalino = load_image(_asset("conect_bitalino.png"))
        self.conect_bitalino_dim = load_image(_asset("conect_bitalino_dim.png"))
        self.conectado = load_image(_asset("conectado.png"))

        # estados do botão principal; rodando/continuar recaem em começar se faltarem
        self.comecar = load_image(_asset("comecar.png"))
        self.comecar_dim = load_image(_asset("comecar_dim.png"))
        self.rodando = load_image(_asset("rodando.png"), fallback=self.comecar)
        self.rodando_dim = load_image(_asset("rodando_dim.png"), fallback=self.comecar_dim)
        self.continuar = load_image(_asset("continuar.png"), fallback=self.comecar)
        self.continuar_dim = load_image(_asset("continuar_dim.png"), fallback=self.comecar_dim)
