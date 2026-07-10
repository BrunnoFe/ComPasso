"""Janela modal de calibração de volume de som (menu/atalho "Calibrar" do PlayerBar).

Toca uma faixa de áudio dedicada (definida no `.config`) enquanto o volume principal do sistema
sobe gradualmente entre um mínimo e um máximo (X% a cada X s), para calibrar o volume com o
participante antes da sessão. Segue o tema escuro da janela principal (cores/fontes de `theme.py`),
no mesmo molde de `ExperimentConfigWindow`/`GraphSettingsWindow`. A lógica pura da rampa
(validação, duração estimada, volume por degrau) vive em `compasso.core.calibration`; aqui ficam a
UI, a orquestração por temporizador (`after`) e a máquina de estados dos botões.

Fluxo: o participante primeiro ouve a **linha de base** (rampa completa, demonstrativa); só então a
**calibração** é liberada — nela, o participante avisa quando o volume fica confortável e o teste
para, mantendo o volume atual. Ao salvar, o volume ótimo é aplicado ao sistema e ao slider do
PlayerBar (travado) via `ctx.aplicar_volume_calibrado`.
"""

import os

import pywinstyles
import customtkinter as ctk

from compasso.gui.assets import ASSETS_DIR
from compasso.utils.configs import ICON_FILENAME
from compasso.utils import format_time

from . import gui_logger
from .theme import (FONT_LG, WIN_BG, BAR_BG, BORDER, INPUT_BG, TRANSPARENTE, ACCENT, ACCENT_INK,
                   TEXT, MUTED, FAINT, DANGER, DANGER_TINT, DANGER_BORDER, CORNER, CORNER_PILL,
                   DISPLAY_FAMILY, BASE_FONT, INPUT_H, BTN_H, FONT_SM, FONT_BASE, FONT_4XL)
from .widgets import show_message, ask_options, styled_label, styled_entry, styled_button, \
    ghost_button, caption, mono
from compasso.core import get_system_volume, set_system_volume, calibration

# Intervalo (ms) do laço que atualiza a barra de progresso do mini-player.
_INTERVALO_PROGRESSO_MS = 200


