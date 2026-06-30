"""Carregamento centralizado das imagens da GUI.

Resolve a pasta ``assets/`` a partir da localização deste arquivo (independente do
diretório de trabalho atual) e carrega todas as imagens uma única vez em objetos
``CTkImage``. Deve ser instanciado **após** a criação do root Tk (ex.: dentro de
``Compasso.__init__``), pois ``CTkImage`` depende do root.
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

        # Uniformiza o tamanho de cada grupo de imagens trocadas no mesmo botão.
        # Os PNGs originais diferem por 1–2 px (hover) ou ~8 px (estados do botão
        # principal); como o tamanho do botão acompanha o da imagem, a troca causava
        # um "pulo"/redimensionamento visível a cada hover/clique/mudança de estado.
        self._normalize_sizes((self.conect_bitalino, self.conect_bitalino_dim, self.conectado))
        self._normalize_sizes((self.comecar, self.comecar_dim, self.rodando,
                               self.rodando_dim, self.continuar, self.continuar_dim))

    @staticmethod
    def _normalize_sizes(images):
        """Força todas as imagens do grupo a terem o tamanho da primeira válida.

        Evita que a troca de imagem (hover/estado) altere o tamanho do botão e
        dispare um reflow do layout (o "glitch" de redimensionamento ao clicar).
        """
        ref = next((img.cget("size") for img in images if img is not None), None)
        if ref is None:
            return
        for img in images:
            if img is not None and img.cget("size") != ref:
                img.configure(size=ref)
