"""Helpers de GUI compartilhados: diálogos, carregamento de imagens, hover e
fábricas de widgets estilizados.

Concentram a repetição de kwargs de estilo e padrões duplicados que antes apareciam
em cada frame (caixas de mensagem, troca de imagem no hover, criação de imagens).
"""

import customtkinter as ctk
from CTkMessagebox import CTkMessagebox
from PIL import Image

from . import gui_logger
from .theme import (AZUL, AZUL_CLARO, CINZA, ROSA, AMARELO, TRANSPARENTE,
                    BASE_FONT_MIN, BORDER_WIDTH, CORNER)


def show_message(title: str, message: str, icon: str = "cancel") -> None:
    """Exibe uma CTkMessagebox com o estilo padrão do Compasso.

    Deve ser chamada na thread da GUI (use `ctx.run_after(...)` a partir de threads
    de trabalho).
    """
    CTkMessagebox(title=title, message=message, icon=icon, option_1="OK",
                  fg_color=ROSA, bg_color=AZUL, text_color=CINZA, button_color=AZUL_CLARO,
                  button_hover_color=AMARELO, font=BASE_FONT_MIN, border_color=AZUL,
                  border_width=BORDER_WIDTH, title_color=CINZA, button_text_color=CINZA,
                  corner_radius=CORNER, sound=True, width=500, height=300)


def load_image(path: str, fallback=None):
    """Carrega `path` como `ctk.CTkImage`; retorna `fallback` se o arquivo faltar."""
    try:
        img = Image.open(path)
        return ctk.CTkImage(light_image=img, dark_image=img, size=(img.width, img.height))
    except Exception as e:
        gui_logger.logger.warning(f"Imagem ausente: {path} ({e}). Usando fallback.")
        return fallback


def bind_hover_images(button, normal, dim, only_when_enabled: bool = False) -> None:
    """Faz o botão trocar `normal`<->`dim` ao passar o mouse.

    :param only_when_enabled: se True, só escurece quando o botão não está desabilitado.
    """
    if only_when_enabled:
        button.bind('<Enter>', lambda event: button.configure(image=dim) if button.cget("state") != "disabled" else None)
    else:
        button.bind('<Enter>', lambda event: button.configure(image=dim))
    button.bind('<Leave>', lambda event: button.configure(image=normal))


def styled_label(master, **kwargs):
    """CTkLabel com o estilo padrão (fonte mínima, texto cinza, fundo transparente)."""
    opts = dict(font=BASE_FONT_MIN, text_color=CINZA, bg_color=TRANSPARENTE, fg_color=TRANSPARENTE)
    opts.update(kwargs)
    return ctk.CTkLabel(master, **opts)


def styled_button(master, **kwargs):
    """CTkButton com bordas/cantos/fonte padrão (cores de fundo passadas pelo chamador)."""
    opts = dict(corner_radius=CORNER, border_width=BORDER_WIDTH, border_color=AZUL,
                hover_color=AZUL, font=BASE_FONT_MIN, text_color=CINZA)
    opts.update(kwargs)
    return ctk.CTkButton(master, **opts)


def styled_entry(master, **kwargs):
    """CTkEntry com o estilo padrão dos campos do formulário."""
    opts = dict(corner_radius=CORNER, border_width=BORDER_WIDTH, border_color=AZUL,
                bg_color=AZUL_CLARO, fg_color=ROSA, placeholder_text_color=CINZA,
                font=BASE_FONT_MIN, text_color=CINZA)
    opts.update(kwargs)
    return ctk.CTkEntry(master, **opts)


def styled_combobox(master, **kwargs):
    """CTkComboBox com o estilo padrão (cores rosa/azul, fonte mínima)."""
    opts = dict(corner_radius=CORNER, border_width=BORDER_WIDTH, border_color=AZUL,
                bg_color=ROSA, fg_color=ROSA, button_color=AZUL, button_hover_color=AMARELO,
                dropdown_fg_color=ROSA, dropdown_hover_color=AZUL_CLARO, text_color=CINZA,
                dropdown_text_color=CINZA, justify=ctk.CENTER, font=BASE_FONT_MIN,
                dropdown_font=BASE_FONT_MIN)
    opts.update(kwargs)
    return ctk.CTkComboBox(master, **opts)