class CalibrationWindow(ctk.CTkToplevel):
    """Janela modal de calibração de volume.

    :param master: janela/root pai.
    :param ctx: `AppContext` — usa `ctx.player` (reprodução), `ctx.calibracao_caminho` (faixa) e
        o callback `ctx.aplicar_volume_calibrado(volume)` para fixar o volume ótimo no PlayerBar.
    """

    def __init__(self, master, ctx):
        super().__init__(master, fg_color=WIN_BG)
        self.ctx = ctx

        self.title("Calibração de Volume")
        self.resizable(False, False)
        self.transient(master)
        self.after(10, self._safe_grab)
        self.protocol("WM_DELETE_WINDOW", self._on_fechar)  # fechar no "X" restaura o volume

        try:
            pywinstyles.change_border_color(self, WIN_BG)
            pywinstyles.change_header_color(self, WIN_BG)
            self.iconbitmap(str(ASSETS_DIR / ICON_FILENAME))
        except Exception as e:
            gui_logger.logger.warning(f"Não foi possível ajustar a janela : {e}")

        # reutiliza o Player do app (pygame.mixer é global; o botão "Calibrar" fica desabilitado
        # durante o experimento, então não há disputa pela reprodução).
        self._player = ctx.player
        self._volume_original = int(round(get_system_volume()))
        self._vol_atual = self._volume_original

        # estado da máquina de calibração
        self._estado = "idle"          # idle | base | calibrar | salvar
        self._modo = None              # rampa em curso: "base" | "calibrar" | None
        self._base_ok = False          # linha de base concluída? (libera a calibração)
        self._params_validos = True
        self._volume_otimo = None
        self._salvo = False            # o usuário confirmou um volume ótimo?
        self._indice = 0               # degrau atual da rampa
        self._passo_id = None          # id do after() da rampa (cancelável)
        self._progresso_id = None      # id do after() do polling de progresso
        # parâmetros da rampa em execução (fixados no início de cada teste)
        self._vmin = self._vmax = self._step_pct = self._step_seg = 0

        # variáveis dos controles (defaults da sessão — não persistidos, ver CLAUDE.md)
        self._vol_min_var = ctk.StringVar(value=str(calibration.CALIB_VOL_MIN_DEFAULT))
        self._vol_max_var = ctk.StringVar(value=str(calibration.CALIB_VOL_MAX_DEFAULT))
        self._step_pct_var = ctk.IntVar(value=calibration.CALIB_STEP_PCT_DEFAULT)
        self._step_seg_var = ctk.IntVar(value=calibration.CALIB_STEP_SEG_DEFAULT)
        self._t_begin_var = ctk.StringVar(value="00:00")
        self._t_end_var = ctk.StringVar(value="00:00")
        self._vol_label_var = ctk.StringVar(value=f"Volume: {self._volume_original}%")

        self._montar_layout()
        self._on_param_change()          # sincroniza rótulos + validação + estado inicial
        self._agendar_progresso()

    # ------------------------------------------------------------------ #
    def _safe_grab(self):
        try:
            self.grab_set()
        except Exception:
            pass

    # -- construção da UI ----------------------------------------------- #
    def _montar_layout(self):
        mainframe = ctk.CTkFrame(self, corner_radius=CORNER, border_width=1,
                                 bg_color=WIN_BG, fg_color=BAR_BG, border_color=BORDER)
        mainframe.grid(row=0, column=0, padx=20, pady=20, sticky=ctk.NSEW)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        mainframe.grid_columnconfigure(0, weight=1)

        styled_label(mainframe, text="Calibração de Volume", font=BASE_FONT).grid(
            row=0, column=0, padx=15, pady=(15, 4), sticky=ctk.N)
        styled_label(mainframe, text="Ajuste o volume ideal para o participante antes da sessão.",
                     text_color=FAINT, font=ctk.CTkFont(DISPLAY_FAMILY, FONT_SM)).grid(
            row=1, column=0, padx=15, pady=(0, 16), sticky=ctk.N)

        self._montar_parametros(mainframe, 2)
        self._montar_mini_player(mainframe, 3)

        # rótulo grande do volume atual (linha de base e calibração o atualizam ao vivo)
        ctk.CTkLabel(mainframe, textvariable=self._vol_label_var, text_color=TEXT,
                     font=ctk.CTkFont(DISPLAY_FAMILY, FONT_4XL, weight="bold")).grid(
            row=4, column=0, padx=15, pady=(6, 12))

        self._montar_botoes(mainframe, 5)

    def _montar_parametros(self, master, row):
        """Linha horizontal com os quatro parâmetros da rampa (mín/máx/passo%/intervalo)."""
        frame = ctk.CTkFrame(master, fg_color=TRANSPARENTE)
        frame.grid(row=row, column=0, padx=15, pady=(0, 14))

        # entries de volume mínimo/máximo (0–100%), com validação de borda vermelha.
        self._vol_min_entry = self._coluna_entry(frame, "VOL. MÍNIMO (%)", self._vol_min_var)
        self._vol_max_entry = self._coluna_entry(frame, "VOL. MÁXIMO (%)", self._vol_max_var)

        # sliders de passo de aumento (%) e intervalo (s), ambos 1–5.
        self._step_pct_slider, self._step_pct_valor = self._coluna_slider(
            frame, "AUMENTO (%)", self._step_pct_var,
            calibration.CALIB_STEP_PCT_MIN, calibration.CALIB_STEP_PCT_MAX)
        self._step_seg_slider, self._step_seg_valor = self._coluna_slider(
            frame, "A CADA (S)", self._step_seg_var,
            calibration.CALIB_STEP_SEG_MIN, calibration.CALIB_STEP_SEG_MAX)

    def _coluna_entry(self, master, rotulo, var):
        """Sub-coluna (caption + entry estreito) para um parâmetro de volume."""
        col = ctk.CTkFrame(master, fg_color=TRANSPARENTE)
        col.pack(side=ctk.LEFT, padx=(0, 14))
        caption(col, rotulo).pack(anchor=ctk.W, pady=(0, 4))
        entry = styled_entry(col, textvariable=var, width=72, height=INPUT_H, justify=ctk.CENTER)
        entry.pack()
        entry.bind("<KeyRelease>", lambda _e: self._on_param_change())
        return entry

    def _coluna_slider(self, master, rotulo, var, minimo, maximo):
        """Sub-coluna (caption + slider 1–5 + valor) para um parâmetro de passo/intervalo."""
        col = ctk.CTkFrame(master, fg_color=TRANSPARENTE)
        col.pack(side=ctk.TOP, padx=(0, 14))
        caption(col, rotulo).pack(anchor=ctk.W, pady=(0, 4))
        linha = ctk.CTkFrame(col, fg_color=TRANSPARENTE)
        linha.pack()
        slider = ctk.CTkSlider(linha, from_=minimo, to=maximo, number_of_steps=maximo - minimo,
                               width=110, height=16, variable=var,
                               command=lambda _v: self._on_param_change(),
                               progress_color=ACCENT, button_color=ACCENT,
                               button_hover_color=ACCENT, fg_color=BORDER)
        slider.pack(side=ctk.LEFT)
        valor = mono(linha, str(var.get()), size=FONT_LG, color=MUTED, width=24)
        valor.pack(side=ctk.LEFT, padx=(8, 0))
        return slider, valor

    def _montar_mini_player(self, master, row):
        """Mini-player: tempo decorrido | barra de progresso | tempo total."""
        frame = ctk.CTkFrame(master, fg_color=TRANSPARENTE)
        frame.grid(row=row, column=0, padx=15, pady=(0, 8), sticky=ctk.EW)
        master.grid_columnconfigure(0, weight=1)
        mono(frame, "", FONT_BASE, MUTED, textvariable=self._t_begin_var).pack(side=ctk.LEFT)
        self._progress = ctk.CTkProgressBar(frame, height=6, corner_radius=CORNER_PILL,
                                            progress_color=ACCENT, fg_color=BORDER)
        self._progress.set(0.0)
        self._progress.pack(side=ctk.LEFT, fill=ctk.X, expand=True, padx=12)
        mono(frame, "", FONT_BASE, MUTED, textvariable=self._t_end_var).pack(side=ctk.LEFT)

    def _montar_botoes(self, master, row):
        """Botões: "Linha de Base" (esquerda) e "Calibrar" (direita, morfa para Parar/Salvar)."""
        frame = ctk.CTkFrame(master, fg_color=TRANSPARENTE)
        frame.grid(row=row, column=0, padx=15, pady=(6, 15))
        self._btn_base = ghost_button(frame, "Linha de Base", command=self._on_linha_base,
                                      width=150, height=BTN_H)
        self._btn_base.pack(side=ctk.LEFT, padx=(0, 10))
        self._btn_calibrar = styled_button(frame, text="Calibrar", command=self._on_calibrar,
                                            width=150, height=BTN_H)
        self._btn_calibrar.pack(side=ctk.LEFT)

    # -- estilos morfáveis dos botões ----------------------------------- #
    def _como_acento(self, btn, texto):
        btn.configure(text=texto, fg_color=ACCENT, hover_color=ACCENT,
                      text_color=ACCENT_INK, border_width=0)

    def _como_ghost(self, btn, texto):
        btn.configure(text=texto, fg_color=INPUT_BG, hover_color=BORDER,
                      text_color=MUTED, border_width=1, border_color=BORDER)

    def _como_danger(self, btn, texto):
        btn.configure(text=texto, fg_color=DANGER_TINT, hover_color=DANGER_BORDER,
                      text_color=DANGER, border_width=1, border_color=DANGER_BORDER)

    # -- validação e rótulos -------------------------------------------- #
    def _on_param_change(self):
        """Reagenda a validação e atualiza os rótulos dos sliders (chamado por qualquer controle)."""
        self._step_pct_valor.configure(text=str(int(self._step_pct_var.get())))
        self._step_seg_valor.configure(text=str(int(self._step_seg_var.get())))
        self._validar_parametros_visual()

    def _validar_parametros_visual(self) -> list:
        """Valida os parâmetros; pinta a borda das entries de vermelho se inválido. Retorna erros."""
        erros = calibration.validar_parametros(
            self._vol_min_var.get(), self._vol_max_var.get(),
            int(self._step_pct_var.get()), int(self._step_seg_var.get()))
        self._params_validos = not erros
        cor = DANGER if erros else BORDER
        for entry in (self._vol_min_entry, self._vol_max_entry):
            try:
                entry.configure(border_color=cor)
            except Exception:
                pass
        if self._estado == "idle":
            self._aplicar_estado()
        return erros

    # -- máquina de estados --------------------------------------------- #
    def _aplicar_estado(self):
        """Configura os dois botões e a habilitação dos parâmetros conforme `self._estado`."""
        self._habilitar_parametros(self._estado == "idle")
        if self._estado == "idle":
            self._como_ghost(self._btn_base, "Linha de Base")
            self._btn_base.configure(command=self._on_linha_base,
                                     state="normal" if self._params_validos else "disabled")
            self._como_acento(self._btn_calibrar, "Calibrar")
            self._btn_calibrar.configure(
                command=self._on_calibrar,
                state="normal" if (self._params_validos and self._base_ok) else "disabled")
        elif self._estado == "base":
            self._como_danger(self._btn_base, "Parar")
            self._btn_base.configure(command=self._on_parar, state="normal")
            self._btn_calibrar.configure(state="disabled")
        elif self._estado == "calibrar":
            self._btn_base.configure(state="disabled")
            self._como_danger(self._btn_calibrar, "Parar")
            self._btn_calibrar.configure(command=self._on_parar, state="normal")
        elif self._estado == "salvar":
            self._btn_base.configure(state="disabled")
            self._como_acento(self._btn_calibrar, "Salvar")
            self._btn_calibrar.configure(command=self._on_salvar, state="normal")

    def _habilitar_parametros(self, habilitado: bool):
        estado = "normal" if habilitado else "disabled"
        for widget in (self._vol_min_entry, self._vol_max_entry,
                       self._step_pct_slider, self._step_seg_slider):
            try:
                widget.configure(state=estado)
            except Exception:
                pass

    # -- ações dos botões ----------------------------------------------- #
    def _on_linha_base(self):
        if not self._preparar_reproducao():
            return
        self._estado = "base"
        self._aplicar_estado()
        self._iniciar_rampa("base")

    def _on_calibrar(self):
        if not self._preparar_reproducao():
            return
        self._estado = "calibrar"
        self._aplicar_estado()
        self._iniciar_rampa("calibrar")

    def _on_parar(self):
        """Interrompe a rampa em curso (botão "Parar")."""
        modo = self._modo
        self._parar_reproducao()
        if modo == "base":
            # linha de base abortada: não conclui, logo a calibração continua bloqueada.
            self._estado = "idle"
        else:
            # calibração interrompida pelo participante: mantém o volume atual como ótimo.
            self._volume_otimo = self._vol_atual
            self._estado = "salvar"
        self._aplicar_estado()

    def _on_salvar(self):
        """Confirma o volume ótimo ("Sim") ou reinicia o teste ("Reiniciar")."""
        escolha = ask_options(
            "Confirmar volume", f"Confirma esse volume de {self._volume_otimo}%?",
            "Reiniciar", "Sim")
        if escolha == "Sim":
            self._salvo = True
            cb = self.ctx.aplicar_volume_calibrado
            if cb is not None:
                cb(self._volume_otimo)
            gui_logger.logger.info(f"Volume de calibração confirmado: {self._volume_otimo}%")
            self._fechar()
        elif escolha == "Reiniciar":
            # reinicia o teste; a linha de base já concluída continua válida.
            self._volume_otimo = None
            self._estado = "idle"
            atual = int(round(get_system_volume()))
            self._definir_volume_label(atual)
            self._aplicar_estado()

    # -- rampa de volume ------------------------------------------------ #
    def _preparar_reproducao(self) -> bool:
        """Valida parâmetros/arquivo, carrega o áudio e bloqueia se a faixa for curta demais.

        Retorna True se está tudo pronto para iniciar a rampa. Em qualquer falha, avisa o
        usuário (`show_message`) e retorna False sem alterar o estado.
        """
        erros = self._validar_parametros_visual()
        if erros:
            show_message("Parâmetros inválidos", "\n".join(erros))
            return False

        caminho = self.ctx.calibracao_caminho
        if not caminho or not os.path.isfile(caminho):
            show_message("Erro", "Nenhum arquivo de áudio de calibração válido foi definido.\n"
                                 "Carregue-o na janela de configuração do experimento.")
            return False

        if not self._player.load(caminho):
            show_message("Erro", "Não foi possível carregar o áudio de calibração.\n"
                                 "Verifique o arquivo (use .wav/.ogg/.mp3).")
            return False

        vmin, vmax, step_pct, step_seg = self._parametros_int()
        duracao = calibration.duracao_estimada_segundos(vmin, vmax, step_pct, step_seg)
        comprimento = self._player.get_length()
        # comprimento 0.0 = desconhecido -> não há como checar; deixa iniciar.
        if comprimento and duracao > comprimento:
            show_message(
                "Atenção",
                f"A faixa de calibração ({comprimento:.0f} s) é mais curta que a duração do "
                f"teste ({duracao:.0f} s).\nUse um áudio mais longo ou reduza o passo/intervalo.",
                icon="warning")
            return False
        return True

    def _iniciar_rampa(self, modo: str):
        """Começa a rampa: aplica o volume mínimo, toca a faixa e agenda o primeiro degrau."""
        self._modo = modo
        self._vmin, self._vmax, self._step_pct, self._step_seg = self._parametros_int()
        self._indice = 0
        self._definir_volume_label(self._vmin)
        set_system_volume(self._vmin)
        self._player.play()
        self._passo_id = self.after(self._step_seg * 1000, self._passo_rampa)
        gui_logger.logger.info(
            f"Calibração ({modo}) iniciada: {self._vmin}->{self._vmax}%, "
            f"+{self._step_pct}%/{self._step_seg}s")

    def _passo_rampa(self):
        """Sobe um degrau de volume; ao chegar no máximo, agenda o fim após o tempo de espera."""
        self._indice += 1
        vol = calibration.volume_no_incremento(self._indice, self._vmin, self._vmax, self._step_pct)
        set_system_volume(vol)
        self._definir_volume_label(vol)
        if vol >= self._vmax:
            self._passo_id = self.after(calibration.CALIB_HOLD_SEGUNDOS * 1000, self._fim_rampa)
        else:
            self._passo_id = self.after(self._step_seg * 1000, self._passo_rampa)

    def _fim_rampa(self):
        """Fim natural da rampa (chegou ao máximo e manteve o tempo de espera)."""
        modo = self._modo
        self._parar_reproducao()
        if modo == "base":
            self._base_ok = True         # linha de base concluída -> libera a calibração
            self._estado = "idle"
        else:
            self._volume_otimo = self._vmax
            self._estado = "salvar"
        self._aplicar_estado()

    def _parar_reproducao(self):
        """Cancela o temporizador da rampa e para a reprodução (não mexe no volume do sistema)."""
        self._modo = None
        if self._passo_id is not None:
            try:
                self.after_cancel(self._passo_id)
            except Exception:
                pass
            self._passo_id = None
        try:
            self._player.stop()
        except Exception:
            pass

    def _definir_volume_label(self, vol):
        """Atualiza o rótulo grande e o volume atual acompanhado internamente."""
        self._vol_atual = int(vol)
        self._vol_label_var.set(f"{int(vol)}%")

    def _parametros_int(self):
        """Parâmetros como inteiros (só chamado após a validação garantir que são válidos)."""
        return (int(self._vol_min_var.get()), int(self._vol_max_var.get()),
                int(self._step_pct_var.get()), int(self._step_seg_var.get()))

    # -- progresso do mini-player --------------------------------------- #
    def _agendar_progresso(self):
        self._progresso_id = self.after(_INTERVALO_PROGRESSO_MS, self._atualizar_progresso)

    def _atualizar_progresso(self):
        """Reflete posição/duração do player na barra e nos tempos (laço na thread da GUI)."""
        pos = comprimento = 0.0
        try:
            if self._player and self._player.is_busy():
                pos = float(self._player.get_pos() or 0.0)
                comprimento = float(self._player.get_length() or 0.0)
        except Exception:
            pass
        try:
            self._t_begin_var.set(format_time(pos))
            self._t_end_var.set(format_time(comprimento))
            prog = max(0.0, min(1.0, pos / comprimento)) if comprimento > 0 else 0.0
            self._progress.set(prog)
        except Exception:
            pass
        self._agendar_progresso()

    # -- fechamento ----------------------------------------------------- #
    def _on_fechar(self):
        """Fecha a janela; se o usuário não salvou, restaura o volume original do sistema."""
        self._parar_reproducao()
        if not self._salvo:
            set_system_volume(self._volume_original)
        self._fechar()

    def _fechar(self):
        if self._progresso_id is not None:
            try:
                self.after_cancel(self._progresso_id)
            except Exception:
                pass
            self._progresso_id = None
        self.withdraw()
        self.destroy()
