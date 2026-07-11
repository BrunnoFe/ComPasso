import customtkinter as ctk

from ..theme import (BORDER, TEXT, FAINT, ACCENT, ACCENT_INK, ACCENT_TINT,
                     DANGER, DANGER_TINT, TRANSPARENTE, DISPLAY_FAMILY,
                     FONT_S10, FONT_S13, FONT_S14)
from ..widgets import Card


class StepperFrame(Card):
    """Indicador de progresso das etapas do experimento (funcional, dirigido pelo estado).

    Etapas fixas: Configurações → Conectar → Participante → Arquivos → [Calibragem] →
    Começar. A etapa "Calibragem" só aparece quando a calibração de volume está
    habilitada (`ctx.calibracao_habilitada`); nesse caso "Começar" vira a 6ª etapa,
    senão a 5ª. As etapas acendem conforme o estado real do `AppContext`:

    - concluída → verde (accent) com "✓";
    - atual (primeira ainda não feita) → destacada em accent com "AGORA";
    - pendente (ainda não feita e não é a atual) → vermelha (danger).

    Registra `ctx.refresh_stepper = self.refresh`; qualquer frame que mude o estado
    chama `ctx.notify_stepper()` para re-renderizar (sempre na thread da GUI). Quando
    o conjunto de etapas muda (calibração habilitada/desabilitada), a linha é
    reconstruída; caso contrário só re-estiliza.
    """

    def __init__(self, master, ctx):
        super().__init__(master)
        self.ctx = ctx

        self._row = ctk.CTkFrame(self, fg_color=TRANSPARENTE)
        self._row.pack(fill="x", padx=22, pady=14)

        self._badges = []
        self._tops = []
        self._labels = []
        self._connectors = []
        self._rotulos_construidos = []  # rótulos atualmente renderizados (detecta rebuild)

        # registra o callback e faz a primeira renderização
        self.ctx.refresh_stepper = self.refresh
        self.refresh()

    def _etapas_atuais(self):
        """Monta a lista (rótulo, concluída) das etapas ativas conforme o estado.

        "Calibragem" só entra quando `ctx.calibracao_habilitada`. "Começar" é a ação
        final e nunca é marcada como concluída aqui.
        """
        etapas = [
            ("Configurações", bool(self.ctx.config_loaded)),
            ("Conectar", self.ctx.bitalino is not None),
            ("Participante", bool(self.ctx.infos_saved)),
            ("Arquivos", bool(self.ctx.music_condition_mapping) and bool(self.ctx.save_dir)),
        ]
        if self.ctx.calibracao_habilitada:
            etapas.append(("Calibragem", self.ctx.volume_calibrado is not None))
        etapas.append(("Começar", False))
        return etapas

    def _reconstruir(self, rotulos):
        """Recria badges/rótulos/conectores para a lista de rótulos informada."""
        for widget in self._row.winfo_children():
            widget.destroy()
        self._badges, self._tops, self._labels, self._connectors = [], [], [], []

        total = len(rotulos)
        for i, rotulo in enumerate(rotulos):
            item = ctk.CTkFrame(self._row, fg_color=TRANSPARENTE)
            item.pack(side="left")

            badge = ctk.CTkLabel(item, text=str(i + 1), width=28, height=28, corner_radius=14,
                                 fg_color=ACCENT_TINT, text_color=ACCENT,
                                 font=ctk.CTkFont(DISPLAY_FAMILY, FONT_S13, weight="bold"))
            badge.pack(side="left", padx=(0, 11))
            self._badges.append(badge)

            texts = ctk.CTkFrame(item, fg_color=TRANSPARENTE)
            texts.pack(side="left")
            top = ctk.CTkLabel(texts, text=f"ETAPA {i + 1}", text_color=FAINT,
                               font=ctk.CTkFont(DISPLAY_FAMILY, FONT_S10, weight="bold"))
            top.pack(anchor="w")
            self._tops.append(top)
            lab = ctk.CTkLabel(texts, text=rotulo, text_color=TEXT,
                               font=ctk.CTkFont(DISPLAY_FAMILY, FONT_S14, weight="bold"))
            lab.pack(anchor="w")
            self._labels.append(lab)

            if i < total - 1:
                conn = ctk.CTkFrame(self._row, fg_color=BORDER, height=2, width=56, corner_radius=2)
                conn.pack(side="left", padx=18)
                self._connectors.append(conn)

    def refresh(self):
        """Recalcula a conclusão a partir do estado e re-estiliza badges/rótulos/conectores."""
        etapas = self._etapas_atuais()
        rotulos = [rotulo for rotulo, _ in etapas]
        done = [concluida for _, concluida in etapas]

        # reconstrói a linha só quando o conjunto de etapas muda (evita flicker por refresh)
        if rotulos != self._rotulos_construidos:
            self._reconstruir(rotulos)
            self._rotulos_construidos = rotulos

        current = next((i for i, d in enumerate(done) if not d), len(done) - 1)

        for i in range(len(rotulos)):
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
                badge.configure(text=str(i + 1), fg_color=DANGER_TINT, text_color=DANGER)
                top.configure(text="PENDENTE", text_color=DANGER)
                lab.configure(text_color=DANGER)

        for i, conn in enumerate(self._connectors):
            conn.configure(fg_color=ACCENT if done[i] else BORDER)
