"""Constantes visuais compartilhadas da GUI (cores, fontes e dimensões).

Tema escuro do ComPasso. Três paletas estão disponíveis (Teal/Iris/Amber); a paleta
ativa é escolhida por `THEME` — trocar essa única linha recolore toda a interface. As
constantes semânticas (WIN_BG, ACCENT, TEXT...) derivam de `THEME` e são importadas pelos
frames e helpers, evitando repetir cores em cada módulo.
"""

# ---------------------------------------------------------------------------
# Paletas (dicionários de cores semânticas)
# ---------------------------------------------------------------------------

# Paleta 2a — Teal (padrão)
PALETTE_TEAL = {
    "win_bg":        "#0E1116",   # fundo da janela
    "bar_bg":        "#161B22",   # barra de título / menu / cartões
    "footer_bg":     "#12161C",   # rodapé
    "border":        "#21262d",   # bordas de cartões e campos
    "border_win":    "#262c36",   # borda externa da janela / placeholder
    "input_bg":      "#0E1116",   # fundo de campos e botões secundários

    "text":          "#E6EDF3",   # texto principal
    "muted":         "#8B949E",   # texto secundário
    "faint":         "#6E7681",   # rótulos / caption
    "faint2":        "#4B525C",   # números apagados (/12)

    "accent":        "#2DD4BF",   # acento (teal)
    "accent_ink":    "#04120F",   # texto sobre o acento
    "accent_tint":   "#0C2B28",   # fundo tênue do acento (badges, chips)
    "accent_border": "#14463F",   # borda do pill conectado
 
    "success":       "#34D399",   # ponto "conectado" / checks
    "danger":        "#F87171",   # gravando / parar
    "danger_tint":   "#2A1515",
    "danger_border": "#7F2D2D",
}

PALETTE_IRIS = {
    "win_bg":        "#0E0F17", 
    "bar_bg":        "#171826", 
    "footer_bg":     "#131324",
    "border":        "#262838", 
    "border_win":    "#2A2C40", 
    "input_bg":      "#0E0F17",

    "text":          "#E7E7F5", 
    "muted":         "#9A9BB5", 
    "faint":         "#6F6F8C", 
    "faint2":        "#4D4D68",

    "accent":        "#7C74FF", 
    "accent_ink":    "#0C0A24", 
    "accent_tint":   "#1E1C3D",
    "accent_border": "#322F5C", 

    "success":       "#4ADE80",
    "danger":        "#FB7185", 
    "danger_tint":   "#2A1620", 
    "danger_border": "#7A2E46",
}

PALETTE_AMBER = {
    "win_bg":        "#14120C", 
    "bar_bg":        "#1C1A12", 
    "footer_bg":     "#191710",
    "border":        "#2B271A", 
    "border_win":    "#2F2B1C", 
    "input_bg":      "#14120C",

    "text":          "#F2EEE2", 
    "muted":         "#B3A98F", 
    "faint":         "#837B64", 
    "faint2":        "#5C5540",

    "accent":        "#F5A524",
    "accent_ink":    "#241A04", 
    "accent_tint":   "#2E2410",
    "accent_border": "#4A3D1C", 
    
    "success":       "#8CC63F",
    "danger":        "#F87171", 
    "danger_tint":   "#2A1A12", 
    "danger_border": "#7A3F2D",
}

# ---------------------------------------------------------------------------
# CLARO · frio — acento azul-céu suave
# ---------------------------------------------------------------------------
PALETTE_SERENO = {
    "win_bg":        "#F6F8FB",   # fundo da janela (branco-azulado)
    "bar_bg":        "#FFFFFF",   # barra de título / menu / cartões
    "footer_bg":     "#EEF2F7",   # rodapé
    "border":        "#E2E7EF",   # bordas de cartões e campos
    "border_win":    "#D6DDE7",   # borda externa da janela / placeholder
    "input_bg":      "#FFFFFF",   # fundo de campos e botões secundários

    "text":          "#1B2430",   # texto principal (azul-noite)
    "muted":         "#5A6675",   # texto secundário
    "faint":         "#8A94A3",   # rótulos / caption
    "faint2":        "#B4BCC7",   # números apagados (/12)

    "accent":        "#4F86E8",   # acento (azul-céu suave)
    "accent_ink":    "#FFFFFF",   # texto sobre o acento
    "accent_tint":   "#E8F1FE",   # fundo tênue do acento (badges, chips)
    "accent_border": "#C6DBF9",   # borda do pill conectado

    "success":       "#1FA97C",   # ponto "conectado" / checks
    "danger":        "#E04B54",   # gravando / parar
    "danger_tint":   "#FCECEE",
    "danger_border": "#F3C4C8",
}

