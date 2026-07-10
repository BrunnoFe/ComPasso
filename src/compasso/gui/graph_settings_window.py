"""Janela modal "Configurações do Gráfico" (menu Configurações → Gráfico).

Ajusta os parâmetros de exibição do gráfico do sinal em tempo real (ver
`src/gui/frames/signal_plot.py`) com **preview ao vivo** e **persistência** no mesmo
`prefs.json` do tema (chave `graph`, ver `src/core/config_manager.py`). Segue o tema
escuro da janela principal (cores/fontes de `theme.py`), no mesmo molde do
`ExperimentConfigWindow`.

As configurações são o dict de chaves `graph_settings` (y_scale, smoothing_enabled,
smoothing_window, fps, line_width, grid_visible, axis_labels_visible). A **escala Y**
fica desabilitada enquanto uma sessão está em andamento (é fixa durante o experimento).
"""

import pywinstyles
import customtkinter as ctk

from compasso.gui.assets import ASSETS_DIR
from compasso.utils.configs import ICON_FILENAME

from . import gui_logger
from .theme import (WIN_BG, BAR_BG, BORDER, INPUT_BG, TRANSPARENTE, ACCENT,
                   ACCENT_TINT, TEXT, MUTED, FAINT, BASE_FONT, CORNER, CORNER_SM,
                   DISPLAY_FAMILY, MONO_FAMILY, FONT_MD, FONT_SM)
from .widgets import styled_label, styled_button, ghost_button, mono
from compasso.core import config_manager
from compasso.core.constants import SENSOR_DEFAULT, SENSOR_GRAPH_PARAMS

# opções de FPS oferecidas no menu (quadros por segundo do gráfico)
_OPCOES_FPS = ["10", "15", "30", "60"]

# rótulo de valor do gráfico: mapeia o texto exibido no menu <-> chave persistida (value_mode)
_OPCOES_VALUE_MODE = ["Valor bruto", "Média"]
_MAPA_VALUE_MODE = {"Valor bruto": "raw", "Média": "mean"}
_MAPA_VALUE_MODE_INV = {"raw": "Valor bruto", "mean": "Média"}

# limites/passos dos sliders. A escala Y depende do sensor ativo (unidade/mín/máx/passo,
# ver constants.SENSOR_GRAPH_PARAMS) — calculada em runtime no __init__.
_JANELA_MIN, _JANELA_MAX, _JANELA_PASSOS = 1, 15, 14   # média móvel: 1..15 colunas
_LARGURA_MIN, _LARGURA_MAX, _LARGURA_PASSOS = 0.5, 4.0, 7  # espessura: 0.5..4.0 (passo 0.5)


