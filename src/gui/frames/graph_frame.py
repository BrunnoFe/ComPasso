"""Cartão do gráfico do sinal do BITalino em tempo real.

`GraphFrame` é a fachada que o app usa: envolve o widget `SignalPlot`
(`signal_plot.py`) num cartão padrão com cabeçalho (canal + leitura ao
vivo do valor atual) e o expõe ao restante do sistema via `ctx.signal_plot`.

O `ExperimentRunner` controla o ciclo de vida do gráfico por estes métodos:
`begin(duration)` ao iniciar a música, `push(t, v)` a cada amostra (da thread de
aquisição — thread-safe), `end()` ao terminar a faixa e `reset_idle()` para voltar
ao estado ocioso. `begin`/`end`/`reset_idle` tocam o canvas e são sempre agendados
pelo runner na thread da GUI; `push` é seguro a partir de qualquer thread.
"""

import tkinter as tk

import customtkinter as ctk

from .. import theme
from ..theme import (ACCENT, FAINT, TRANSPARENTE, DISPLAY_FAMILY, MONO_FAMILY,
                     FONT_MD, PAD_MD, PAD_SM)
from ..widgets import Card, caption, mono
from .signal_plot import SignalPlot

# altura fixa do gráfico (largura é responsiva via fill="x")
_PLOT_HEIGHT = 300
# intervalo (ms) de atualização da leitura ao vivo do valor atual
_VALUE_MS = 500

class GraphFrame(Card):
    """Cartão com o gráfico do sinal em tempo real (fachada de `SignalPlot`)."""

    def __init__(self, master, ctx=None):
        super().__init__(master)
        self.ctx = ctx

        # cabeçalho: rótulo do canal (esquerda) + valor atual ao vivo (direita)
        header = ctk.CTkFrame(self, fg_color=TRANSPARENTE)
        header.pack(fill="x", padx=PAD_MD, pady=(PAD_SM, 0))

        self._channel_caption = caption(header, self._channel_text())
        self._channel_caption.pack(side="left")

        self._value_label = mono(header, "—", size=FONT_MD, color=ACCENT)
        self._value_label.pack(side="right")

        # o gráfico propriamente dito (Canvas puro, recebe a paleta ativa por parâmetro)
        self._plot = SignalPlot(self, palette=theme.THEME,
                                channel_label=self._channel_label(),
                                display_family=DISPLAY_FAMILY, mono_family=MONO_FAMILY,
                                height=_PLOT_HEIGHT)
        self._plot.pack(fill="x", expand=True, padx=PAD_MD, pady=(PAD_SM, PAD_MD))

        # nasce ocioso ("Aguardando gravação…")
        self._plot.reset_idle()

        # registra a fachada no hub de estado, para o runner alimentar/controlar
        if ctx is not None:
            ctx.signal_plot = self

        self._value_after_id = None
        self._tick_value()

    # -- rótulo do canal --------------------------------------------------
    def _channel_label(self) -> str:
        n = getattr(self.ctx, "signal_channel", 0) if self.ctx is not None else 0
        return f"A{n}"

    def _channel_text(self) -> str:
        return f"SINAL DO BITALINO · CANAL {self._channel_label()}"

    # -- leitura ao vivo do valor atual ----------------------------------
    def _tick_value(self) -> None:
        try:
            v = self._plot.current_value
            self._value_label.configure(text=(f"{v:+.2f} {self._plot.unit}"
                                              if v is not None else "—"))
            self._value_after_id = self.after(_VALUE_MS, self._tick_value)
        except tk.TclError:
            return

    # -- fachada thread-safe (delegada ao SignalPlot) --------------------
    def push(self, t, value) -> None:
        """Adiciona uma amostra (thread-safe; chamado da thread de aquisição)."""
        self._plot.push(t, value)

    def begin(self, duration_s, lead_s=0) -> None:
        """Inicia uma gravação; atualiza o rótulo do canal e fixa o eixo X.

        `lead_s` = segundos iniciais de lead da contagem (eixo mostra t - lead)."""
        self._channel_caption.configure(text=self._channel_text())
        self._plot.channel_label = self._channel_label()
        self._plot.begin(duration_s, lead_s)

    def end(self) -> None:
        """Encerra a faixa; o registro completo permanece visível."""
        self._plot.end()

    def reset_idle(self) -> None:
        """Volta o gráfico ao estado ocioso."""
        self._plot.reset_idle()

    def destroy(self):
        if self._value_after_id:
            try:
                self.after_cancel(self._value_after_id)
            except Exception:
                pass
        if self.ctx is not None and getattr(self.ctx, "signal_plot", None) is self:
            self.ctx.signal_plot = None
        super().destroy()