# ---------------------------------------------------------------------------
# CLARO · quente — acento coral-pêssego suave
# ---------------------------------------------------------------------------
PALETTE_AURORA = {
    "win_bg":        "#FBF7F4",   # fundo da janela (marfim quente)
    "bar_bg":        "#FFFFFF",   # barra de título / menu / cartões
    "footer_bg":     "#F5EEE9",   # rodapé
    "border":        "#ECE3DC",   # bordas de cartões e campos
    "border_win":    "#E1D6CD",   # borda externa da janela / placeholder
    "input_bg":      "#FFFFFF",   # fundo de campos e botões secundários

    "text":          "#2A211E",   # texto principal (marrom-quase-preto)
    "muted":         "#6E605A",   # texto secundário
    "faint":         "#9A8B83",   # rótulos / caption
    "faint2":        "#C6B9B1",   # números apagados (/12)

    "accent":        "#E2865F",   # acento (coral-pêssego suave)
    "accent_ink":    "#2A140B",   # texto sobre o acento
    "accent_tint":   "#FBEAE1",   # fundo tênue do acento (badges, chips)
    "accent_border": "#F2D0BF",   # borda do pill conectado

    "success":       "#4FA97C",   # ponto "conectado" / checks
    "danger":        "#D6455A",   # gravando / parar
    "danger_tint":   "#FBE8EB",
    "danger_border": "#F0BFC7",
}

# ---------------------------------------------------------------------------
# ESCURO — acento verde-esmeralda / menta suave
# ---------------------------------------------------------------------------
PALETTE_FLORESTA = {
    "win_bg":        "#0F1512",   # fundo da janela (verde-quase-preto)
    "bar_bg":        "#161E1A",   # barra de título / menu / cartões
    "footer_bg":     "#121814",   # rodapé
    "border":        "#232E27",   # bordas de cartões e campos
    "border_win":    "#2A362E",   # borda externa da janela / placeholder
    "input_bg":      "#0F1512",   # fundo de campos e botões secundários

    "text":          "#E8F0EA",   # texto principal (branco-esverdeado)
    "muted":         "#93A399",   # texto secundário
    "faint":         "#6E7D73",   # rótulos / caption
    "faint2":        "#4A564E",   # números apagados (/12)

    "accent":        "#5ED6A0",   # acento (verde-menta suave)
    "accent_ink":    "#04140C",   # texto sobre o acento
    "accent_tint":   "#0E2A1F",   # fundo tênue do acento (badges, chips)
    "accent_border": "#1C4736",   # borda do pill conectado

    "success":       "#4ADE80",   # ponto "conectado" / checks
    "danger":        "#F0868A",   # gravando / parar
    "danger_tint":   "#2A1618",
    "danger_border": "#7A3038",
}

# Registro de paletas disponíveis, indexadas pelo nome exibido no menu "Tema".
PALETTES = {
    "Teal":  PALETTE_TEAL,
    "Iris":  PALETTE_IRIS,
    "Amber": PALETTE_AMBER,
    "Sereno":   PALETTE_SERENO,
    "Aurora":   PALETTE_AURORA,
    "Floresta": PALETTE_FLORESTA
}
THEME_NAMES = list(PALETTES)

# >>> Paleta ativa (troque por PALETTE_IRIS ou PALETTE_AMBER para recolorir tudo) <<<
THEME = PALETTE_TEAL
_CURRENT = "Teal"

# ---------------------------------------------------------------------------
# Constantes semânticas de cor (derivadas da paleta ativa)
# ---------------------------------------------------------------------------
WIN_BG: str = THEME["win_bg"]
BAR_BG: str = THEME["bar_bg"]
FOOTER_BG: str = THEME["footer_bg"]
BORDER: str = THEME["border"]
BORDER_WIN: str = THEME["border_win"]
INPUT_BG: str = THEME["input_bg"]

TEXT: str = THEME["text"]
MUTED: str = THEME["muted"]
FAINT: str = THEME["faint"]
FAINT2: str = THEME["faint2"]

ACCENT: str = THEME["accent"]
ACCENT_INK: str = THEME["accent_ink"]
ACCENT_TINT: str = THEME["accent_tint"]
ACCENT_BORDER: str = THEME["accent_border"]

SUCCESS: str = THEME["success"]
DANGER: str = THEME["danger"]
DANGER_TINT: str = THEME["danger_tint"]
DANGER_BORDER: str = THEME["danger_border"]

TRANSPARENTE: str = "transparent"