class GraphSettingsWindow(ctk.CTkToplevel):
    """Janela modal de configurações do gráfico do sinal.

    :param master: janela/root pai.
    :param ctx: `AppContext` (para ler/gravar `graph_settings`, aplicar preview via
        `ctx.signal_plot` e checar se há uma sessão em andamento em `ctx.runner`).
    """

    def __init__(self, master, ctx):
        super().__init__(master, fg_color=WIN_BG)
        self.ctx = ctx

        self.title("Configurações do Gráfico")
        self.resizable(False, False)
        self.transient(master)
        self.after(10, self._safe_grab)
        self.protocol("WM_DELETE_WINDOW", self._on_cancelar)  # fechar no "X" = Cancelar

        try:
            pywinstyles.change_border_color(self, WIN_BG)
            pywinstyles.change_header_color(self, WIN_BG)
            self.iconbitmap(str(ASSETS_DIR / ICON_FILENAME))
        except Exception as e:
            gui_logger.logger.warning(f"Não foi possível ajustar a janela : {e}")

        # parâmetros do eixo Y do sensor ativo (unidade/mín/máx/passo/padrão). A escala Y é
        # interpretada na unidade do sensor; o slider usa esses limites e passo.
        self._sensor_params = SENSOR_GRAPH_PARAMS.get(
            getattr(ctx, "sensor_type", SENSOR_DEFAULT), SENSOR_GRAPH_PARAMS[SENSOR_DEFAULT])

        # snapshot dos valores ativos ao abrir (para o Cancelar reverter o preview)
        self._snapshot = self._settings_atuais()

        # --- variáveis dos controles (inicializadas com o snapshot) ---
        # escala Y pode ser fracionária (mV: 0,2/0,1) -> DoubleVar; clampada à faixa do sensor.
        self._y_var = ctk.DoubleVar(value=self._escala_no_intervalo(self._snapshot["y_scale"]))
        self._smooth_enabled_var = ctk.BooleanVar(value=bool(self._snapshot["smoothing_enabled"]))
        self._smooth_window_var = ctk.IntVar(value=int(self._snapshot["smoothing_window"]))
        self._fps_var = ctk.StringVar(value=str(int(self._snapshot["fps"])))
        self._width_var = ctk.DoubleVar(value=float(self._snapshot["line_width"]))
        self._grid_var = ctk.BooleanVar(value=bool(self._snapshot["grid_visible"]))
        self._labels_var = ctk.BooleanVar(value=bool(self._snapshot["axis_labels_visible"]))
        self._value_mode_var = ctk.StringVar(
            value=_MAPA_VALUE_MODE_INV.get(self._snapshot["value_mode"], _OPCOES_VALUE_MODE[0]))

        self._sessao_ativa = bool(getattr(ctx, "runner", None) is not None
                                  and ctx.runner.is_running())

        self._montar_layout()
        self._atualizar_rotulos()

    # ------------------------------------------------------------------ #
    def _safe_grab(self):
        try:
            self.grab_set()
        except Exception:
            pass

    def _settings_atuais(self) -> dict:
        """Valores ativos ao abrir a janela (ctx.graph_settings sobre os defaults)."""
        atual = dict(config_manager.DEFAULT_GRAPH_SETTINGS)
        salvo = getattr(self.ctx, "graph_settings", None)
        if isinstance(salvo, dict):
            atual.update({k: salvo[k] for k in config_manager.DEFAULT_GRAPH_SETTINGS if k in salvo})
        return atual

    # -- construção da UI ----------------------------------------------- #
    def _montar_layout(self):
        mainframe = ctk.CTkFrame(self, corner_radius=CORNER, border_width=1,
                                 bg_color=WIN_BG, fg_color=BAR_BG, border_color=BORDER)
        mainframe.grid(row=0, column=0, padx=20, pady=20, sticky=ctk.NSEW)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        mainframe.grid_columnconfigure(1, weight=1)

        styled_label(mainframe, text="Configurações do Gráfico", font=BASE_FONT).grid(
            row=0, column=0, columnspan=2, padx=15, pady=(15, 20), sticky=ctk.N)

        # 1) Escala do eixo Y (slider simétrico) ---------------------------------
        styled_label(mainframe, text="Escala do eixo Y:").grid(
            row=1, column=0, padx=15, pady=10, sticky=ctk.E)
        y_frame = ctk.CTkFrame(mainframe, fg_color=TRANSPARENTE)
        y_frame.grid(row=1, column=1, padx=15, pady=10, sticky=ctk.EW)
        self._y_neg_label = mono(y_frame, "", size=FONT_SM, color=MUTED, width=72)
        self._y_neg_label.pack(side="left")
        p = self._sensor_params
        passos_y = max(1, int(round((p["maximo"] - p["minimo"]) / p["passo"])))
        self._y_slider = self._slider(y_frame, self._y_var, p["minimo"], p["maximo"], passos_y)
        self._y_slider.pack(side="left", padx=8, fill="x", expand=True)
        self._y_pos_label = mono(y_frame, "", size=FONT_SM, color=MUTED, width=72)
        self._y_pos_label.pack(side="left")

        # nota quando a escala Y está travada (sessão em andamento)
        self._y_nota = styled_label(mainframe, text="", text_color=FAINT,
                                    font=ctk.CTkFont(DISPLAY_FAMILY, FONT_SM))
        self._y_nota.grid(row=2, column=1, padx=15, pady=(0, 6), sticky=ctk.W)

        # 2) Média móvel (toggle + janela) ---------------------------------------
        styled_label(mainframe, text="Média móvel (suavização):").grid(
            row=3, column=0, padx=15, pady=10, sticky=ctk.E)
        smooth_frame = ctk.CTkFrame(mainframe, fg_color=TRANSPARENTE)
        smooth_frame.grid(row=3, column=1, padx=15, pady=10, sticky=ctk.EW)
        self._smooth_switch = self._switch(smooth_frame, self._smooth_enabled_var)
        self._smooth_switch.pack(side="left")
        self._smooth_window_slider = self._slider(
            smooth_frame, self._smooth_window_var, _JANELA_MIN, _JANELA_MAX, _JANELA_PASSOS)
        self._smooth_window_slider.pack(side="left", padx=(12, 8), fill="x", expand=True)
        self._smooth_window_value = mono(smooth_frame, "5", size=FONT_SM, color=MUTED, width=54)
        self._smooth_window_value.pack(side="left")
        styled_label(mainframe, text="janela em colunas de exibição (não altera o dado gravado)",
                     text_color=FAINT, font=ctk.CTkFont(DISPLAY_FAMILY, FONT_SM)).grid(
            row=4, column=1, padx=15, pady=(0, 6), sticky=ctk.W)

        # 3) FPS ------------------------------------------------------------------
        styled_label(mainframe, text="Atualização (FPS):").grid(
            row=5, column=0, padx=15, pady=10, sticky=ctk.E)
        self._fps_menu = ctk.CTkOptionMenu(
            mainframe, variable=self._fps_var, values=_OPCOES_FPS, width=120,
            command=self._on_change, fg_color=INPUT_BG, button_color=INPUT_BG,
            button_hover_color=BORDER, dropdown_fg_color=BAR_BG,
            dropdown_hover_color=ACCENT_TINT, text_color=TEXT, dropdown_text_color=TEXT,
            font=ctk.CTkFont(MONO_FAMILY, FONT_MD), dropdown_font=ctk.CTkFont(MONO_FAMILY, FONT_MD),
            corner_radius=CORNER_SM)
        self._fps_menu.grid(row=5, column=1, padx=15, pady=10, sticky=ctk.W)

        # 4) Espessura da linha ---------------------------------------------------
        styled_label(mainframe, text="Espessura da linha:").grid(
            row=6, column=0, padx=15, pady=10, sticky=ctk.E)
        width_frame = ctk.CTkFrame(mainframe, fg_color=TRANSPARENTE)
        width_frame.grid(row=6, column=1, padx=15, pady=10, sticky=ctk.EW)
        self._width_slider = self._slider(
            width_frame, self._width_var, _LARGURA_MIN, _LARGURA_MAX, _LARGURA_PASSOS)
        self._width_slider.pack(side="left", padx=(0, 8), fill="x", expand=True)
        self._width_value = mono(width_frame, "1.5 px", size=FONT_SM, color=MUTED, width=54)
        self._width_value.pack(side="left")

        # 5) Grade liga/desliga ---------------------------------------------------
        styled_label(mainframe, text="Linhas de grade:").grid(
            row=7, column=0, padx=15, pady=10, sticky=ctk.E)
        self._switch(mainframe, self._grid_var).grid(row=7, column=1, padx=15, pady=10, sticky=ctk.W)

        # 6) Rótulos dos eixos ----------------------------------------------------
        styled_label(mainframe, text="Rótulos dos eixos:").grid(
            row=8, column=0, padx=15, pady=10, sticky=ctk.E)
        self._switch(mainframe, self._labels_var).grid(row=8, column=1, padx=15, pady=10, sticky=ctk.W)

        # 7) Rótulo de valor (valor bruto + mín/máx  vs  média + desvio-padrão) ----
        styled_label(mainframe, text="Rótulo de valor:").grid(
            row=9, column=0, padx=15, pady=10, sticky=ctk.E)
        self._value_mode_menu = ctk.CTkOptionMenu(
            mainframe, variable=self._value_mode_var, values=_OPCOES_VALUE_MODE, width=160,
            command=self._on_change, fg_color=INPUT_BG, button_color=INPUT_BG,
            button_hover_color=BORDER, dropdown_fg_color=BAR_BG,
            dropdown_hover_color=ACCENT_TINT, text_color=TEXT, dropdown_text_color=TEXT,
            font=ctk.CTkFont(MONO_FAMILY, FONT_MD), dropdown_font=ctk.CTkFont(MONO_FAMILY, FONT_MD),
            corner_radius=CORNER_SM)
        self._value_mode_menu.grid(row=9, column=1, padx=15, pady=10, sticky=ctk.W)

        # botões ------------------------------------------------------------------
        button_row = ctk.CTkFrame(mainframe, fg_color=TRANSPARENTE)
        button_row.grid(row=10, column=0, columnspan=2, padx=15, pady=(20, 15), sticky=ctk.E)
        styled_button(button_row, text="Salvar", width=110, command=self._on_salvar).grid(
            row=0, column=0, padx=(0, 10))
        ghost_button(button_row, text="Restaurar padrões", width=150,
                     command=self._on_restaurar).grid(row=0, column=1, padx=(0, 10))
        ghost_button(button_row, text="Cancelar", width=110, command=self._on_cancelar).grid(
            row=0, column=2)

        # trava a escala Y durante uma sessão em andamento
        if self._sessao_ativa:
            self._y_slider.configure(state="disabled")
            self._y_nota.configure(text="A escala Y não pode ser alterada durante um experimento em andamento.")

    def _slider(self, master, variable, minimo, maximo, passos):
        """CTkSlider no estilo do slider de volume (progresso/knob no acento)."""
        return ctk.CTkSlider(master, from_=minimo, to=maximo, number_of_steps=passos,
                             variable=variable, command=self._on_change, height=16,
                             progress_color=ACCENT, button_color=ACCENT,
                             button_hover_color=ACCENT, fg_color=BORDER)

    def _switch(self, master, variable):
        """CTkSwitch no estilo do tema (trilho no acento quando ligado)."""
        return ctk.CTkSwitch(master, text="", variable=variable, command=self._on_change,
                            onvalue=True, offvalue=False, progress_color=ACCENT,
                            button_color=TEXT, button_hover_color=TEXT, fg_color=BORDER,
                            width=44)

    # -- reações e preview ---------------------------------------------- #
    def _on_change(self, *_):
        """Chamado por qualquer controle: atualiza os rótulos e aplica o preview ao vivo."""
        self._atualizar_rotulos()
        self._aplicar_preview(self._coletar())

    def _escala_no_intervalo(self, escala):
        """Clampa `escala` à faixa do sensor; fora dela, cai no padrão do sensor."""
        p = self._sensor_params
        try:
            valor = abs(float(escala))
        except (TypeError, ValueError):
            return p["padrao"]
        return valor if p["minimo"] <= valor <= p["maximo"] else p["padrao"]

    def _arredondar_escala(self, escala):
        """Arredonda `escala` ao múltiplo de passo do sensor mais próximo, dentro dos limites."""
        p = self._sensor_params
        passos = round((float(escala) - p["minimo"]) / p["passo"])
        valor = p["minimo"] + passos * p["passo"]
        valor = min(max(valor, p["minimo"]), p["maximo"])
        return round(valor, 3)

    @staticmethod
    def _fmt_escala(valor):
        """Formata a escala Y sem zeros à toa (ex.: ``0.4``, ``1``, ``30``)."""
        return f"{round(float(valor), 3):g}"

    def _atualizar_rotulos(self):
        """Reflete os valores atuais dos sliders nos rótulos e habilita/desabilita a janela."""
        y = self._fmt_escala(self._y_var.get())
        unidade = self._sensor_params["unidade"]
        self._y_neg_label.configure(text=f"−{y} {unidade}")
        self._y_pos_label.configure(text=f"+{y} {unidade}")
        self._smooth_window_value.configure(text=str(int(round(self._smooth_window_var.get()))))
        largura = self._arredondar_meio(self._width_var.get())
        self._width_value.configure(text=f"{largura:g} px")
        estado = "normal" if self._smooth_enabled_var.get() else "disabled"
        self._smooth_window_slider.configure(state=estado)

    @staticmethod
    def _arredondar_meio(valor):
        """Arredonda para o múltiplo de 0,5 mais próximo (passo do slider de espessura)."""
        return round(float(valor) * 2) / 2

    def _coletar(self) -> dict:
        """Monta o dict de configurações a partir do estado atual dos controles."""
        return {
            "y_scale": self._arredondar_escala(self._y_var.get()),
            "smoothing_enabled": bool(self._smooth_enabled_var.get()),
            "smoothing_window": int(round(self._smooth_window_var.get())),
            "fps": int(self._fps_var.get()),
            "line_width": self._arredondar_meio(self._width_var.get()),
            "grid_visible": bool(self._grid_var.get()),
            "axis_labels_visible": bool(self._labels_var.get()),
            "value_mode": _MAPA_VALUE_MODE.get(self._value_mode_var.get(), "raw"),
        }

    def _aplicar_preview(self, settings: dict):
        """Aplica `settings` ao gráfico ao vivo, se houver um gráfico registrado."""
        plot = getattr(self.ctx, "signal_plot", None)
        if plot is not None:
            try:
                plot.apply_settings(settings)
            except Exception as e:
                gui_logger.logger.warning(f"Falha ao aplicar preview do gráfico: {e}")

    # -- ações dos botões ----------------------------------------------- #
    def _on_salvar(self):
        settings = self._coletar()
        config_manager.set_graph_prefs(settings)
        self.ctx.graph_settings = settings
        self._aplicar_preview(settings)
        gui_logger.logger.info(f"Configurações do gráfico salvas: {settings}")
        self._fechar()

    def _on_restaurar(self):
        """Volta os controles aos defaults de fábrica e aplica o preview."""
        padrao = config_manager.DEFAULT_GRAPH_SETTINGS
        # a escala Y padrão vem do sensor ativo (não do default global de µV).
        self._y_var.set(self._sensor_params["padrao"])
        self._smooth_enabled_var.set(bool(padrao["smoothing_enabled"]))
        self._smooth_window_var.set(int(padrao["smoothing_window"]))
        self._fps_var.set(str(int(padrao["fps"])))
        self._width_var.set(float(padrao["line_width"]))
        self._grid_var.set(bool(padrao["grid_visible"]))
        self._labels_var.set(bool(padrao["axis_labels_visible"]))
        self._value_mode_var.set(_MAPA_VALUE_MODE_INV.get(padrao["value_mode"], _OPCOES_VALUE_MODE[0]))
        self._on_change()

    def _on_cancelar(self):
        """Reverte o preview ao estado de abertura e fecha sem salvar."""
        self._aplicar_preview(self._snapshot)
        self._fechar()

    def _fechar(self):
        self.withdraw()
        self.destroy()
