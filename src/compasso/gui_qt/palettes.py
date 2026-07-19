"""Dados de tema do ComPasso: paletas de cor, dimensões e fontes.

Módulo de dados puro (sem dependência de GUI): as seis paletas semânticas, a escala de
dimensões (raios, alturas, paddings) e as famílias/tamanhos de fonte. O objeto ``Theme``
(ver ``theme.py``) consome estes dicionários e os expõe ao QML de forma reativa.

As paletas são idênticas às da GUI antiga (``compasso.gui.theme``); foram copiadas para cá
para manter esta camada desacoplada do CustomTkinter durante a migração.
"""

import sys

# ---------------------------------------------------------------------------
# Paletas (dicionários de cores semânticas) — 18 chaves cada
# ---------------------------------------------------------------------------

PALETTE_TEAL = {
    "win_bg": "#0E1116", "bar_bg": "#161B22", "footer_bg": "#12161C",
    "border": "#21262d", "border_win": "#262c36", "input_bg": "#0E1116",
    "text": "#E6EDF3", "muted": "#8B949E", "faint": "#6E7681", "faint2": "#4B525C",
    "accent": "#2DD4BF", "accent_ink": "#04120F", "accent_tint": "#0C2B28", "accent_border": "#14463F",
    "success": "#34D399", "danger": "#F87171", "danger_tint": "#2A1515", "danger_border": "#7F2D2D",
}

PALETTE_IRIS = {
    "win_bg": "#0E0F17", "bar_bg": "#171826", "footer_bg": "#131324",
    "border": "#262838", "border_win": "#2A2C40", "input_bg": "#0E0F17",
    "text": "#E7E7F5", "muted": "#9A9BB5", "faint": "#6F6F8C", "faint2": "#4D4D68",
    "accent": "#7C74FF", "accent_ink": "#0C0A24", "accent_tint": "#1E1C3D", "accent_border": "#322F5C",
    "success": "#4ADE80", "danger": "#FB7185", "danger_tint": "#2A1620", "danger_border": "#7A2E46",
}

PALETTE_AMBER = {
    "win_bg": "#14120C", "bar_bg": "#1C1A12", "footer_bg": "#191710",
    "border": "#2B271A", "border_win": "#2F2B1C", "input_bg": "#14120C",
    "text": "#F2EEE2", "muted": "#B3A98F", "faint": "#837B64", "faint2": "#5C5540",
    "accent": "#F5A524", "accent_ink": "#241A04", "accent_tint": "#2E2410", "accent_border": "#4A3D1C",
    "success": "#8CC63F", "danger": "#F87171", "danger_tint": "#2A1A12", "danger_border": "#7A3F2D",
}

# CLARO · frio — acento azul-céu suave
PALETTE_SERENO = {
    "win_bg": "#F6F8FB", "bar_bg": "#FFFFFF", "footer_bg": "#EEF2F7",
    "border": "#E2E7EF", "border_win": "#D6DDE7", "input_bg": "#FFFFFF",
    "text": "#1B2430", "muted": "#5A6675", "faint": "#8A94A3", "faint2": "#B4BCC7",
    "accent": "#4F86E8", "accent_ink": "#FFFFFF", "accent_tint": "#E8F1FE", "accent_border": "#C6DBF9",
    "success": "#1FA97C", "danger": "#E04B54", "danger_tint": "#FCECEE", "danger_border": "#F3C4C8",
}

# CLARO · quente — acento coral-pêssego suave
PALETTE_AURORA = {
    "win_bg": "#FBF7F4", "bar_bg": "#FFFFFF", "footer_bg": "#F5EEE9",
    "border": "#ECE3DC", "border_win": "#E1D6CD", "input_bg": "#FFFFFF",
    "text": "#2A211E", "muted": "#6E605A", "faint": "#9A8B83", "faint2": "#C6B9B1",
    "accent": "#E2865F", "accent_ink": "#2A140B", "accent_tint": "#FBEAE1", "accent_border": "#F2D0BF",
    "success": "#4FA97C", "danger": "#D6455A", "danger_tint": "#FBE8EB", "danger_border": "#F0BFC7",
}