# ---------------------------------------------------------------------------
# Troca de tema em tempo de execução
# ---------------------------------------------------------------------------
# Mapa chave-da-paleta -> nome da constante semântica global (mesma correspondência
# do bloco de derivação acima). Usado por `set_theme` para reescrever as constantes.
_COLOR_MAP = {
    "win_bg": "WIN_BG", "bar_bg": "BAR_BG", "footer_bg": "FOOTER_BG",
    "border": "BORDER", "border_win": "BORDER_WIN", "input_bg": "INPUT_BG",
    "text": "TEXT", "muted": "MUTED", "faint": "FAINT", "faint2": "FAINT2",
    "accent": "ACCENT", "accent_ink": "ACCENT_INK", "accent_tint": "ACCENT_TINT",
    "accent_border": "ACCENT_BORDER", "success": "SUCCESS", "danger": "DANGER",
    "danger_tint": "DANGER_TINT", "danger_border": "DANGER_BORDER",
}


def _assign(palette: dict) -> None:
    """Reescreve, no namespace deste módulo, todas as constantes semânticas a partir de `palette`."""
    g = globals()
    for chave, nome in _COLOR_MAP.items():
        g[nome] = palette[chave]


def set_theme(name: str) -> bool:
    """Troca a paleta ativa em tempo de execução e propaga as cores aos módulos já importados.

    Como os frames importam as constantes por valor (`from ..theme import WIN_BG`), reescrever
    apenas este módulo não bastaria; por isso as novas cores são injetadas no namespace de cada
    módulo `src.gui.*` já carregado. Widgets construídos depois disso (após reconstruir a UI)
    passam a usar a nova paleta.

    :param name: nome da paleta (chave de `PALETTES`, ex.: "Teal").
    :return: True se a paleta existe e foi aplicada; False se `name` é desconhecido.
    """
    import sys

    global THEME, _CURRENT
    palette = PALETTES.get(name)
    if palette is None:
        return False

    THEME = palette
    _CURRENT = name
    _assign(palette)

    novos = {nome: globals()[nome] for nome in _COLOR_MAP.values()}
    for modname, mod in list(sys.modules.items()):
        if mod is None or modname == __name__ or not modname.startswith("src.gui"):
            continue
        for nome, valor in novos.items():
            if hasattr(mod, nome):
                setattr(mod, nome, valor)
    return True


def current_theme_name() -> str:
    """Retorna o nome da paleta ativa (chave de `PALETTES`)."""
    return _CURRENT


# ---------------------------------------------------------------------------
# Dimensões / layout
# ---------------------------------------------------------------------------
WIN_MIN_WIDTH: int = 1280
WIN_MIN_HEIGHT: int = 768

# Raios de canto
CORNER: int = 14          # raio dos cartões
CORNER_SM: int = 9        # raio de campos/botões
CORNER_PILL: int = 999    # totalmente arredondado (pills, barras de progresso)
CORNER_CHIP: int = 6      # chips (ex.: condição no player)

# Alturas de widgets recorrentes
INPUT_H: int = 36         # entradas de texto / optionmenu
BTN_H: int = 38           # botões padrão (conectar, ghost, parar)
ACTION_BTN_H: int = 48    # botão principal do rodapé ("Começar")

# Escala de espaçamento (paddings recorrentes; one-offs assimétricos ficam inline)
PAD_SM: int = 8
PAD_MD: int = 16
PAD_LG: int = 22

# ---------------------------------------------------------------------------
# Fontes
# ---------------------------------------------------------------------------
import sys as _sys

if _sys.platform == "darwin":
    DISPLAY_FAMILY, MONO_FAMILY = "SF Pro Display", "Menlo"
elif _sys.platform.startswith("win"):
    DISPLAY_FAMILY, MONO_FAMILY = "Segoe UI", "Consolas"
else:
    DISPLAY_FAMILY, MONO_FAMILY = "DejaVu Sans", "DejaVu Sans Mono"

# Escala de tamanhos de fonte (cobre os tamanhos usados na UI: 9,10,11,12,13,14,15,17,18,19).
# Trocar um valor aqui reflete em todos os widgets que usam o mesmo nível.
FONT_2XS: int = 9
FONT_XS: int = 10
FONT_SM: int = 11
FONT_BASE: int = 12
FONT_MD: int = 13
FONT_LG: int = 14
FONT_XL: int = 15
FONT_2XL: int = 17
FONT_3XL: int = 18
FONT_4XL: int = 19

BASE_FONT: tuple = (DISPLAY_FAMILY, 16, "bold")
BASE_FONT_MIN: tuple = (DISPLAY_FAMILY, FONT_BASE, "bold")
