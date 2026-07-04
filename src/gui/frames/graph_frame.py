"""Cartão do gráfico do sinal do BITalino em tempo real.

`GraphFrame` é a fachada que o app usa: envolve o widget `GraficoSinal`
(`signal_plot.py`) num cartão padrão com cabeçalho (canal + leitura ao vivo do
valor atual) e o expõe ao restante do sistema via `ctx.signal_plot`.

O `ExperimentRunner` controla o ciclo de vida do gráfico por estes métodos:
`begin(duration, lead)` ao iniciar a música, `push(t, v)` a cada amostra (da
thread de aquisição — thread-safe), `end()` ao terminar a faixa e `reset_idle()`
para voltar ao estado ocioso. `begin`/`end`/`reset_idle` tocam o canvas e são
sempre agendados pelo runner na thread da GUI; `push` é seguro a partir de
qualquer thread. Esses quatro nomes (em inglês) são o contrato público usado
por `src/core/experiment.py` — não renomear sem atualizar o runner também.
"""

import tkinter as tk

import customtkinter as ctk

from .. import theme
from ..theme import (ACCENT, FAINT, TRANSPARENTE, DISPLAY_FAMILY, MONO_FAMILY,
                     FONT_MD, PAD_MD, PAD_SM)
from ..widgets import Card, caption, mono
from .signal_plot import GraficoSinal

# altura fixa do gráfico (largura é responsiva via fill="x")
_ALTURA_GRAFICO = 300
# intervalo (ms) de atualização da leitura ao vivo do valor atual
_INTERVALO_LEITURA_MS = 500


class GraphFrame(Card):
    """Cartão com o gráfico do sinal em tempo real (fachada de `GraficoSinal`)."""

    def __init__(self, master, ctx=None):
        super().__init__(master)
        self.ctx = ctx

        # cabeçalho: rótulo do canal (esquerda) + valor atual ao vivo (direita)
        cabecalho = ctk.CTkFrame(self, fg_color=TRANSPARENTE)
        cabecalho.pack(fill="x", padx=PAD_MD, pady=(PAD_SM, 0))

        self._legenda_canal = caption(cabecalho, self._texto_cabecalho())
        self._legenda_canal.pack(side="left")

        self._rotulo_valor = mono(cabecalho, "—", size=FONT_MD, color=ACCENT)
        self._rotulo_valor.pack(side="right")

        # o gráfico propriamente dito (Canvas puro, recebe a paleta ativa por parâmetro)
        self._grafico = GraficoSinal(self, paleta=theme.THEME,
                                     familia_display=DISPLAY_FAMILY, familia_mono=MONO_FAMILY,
                                     height=_ALTURA_GRAFICO)
        self._grafico.pack(fill="x", expand=True, padx=PAD_MD, pady=(PAD_SM, PAD_MD))

        # nasce ocioso ("Aguardando gravação…")
        self._grafico.voltar_ao_ocioso()

        # registra a fachada no hub de estado, para o runner alimentar/controlar
        if ctx is not None:
            ctx.signal_plot = self

        self._id_after_leitura = None
        self._atualizar_leitura_valor()

    # -- rótulo do canal --------------------------------------------------
    def _rotulo_canal(self) -> str:
        n = getattr(self.ctx, "signal_channel", 0) if self.ctx is not None else 0
        return f"A{n}"

    def _texto_cabecalho(self) -> str:
        return f"SINAL DO BITALINO · CANAL {self._rotulo_canal()}"

    # -- leitura ao vivo do valor atual ----------------------------------
    def _atualizar_leitura_valor(self) -> None:
        try:
            valor = self._grafico.valor_atual
            texto = f"{valor:+.2f} {self._grafico.unidade}" if valor is not None else "—"
            self._rotulo_valor.configure(text=texto)
            self._id_after_leitura = self.after(_INTERVALO_LEITURA_MS, self._atualizar_leitura_valor)
        except tk.TclError:
            return

    # -- fachada thread-safe (delegada ao GraficoSinal) -------------------
    def push(self, t, value) -> None:
        """Adiciona uma amostra (thread-safe; chamado da thread de aquisição)."""
        self._grafico.adicionar_amostra(t, value)

    def begin(self, duration_s, lead_s=0) -> None:
        """Inicia uma gravação; atualiza o rótulo do canal e fixa o eixo X.

        `lead_s` = segundos iniciais de antecedência da contagem (eixo mostra t - lead)."""
        self._legenda_canal.configure(text=self._texto_cabecalho())
        self._grafico.iniciar(duration_s, lead_s)

    def end(self) -> None:
        """Encerra a faixa; o registro completo permanece visível."""
        self._grafico.finalizar()

    def reset_idle(self) -> None:
        """Volta o gráfico ao estado ocioso."""
        self._grafico.voltar_ao_ocioso()

    def destroy(self):
        if self._id_after_leitura:
            try:
                self.after_cancel(self._id_after_leitura)
            except Exception:
                pass
        if self.ctx is not None and getattr(self.ctx, "signal_plot", None) is self:
            self.ctx.signal_plot = None
        super().destroy()