# ESCURO — acento verde-esmeralda / menta suave
PALETTE_FLORESTA = {
    "win_bg": "#0F1512", "bar_bg": "#161E1A", "footer_bg": "#121814",
    "border": "#232E27", "border_win": "#2A362E", "input_bg": "#0F1512",
    "text": "#E8F0EA", "muted": "#93A399", "faint": "#6E7D73", "faint2": "#4A564E",
    "accent": "#5ED6A0", "accent_ink": "#04140C", "accent_tint": "#0E2A1F", "accent_border": "#1C4736",
    "success": "#4ADE80", "danger": "#F0868A", "danger_tint": "#2A1618", "danger_border": "#7A3038",
}

# Registro de paletas, indexadas pelo nome exibido no menu "Tema".
PALETTES = {
    "Teal": PALETTE_TEAL,
    "Iris": PALETTE_IRIS,
    "Amber": PALETTE_AMBER,
    "Sereno": PALETTE_SERENO,
    "Aurora": PALETTE_AURORA,
    "Floresta": PALETTE_FLORESTA,
}
THEME_NAMES = list(PALETTES)

# Paleta padrão ao abrir sem preferência salva.
PALETTE_PADRAO = "Teal"

# Quais paletas são claras (o QML pode ajustar sombras/realces conforme luminosidade).
PALETAS_CLARAS = {"Sereno", "Aurora"}

# Padrões de cada família para o botão sol/lua da barra de menus, usados quando ainda não há
# um "último tema usado" daquela família nesta sessão (ver Theme.alternarClaroEscuro).
TEMA_CLARO_PADRAO = "Aurora"
TEMA_ESCURO_PADRAO = "Teal"

# ---------------------------------------------------------------------------
# Dimensões / layout (nomes camelCase p/ exposição direta ao QML)
# ---------------------------------------------------------------------------
# Tamanho preferido de abertura (a janela abre assim quando a tela comporta).
WIN_PREF_WIDTH: int = 1300
WIN_PREF_HEIGHT: int = 720
# Tamanho minimo absoluto: permite abrir/redimensionar em telas pequenas sem quebrar o
# layout (o conteudo principal e rolavel, entao encolher so ativa a barra de rolagem).
WIN_MIN_WIDTH: int = 600
WIN_MIN_HEIGHT: int = 400

METRICS = {
    "winPrefWidth": WIN_PREF_WIDTH,
    "winPrefHeight": WIN_PREF_HEIGHT,
    "winMinWidth": WIN_MIN_WIDTH,
    "winMinHeight": WIN_MIN_HEIGHT,
    # Raios de canto
    "cornerCard": 14,     # cartões
    "cornerSm": 9,        # campos/botões
    "cornerPill": 999,    # pills/barras de progresso
    "cornerChip": 6,      # chips (ex.: condição no player)
    # Alturas de widgets recorrentes
    "inputH": 36,         # entradas de texto / combobox
    "btnH": 38,           # botões padrão
    "actionBtnH": 48,     # botão principal do rodapé
    "titleBarH": 40,      # barra de título custom (frameless)
    # Escala de espaçamento
    "padSm": 8,
    "padMd": 16,
    "padLg": 22,
    # Durações de animação (ms). Chaves terminadas em "Ms" NÃO são multiplicadas pela escala
    # da UI — ver Theme._escalar: tempo não é tamanho.
    "animJanelaMs": 220,   # maximizar/restaurar da janela frameless
}

# ---------------------------------------------------------------------------
# Fontes (famílias por plataforma; escala de tamanhos)
# ---------------------------------------------------------------------------
if sys.platform == "darwin":
    DISPLAY_FAMILY, MONO_FAMILY = "SF Pro Display", "Menlo"
elif sys.platform.startswith("win"):
    DISPLAY_FAMILY, MONO_FAMILY = "Segoe UI", "Consolas"
else:
    DISPLAY_FAMILY, MONO_FAMILY = "DejaVu Sans", "DejaVu Sans Mono"

FONTS = {
    "display": DISPLAY_FAMILY,
    "mono": MONO_FAMILY,
    # Escala de tamanhos usada na UI (9..19)
    "s9": 9, "s10": 10, "s11": 11, "s12": 12, "s13": 13,
    "s14": 14, "s15": 15, "s16": 16, "s17": 17, "s18": 18, "s19": 19,
}
