"""Helpers de GUI compartilhados: diálogos, cartão base e fábricas de widgets
estilizados (tema escuro).

Concentram a repetição de kwargs de estilo e padrões duplicados que antes apareciam
em cada frame (caixas de mensagem, cartões, rótulos, botões). As cores e tamanhos vêm
sempre das constantes semânticas de `theme.py` — trocar a paleta/escala ativa lá
recolore/redimensiona todos estes helpers.
"""

import customtkinter as ctk
from CTkMessagebox import CTkMessagebox

from .theme import (WIN_BG, BAR_BG, BORDER, INPUT_BG, TEXT, MUTED, FAINT,
                    ACCENT, ACCENT_INK, ACCENT_TINT, SUCCESS, DANGER, DANGER_TINT,
                    DANGER_BORDER, TRANSPARENTE, DISPLAY_FAMILY, MONO_FAMILY,
                    BASE_FONT_MIN, CORNER, CORNER_SM,
                    FONT_SM, FONT_BASE, FONT_MD, FONT_XL)


# ---------------------------------------------------------------------------
# Caixas de diálogo (mensagem e confirmação) — estilo escuro compartilhado
# ---------------------------------------------------------------------------
# Kwargs visuais comuns a todas as CTkMessagebox do app (mensagem e confirmação),
# para não repetir a paleta em cada chamada.
_MSGBOX_STYLE = dict(
    fg_color=BAR_BG, bg_color=WIN_BG, text_color=TEXT, button_color=INPUT_BG,
    button_hover_color=BORDER, font=BASE_FONT_MIN, border_color=BORDER,
    border_width=1, title_color=TEXT, button_text_color=TEXT,
    corner_radius=CORNER, width=500, height=300,
)


def show_message(title: str, message: str, icon: str = "cancel") -> None:
    """Exibe uma CTkMessagebox informativa (botão único "OK") no estilo do ComPasso.

    Deve ser chamada na thread da GUI (use `ctx.run_after(...)` a partir de threads
    de trabalho).
    """
    CTkMessagebox(title=title, message=message, icon=icon, option_1="OK",
                  sound=True, **_MSGBOX_STYLE) #type: ignore


def confirm(title: str, message: str) -> bool:
    """Diálogo de confirmação Sim/Não no estilo padrão. Retorna True se o usuário escolher 'Sim'."""
    box = CTkMessagebox(title=title, message=message, icon="question",
                        option_1="Não", option_2="Sim", **_MSGBOX_STYLE) #type: ignore
    return box.get() == "Sim"


# ---------------------------------------------------------------------------
# Cartão base do redesign
# ---------------------------------------------------------------------------

class Card(ctk.CTkFrame):
    """Cartão escuro base (fundo, borda e cantos padronizados do redesign).

    Frames que são "cartões" (conexão, stepper, participante, arquivos, player)
    herdam desta classe em vez de repetir os mesmos kwargs de estilo.
    """

    def __init__(self, master, **kwargs):
        opts = dict(fg_color=BAR_BG, border_width=1, border_color=BORDER, corner_radius=CORNER)
        opts.update(kwargs)
        super().__init__(master, **opts) #type: ignore


# ---------------------------------------------------------------------------
# Fábricas de widgets estilizados
# ---------------------------------------------------------------------------

def styled_label(master, **kwargs):
    """CTkLabel com o estilo padrão (fonte mínima, texto principal, fundo transparente)."""
    opts = dict(font=BASE_FONT_MIN, text_color=TEXT, bg_color=TRANSPARENTE, fg_color=TRANSPARENTE)
    opts.update(kwargs)
    return ctk.CTkLabel(master, **opts)  # type: ignore

def styled_button(master, **kwargs):
    """CTkButton escuro com cantos/borda/fonte padrão.

    Sem cor de fundo explícita, usa o acento (call-to-action). Passe `fg_color`/`text_color`
    para variações (ex.: botão fantasma ou de perigo).
    """
    opts = dict(corner_radius=CORNER_SM, border_width=0, fg_color=ACCENT,
                hover_color=ACCENT, text_color=ACCENT_INK,
                font=ctk.CTkFont(DISPLAY_FAMILY, FONT_MD, weight="bold"))
    opts.update(kwargs)
    return ctk.CTkButton(master, **opts)  # type: ignore

