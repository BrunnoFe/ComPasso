import customtkinter as ctk

from ..theme import (BORDER, TEXT, FAINT, ACCENT, ACCENT_INK, ACCENT_TINT,
                     TRANSPARENTE, DISPLAY_FAMILY, FONT_XS, FONT_MD, FONT_LG)
from ..widgets import Card


class StepperFrame(Card):
    """Indicador de progresso em 4 etapas (Conectar → Participante → Arquivos → Iniciar).

    Funcional: as etapas acendem conforme o estado real do `AppContext`. Registra
    `ctx.refresh_stepper = self.refresh`; qualquer frame que mude o estado chama
    `ctx.notify_stepper()` para re-renderizar (sempre na thread da GUI).
    """

    STEPS = ("Conectar", "Participante", "Arquivos", "Iniciar")

    def __init__(self, master, ctx):
        super().__init__(master)
        self.ctx = ctx

        row = ctk.CTkFrame(self, fg_color=TRANSPARENTE)
        row.pack(fill="x", padx=22, pady=14)

        self._badges = []
        self._tops = []
        self._labels = []
        self._connectors = [] 

        for i, label in enumerate(self.STEPS):
            item = ctk.CTkFrame(row, fg_color=TRANSPARENTE)
            item.pack(side="left")

            badge = ctk.CTkLabel(item, text=str(i + 1), width=28, height=28, corner_radius=14,
                                 fg_color=ACCENT_TINT, text_color=ACCENT,
                                 font=ctk.CTkFont(DISPLAY_FAMILY, FONT_MD, weight="bold"))
            badge.pack(side="left", padx=(0, 11))
            self._badges.append(badge)

            texts = ctk.CTkFrame(item, fg_color=TRANSPARENTE)
            texts.pack(side="left")
            top = ctk.CTkLabel(texts, text=f"ETAPA {i + 1}", text_color=FAINT,
                               font=ctk.CTkFont(DISPLAY_FAMILY, FONT_XS, weight="bold"))
            top.pack(anchor="w")
            self._tops.append(top)
            lab = ctk.CTkLabel(texts, text=label, text_color=TEXT,
                               font=ctk.CTkFont(DISPLAY_FAMILY, FONT_LG, weight="bold"))
            lab.pack(anchor="w")
            self._labels.append(lab)

            if i < len(self.STEPS) - 1:
                conn = ctk.CTkFrame(row, fg_color=BORDER, height=2, width=56, corner_radius=2)
                conn.pack(side="left", padx=18)
                self._connectors.append(conn)

        # registra o callback e faz a primeira renderização
        self.ctx.refresh_stepper = self.refresh
        self.refresh()

    def refresh(self):
        """Recalcula a conclusão a partir do estado e re-estiliza badges/rótulos/conectores."""
        done = [
            self.ctx.bitalino is not None,
            bool(self.ctx.infos_saved),
            bool(self.ctx.music_condition_mapping) and bool(self.ctx.save_dir),
            False,  # "Iniciar" é a ação; nunca marcada como concluída aqui
        ]
        current = next((i for i, d in enumerate(done) if not d), len(done) - 1)

        for i in range(len(self.STEPS)):
            is_done = done[i]
            is_current = (i == current)
            badge, top, lab = self._badges[i], self._tops[i], self._labels[i]

            if is_done:
                badge.configure(text="✓", fg_color=ACCENT, text_color=ACCENT_INK)
                top.configure(text=f"ETAPA {i + 1}", text_color=FAINT)
                lab.configure(text_color=TEXT)
            elif is_current:
                badge.configure(text=str(i + 1), fg_color=ACCENT_TINT, text_color=ACCENT)
                top.configure(text="AGORA", text_color=ACCENT)
                lab.configure(text_color=ACCENT)
            else:
                badge.configure(text=str(i + 1), fg_color=ACCENT_TINT, text_color=ACCENT)
                top.configure(text=f"ETAPA {i + 1}", text_color=FAINT)
                lab.configure(text_color=TEXT)

        for i, conn in enumerate(self._connectors):
            conn.configure(fg_color=ACCENT if done[i] else BORDER)
