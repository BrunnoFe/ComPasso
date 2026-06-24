"""Constantes visuais compartilhadas da GUI (cores, fontes e dimensões).

Centralizadas aqui para que todos os frames e helpers reutilizem o mesmo tema,
evitando a repetição dessas constantes em cada módulo.
"""

# Dimensões / layout
WIN_MIN_WIDTH: int = 1280
WIN_MIN_HEIGHT: int = 768
BORDER_WIDTH: int = 5
BORDER_WIDTH_INSIDE: int = 8
CORNER: int = 30

# Paleta de cores
AZUL: str = "#99acff"
AZUL_CLARO: str = "#c2cdff"
CINZA: str = "#806e86"
ROSA: str = "#edcbf6"
AMARELO: str = "#ffc700"
AMARELO_ESC: str = "#b68e00"
TRANSPARENTE: str = "transparent"

# Fontes
BASE_FONT: tuple = ("Helvetica", 16, "bold")
BASE_FONT_MED: tuple = ("Helvetica", 14, "bold")
BASE_FONT_MIN: tuple = ("Helvetica", 12, "bold")

# Atalho de sticky usado com frequência
NSE: str = "nse"
