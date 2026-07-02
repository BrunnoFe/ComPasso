import customtkinter as ctk

from ..theme import WIN_BG, BORDER_WIN, FAINT2, TRANSPARENTE, CORNER, MONO_FAMILY, FONT_SM

class GraphPlaceholder(ctk.CTkFrame):
    """Espaço reservado para o gráfico do sinal em tempo real (ainda não implementado).

    Caixa escura com borda tênue e uma legenda monoespaçada — puramente visual, sem lógica.
    """

    def __init__(self, master, ctx=None):
        super().__init__(master, fg_color=WIN_BG, height=50, corner_radius=CORNER,
                         border_width=1, border_color=BORDER_WIN)
        self.pack_propagate(False)
        ctk.CTkLabel(self, text="ESPAÇO RESERVADO · GRÁFICO EM TEMPO REAL · EM BREVE",
                     text_color=FAINT2, bg_color=TRANSPARENTE,
                     font=ctk.CTkFont(MONO_FAMILY, FONT_SM)).pack(expand=True)