def styled_entry(master, **kwargs):
    """CTkEntry com o estilo escuro dos campos do formulário."""
    opts = dict(corner_radius=CORNER_SM, border_width=1, border_color=BORDER,
                bg_color=TRANSPARENTE, fg_color=INPUT_BG, placeholder_text_color=FAINT,
                font=ctk.CTkFont(DISPLAY_FAMILY, FONT_MD), text_color=TEXT)
    opts.update(kwargs)
    return ctk.CTkEntry(master, **opts)  # type: ignore

def styled_combobox(master, **kwargs):
    """CTkComboBox com o estilo escuro padrão."""
    opts = dict(corner_radius=CORNER_SM, border_width=1, border_color=BORDER,
                bg_color=TRANSPARENTE, fg_color=INPUT_BG, button_color=INPUT_BG,
                button_hover_color=BORDER, dropdown_fg_color=BAR_BG,
                dropdown_hover_color=ACCENT_TINT, text_color=TEXT,
                dropdown_text_color=TEXT, justify=ctk.CENTER,
                font=ctk.CTkFont(MONO_FAMILY, FONT_MD), dropdown_font=ctk.CTkFont(MONO_FAMILY, FONT_MD))
    opts.update(kwargs)
    return ctk.CTkComboBox(master, **opts)  # type: ignore

# ---------------------------------------------------------------------------
# Componentes do redesign (rótulos tipográficos, badges)
# ---------------------------------------------------------------------------

def title(master, text, size=FONT_XL, **kwargs):
    """Título de cartão (display, negrito)."""
    return ctk.CTkLabel(master, text=text, text_color=TEXT,
                        font=ctk.CTkFont(DISPLAY_FAMILY, size, weight="bold"), **kwargs)

def caption(master, text, color=None, **kwargs):
    """Rótulo pequeno/apagado (caption em maiúsculas)."""
    return ctk.CTkLabel(master, text=text, text_color=color or FAINT,
                        font=ctk.CTkFont(DISPLAY_FAMILY, FONT_SM, weight="bold"), **kwargs)

def mono(master, text, size=FONT_MD, color=None, **kwargs):
    """Rótulo monoespaçado (caminhos, tempos, contadores)."""
    return ctk.CTkLabel(master, text=text, text_color=color or TEXT,
                        font=ctk.CTkFont(MONO_FAMILY, size), **kwargs)

def ghost_button(master, text, command=None, size=FONT_MD, **kwargs):
    """Botão secundário 'fantasma' (fundo do input, borda sutil, texto apagado)."""
    opts = dict(text=text, command=command, fg_color=INPUT_BG, hover_color=BORDER,
                text_color=MUTED, border_width=1, border_color=BORDER,
                corner_radius=CORNER_SM, font=ctk.CTkFont(DISPLAY_FAMILY, size))
    opts.update(kwargs)
    return ctk.CTkButton(master, **opts)  # type: ignore

def danger_button(master, text, command=None, size=FONT_MD, **kwargs):
    """Botão de perigo (parar/gravando) em tons de vermelho."""
    opts = dict(text=text, command=command, fg_color=DANGER_TINT, hover_color=DANGER_BORDER,
                text_color=DANGER, border_width=1, border_color=DANGER_BORDER,
                corner_radius=CORNER_SM, font=ctk.CTkFont(DISPLAY_FAMILY, size, weight="bold"))
    opts.update(kwargs)
    return ctk.CTkButton(master, **opts)  # type: ignore

def circle(master, text, filled=True, size=28, **kwargs):
    """Badge circular (stepper, avatar do participante)."""
    return ctk.CTkLabel(
        master, text=text, width=size, height=size, corner_radius=size // 2,
        fg_color=ACCENT if filled else ACCENT_TINT,
        text_color=ACCENT_INK if filled else ACCENT,
        font=ctk.CTkFont(DISPLAY_FAMILY, FONT_MD, weight="bold"), **kwargs)

def check_icon(master, done=True, size=22, radius=7, text="✓", fg_color=ACCENT_TINT, **kwargs):
    """Ícone de check de uma linha de arquivo (verde quando pronto, apagado quando não)."""
    return ctk.CTkLabel(master, text=text, width=size, height=size,
                        corner_radius=radius, fg_color=fg_color,
                        text_color=SUCCESS if done else FAINT,
                        font=ctk.CTkFont(DISPLAY_FAMILY, FONT_BASE, weight="bold"), **kwargs)
