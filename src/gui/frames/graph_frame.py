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
from ..theme import (ACCENT, TRANSPARENTE, DISPLAY_FAMILY, MONO_FAMILY,
                     FONT_MD, PAD_MD, PAD_SM)
from ..widgets import Card, caption, mono
from .signal_plot import GraficoSinal

# altura fixa do gráfico (largura é responsiva via fill="x")
_ALTURA_GRAFICO = 300
# intervalo (ms) de atualização da leitura ao vivo do valor atual
_INTERVALO_LEITURA_MS = 500

# mapa das chaves de ctx.graph_settings -> kwargs do construtor de GraficoSinal
_MAPA_SETTINGS_GRAFICO = {
    "y_scale": "escala_y",
    "smoothing_enabled": "suavizacao_ativa",
    "smoothing_window": "janela_suavizacao",
    "fps": "fps",
    "line_width": "largura_linha",
    "grid_visible": "grade_visivel",
    "axis_labels_visible": "rotulos_visiveis",
}


def _kwargs_grafico(settings) -> dict:
    """Traduz um dict ``graph_settings`` nos kwargs do construtor de ``GraficoSinal``.

    Chaves ausentes/inválidas são omitidas, deixando o widget usar seus próprios
    defaults (que já são os valores hardcoded originais)."""
    if not isinstance(settings, dict):
        return {}
    return {kwarg: settings[chave] for chave, kwarg in _MAPA_SETTINGS_GRAFICO.items()
            if chave in settings}


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

        # largura fixa + alinhado à direita: o texto varia de comprimento (modo média/bruto,
        # com mín/máx ou DP) e não deve redimensionar o cabeçalho a cada atualização.
        self._rotulo_valor = mono(cabecalho, "—", size=FONT_MD, color=ACCENT)
        self._rotulo_valor.configure(width=300, anchor="e")
        self._rotulo_valor.pack(side="right")

        # modo do rótulo de valor: "raw" (valor bruto + mín/máx) ou "mean" (média + DP).
        settings_iniciais = getattr(ctx, "graph_settings", None) if ctx is not None else None
        self._value_mode = "raw"
        if isinstance(settings_iniciais, dict):
            self._value_mode = settings_iniciais.get("value_mode", "raw")

        # o gráfico propriamente dito (Canvas puro, recebe a paleta ativa por parâmetro).
        # As configurações de exibição vêm do hub (ctx.graph_settings, populado no arranque
        # e ajustável pela janela "Configurações do Gráfico"); ausentes -> defaults do widget.
        settings = getattr(ctx, "graph_settings", None) if ctx is not None else None
        self._grafico = GraficoSinal(self, paleta=theme.THEME,
                                     familia_display=DISPLAY_FAMILY, familia_mono=MONO_FAMILY,
                                     height=_ALTURA_GRAFICO,
                                     **_kwargs_grafico(settings))
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
    def _texto_leitura(self) -> str:
        """Monta o texto do rótulo de valor conforme o modo configurado.

        - "mean": ``Média: ##.## µV (##.## µV)`` — média + desvio-padrão da janela da música.
        - "raw" : ``Valor: ##.## µV (##.## - ##.##)`` — último valor + (mín – máx) da janela.
        Retorna ``"—"`` enquanto não há dado aplicável.
        """
        unidade = self._grafico.unidade
        if self._value_mode == "mean":
            media = self._grafico.valor_medio
            if media is None:
                return "—"
            texto = f"Média: {media:.2f} {unidade}"
            desvio = self._grafico.desvio_padrao
            if desvio is not None:
                texto += f" ({desvio:.2f} {unidade})"
            return texto

        # modo "raw" (padrão)
        atual = self._grafico.valor_atual
        if atual is None:
            return "—"
        texto = f"Valor: {atual:.2f} {unidade}"
        minimo, maximo = self._grafico.valor_minimo, self._grafico.valor_maximo
        if minimo is not None and maximo is not None:
            texto += f" ({minimo:.2f} - {maximo:.2f})"
        return texto

    def _atualizar_leitura_valor(self) -> None:
        try:
            self._rotulo_valor.configure(text=self._texto_leitura())
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

    def apply_settings(self, settings: dict) -> None:
        """Aplica configurações de exibição ao vivo (janela "Configurações do Gráfico").

        `settings` usa as chaves de `ctx.graph_settings` (ver `_MAPA_SETTINGS_GRAFICO`)
        — a escala Y só muda com o gráfico fora de gravação (ver `GraficoSinal`)."""
        # o modo do rótulo é tratado aqui (o widget não o usa); reflete no próximo tick.
        if isinstance(settings, dict) and "value_mode" in settings:
            self._value_mode = settings["value_mode"]
        self._grafico.aplicar_configuracoes(settings)

    def destroy(self):
        if self._id_after_leitura:
            try:
                self.after_cancel(self._id_after_leitura)
            except Exception:
                pass
        if self.ctx is not None and getattr(self.ctx, "signal_plot", None) is self:
            self.ctx.signal_plot = None
        super().destroy()
