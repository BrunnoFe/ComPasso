"""Janela modal de configuração do experimento (compartilhada por "Novo" e "Editar").

Segue o tema escuro da janela principal (cores/fontes de `theme.py`, widgets de `widgets.py`).
Salva/edita arquivos `.config` via `compasso.core.config_manager`.
"""

import os

import pandas as pd
import pywinstyles
import customtkinter as ctk
from tkinter import filedialog

from compasso.gui.assets import ASSETS_DIR
from compasso.utils.configs import ICON_FILENAME

from . import gui_logger
from .theme import (BASE_FONT_MIN, WIN_BG, BAR_BG, BORDER, DANGER, ACCENT, TEXT, TRANSPARENTE, BASE_FONT, CORNER)
from .widgets import (show_message, confirm, styled_label, styled_button, styled_entry,
                     styled_combobox, ghost_button)
from compasso.core.config_manager import (save_config, validate_values, get_experiment_files_dir,
                                     CHANNEL_OPTIONS, PRE_STIMULUS_MIN, PRE_STIMULUS_MAX,
                                     PRE_STIMULUS_DEFAULT, MUSIC_COLUMN_DEFAULT, FACTOR_COLUMN_DEFAULT,
                                     BEEP_ENABLED_DEFAULT, BEEP_LEAD_MIN, BEEP_LEAD_MAX, BEEP_LEAD_DEFAULT)
from compasso.core.constants import SENSOR_TYPES, SENSOR_DEFAULT

class ExperimentConfigWindow(ctk.CTkToplevel):
    """Janela de configuração do experimento.

    :param master: janela/root pai.
    :param mode: "novo" (campos vazios + salvar como) ou "editar" (pré-preenchido + sobrescrever).
    :param on_saved: callback `on_saved(path, data)` chamado após salvar com sucesso.
    :param initial: dict com valores iniciais (modo "editar").
    :param config_path: caminho do `.config` a sobrescrever (modo "editar").
    """

    def __init__(self, master, mode="novo", on_saved=None, initial=None, config_path=None):
        super().__init__(master, fg_color=WIN_BG)
        self.mode = mode
        self.on_saved = on_saved
        self.config_path = config_path

        self.title("Configuração do Experimento")
        self.resizable(False, False)
        self.transient(master)
        self.after(10, self._safe_grab)

        try:
            pywinstyles.change_border_color(self, WIN_BG)  # Windows: muda a cor da borda da janela
            pywinstyles.change_header_color(self, WIN_BG)  # Windows: muda a cor da barra de título
            self.iconbitmap(str(ASSETS_DIR / ICON_FILENAME))
        except Exception as e:
            gui_logger.logger.warning(f"Não foi possível ajustar a janela : {e}")

        mainframe = ctk.CTkFrame(self, corner_radius=CORNER, border_width=1,
                                 bg_color=WIN_BG, fg_color=BAR_BG, border_color=BORDER)
        mainframe.grid(row=0, column=0, padx=20, pady=20, sticky=ctk.NSEW)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        mainframe.grid_columnconfigure(1, weight=1)

        self.titulo = styled_label(mainframe, text="Configuração do Experimento", font=BASE_FONT)
        self.titulo.grid(row=0, column=0, columnspan=3, padx=15, pady=(15, 20), sticky=ctk.N)

        # variáveis dos campos
        self.music_folder_var = ctk.StringVar()
        self.music_quantity_var = ctk.StringVar()
        self.noise_quantity_var = ctk.StringVar()
        self.factors_file_var = ctk.StringVar()
        self.music_column_var = ctk.StringVar(value="")
        self.factor_column_var = ctk.StringVar(value="")
        self.data_save_var = ctk.StringVar()
        self.channel_var = ctk.StringVar(value="")
        self.sensor_var = ctk.StringVar(value=SENSOR_DEFAULT)
        self.mac_var = ctk.StringVar()
        self.pre_stimulus_var = ctk.IntVar(value=PRE_STIMULUS_DEFAULT)
        self.beep_habilitado_var = ctk.BooleanVar(value=BEEP_ENABLED_DEFAULT)
        self.beep_segundos_var = ctk.IntVar(value=BEEP_LEAD_DEFAULT)

        # 1) Pasta de músicas
        self._path_row(mainframe, 1, "Pasta de músicas:", self.music_folder_var, self._pick_music_folder)
        # 2) Quantidade de músicas
        self._entry_row(mainframe, 2, "Quantidade de músicas:", self.music_quantity_var, "Apenas dígitos (mín. 1)")
        # 3) Quantidade de ruído
        self._entry_row(mainframe, 3, "Quantidade de ruído:", self.noise_quantity_var, "Apenas dígitos (mín. 0)")
        # 4) Arquivo de fatores
        self._path_row(mainframe, 4, "Arquivo de fatores:", self.factors_file_var, self._pick_factors_file)
        # 5-6) Colunas da planilha de fatores — só surgem após carregar o arquivo (grid_remove
        # inicial; exibidas/populadas por _load_factor_columns).
        self.music_column_label = styled_label(mainframe, text="Coluna do nome dos áudios:")
        self.music_column_label.grid(row=5, column=0, padx=15, pady=10, sticky=ctk.E)
        self.music_column_combo = styled_combobox(mainframe, variable=self.music_column_var, values=[],
                                                  state="readonly", width=320, command=self._on_column_change)
        self.music_column_combo.grid(row=5, column=1, columnspan=2, padx=15, pady=10, sticky=ctk.EW)
        self.factor_column_label = styled_label(mainframe, text="Coluna dos fatores:")
        self.factor_column_label.grid(row=6, column=0, padx=15, pady=10, sticky=ctk.E)
        self.factor_column_combo = styled_combobox(mainframe, variable=self.factor_column_var, values=[],
                                                   state="readonly", width=320, command=self._on_column_change)
        self.factor_column_combo.grid(row=6, column=1, columnspan=2, padx=15, pady=10, sticky=ctk.EW)
        self._hide_column_selectors()
        # 7) Pasta de salvamento dos dados
        self._path_row(mainframe, 7, "Pasta de salvamento dos dados:", self.data_save_var, self._pick_save_folder)

        # 8) Canal ativo do BITalino
        styled_label(mainframe, text="Canal ativo do BITalino:").grid(row=8, column=0, padx=15, pady=10, sticky=ctk.E)
        self.channel_combobox = styled_combobox(mainframe, variable=self.channel_var, values=CHANNEL_OPTIONS, state="readonly", width=120)
        self.channel_combobox.grid(row=8, column=1, columnspan=2, padx=15, pady=10, sticky=ctk.W)

        # 9) Tipo de sensor do BITalino (define unidade/escala do gráfico)
        styled_label(mainframe, text="Tipo de sensor:").grid(row=9, column=0, padx=15, pady=10, sticky=ctk.E)
        self.sensor_combobox = styled_combobox(mainframe, variable=self.sensor_var, values=list(SENSOR_TYPES), state="readonly", width=120)
        self.sensor_combobox.grid(row=9, column=1, columnspan=2, padx=15, pady=10, sticky=ctk.W)

        # 10) Endereço MAC do BITalino
        styled_label(mainframe, text="Endereço MAC do BITalino:").grid(row=10, column=0, padx=15, pady=10, sticky=ctk.E)
        self.mac_entry = styled_entry(mainframe, textvariable=self.mac_var, width=320, placeholder_text="XX:XX:XX:XX:XX:XX")
        self.mac_entry.grid(row=10, column=1, columnspan=2, padx=15, pady=10, sticky=ctk.EW)

        # 11) Tempo pré-estímulo (contagem regressiva antes de cada faixa) — slider 5 a 120 s
        self._construir_linha_pre_estimulo(mainframe, 11)

        # 12) Beep de aviso: checkbox que habilita o slider da antecedência (t-X, 1 a 10 s)
        self._construir_linha_beep(mainframe, 12)

        # botões
        button_row = ctk.CTkFrame(mainframe, fg_color=TRANSPARENTE)
        button_row.grid(row=13, column=0, columnspan=3, padx=15, pady=(20, 15), sticky=ctk.E)
        self.salvar_button = styled_button(button_row, text="Salvar", width=120, command=self._on_salvar)
        self.salvar_button.grid(row=0, column=0, padx=(0, 10))
        self.cancelar_button = ghost_button(button_row, text="Cancelar", width=120, command=self._on_cancelar)
        self.cancelar_button.grid(row=0, column=1)

        if initial:
            self._populate(initial)

    # ------------------------------------------------------------------ #
    def _safe_grab(self):
        try:
            self.grab_set()
        except Exception:
            pass

    def _path_row(self, master, row, label, var, command):
        """Linha com rótulo + entry somente-leitura de caminho + botão de seleção."""
        styled_label(master, text=label).grid(row=row, column=0, padx=15, pady=10, sticky=ctk.E)
        entry = styled_entry(master, textvariable=var, width=320, state="readonly")
        entry.grid(row=row, column=1, padx=15, pady=10, sticky=ctk.EW)
        styled_button(master, text="Procurar", width=90, command=command).grid(row=row, column=2, padx=15, pady=10, sticky=ctk.W)

    def _entry_row(self, master, row, label, var, placeholder):
        """Linha com rótulo + entry editável (texto livre validado no salvar)."""
        styled_label(master, text=label).grid(row=row, column=0, padx=15, pady=10, sticky=ctk.E)
        entry = styled_entry(master, textvariable=var, width=320, placeholder_text=placeholder)
        entry.grid(row=row, column=1, columnspan=2, padx=15, pady=10, sticky=ctk.EW)

    # tempo pré-estímulo (contagem regressiva) -------------------------
    def _construir_linha_pre_estimulo(self, master, row):
        """Monta a linha da contagem regressiva como slider (5 a 120 s) com rótulo do valor."""
        styled_label(master, text="Tempo pré-estímulo (s):").grid(row=row, column=0, padx=15, pady=10, sticky=ctk.E)

        frame = ctk.CTkFrame(master, fg_color=TRANSPARENTE)
        frame.grid(row=row, column=1, columnspan=2, padx=15, pady=10, sticky=ctk.EW)
        self.pre_stimulus_slider = ctk.CTkSlider(
            frame, from_=PRE_STIMULUS_MIN, to=PRE_STIMULUS_MAX,
            number_of_steps=PRE_STIMULUS_MAX - PRE_STIMULUS_MIN, width=260,
            variable=self.pre_stimulus_var, command=self._ao_mudar_pre_estimulo,
            progress_color=ACCENT, button_color=ACCENT, button_hover_color=ACCENT, fg_color=BORDER)
        self.pre_stimulus_slider.pack(side=ctk.LEFT)
        self.pre_stimulus_valor_label = styled_label(frame, text=f"{self.pre_stimulus_var.get()} s")
        self.pre_stimulus_valor_label.pack(side=ctk.LEFT, padx=(8, 0))

    def _ao_mudar_pre_estimulo(self, valor):
        """Atualiza o rótulo da contagem e revalida o beep (que deve ser menor que ela)."""
        self.pre_stimulus_valor_label.configure(text=f"{int(round(float(valor)))} s")
        self._validar_beep_visual()

    # beep de aviso -----------------------------------------------------
    def _construir_linha_beep(self, master, row):
        """Monta a linha do beep: checkbox de habilitação + slider da antecedência (t-X).

        O slider (1 a 10 s) só fica habilitado quando o checkbox está marcado. Um rótulo ao
        lado mostra o valor atual em segundos.
        """
        styled_label(master, text="Beep de aviso:").grid(row=row, column=0, padx=15, pady=10, sticky=ctk.E)

        # container-folha: usa pack internamente (o pai usa grid para seus filhos diretos).
        beep_frame = ctk.CTkFrame(master, fg_color=TRANSPARENTE)
        beep_frame.grid(row=row, column=1, columnspan=2, padx=15, pady=10, sticky=ctk.EW)

        self.beep_checkbox = ctk.CTkCheckBox(
            beep_frame, text="Tocar um beep antes de cada faixa",
            variable=self.beep_habilitado_var, command=self._ao_alternar_beep,
            fg_color=ACCENT, hover_color=ACCENT, text_color=TEXT, border_color=BORDER,
            corner_radius=CORNER, font=BASE_FONT_MIN)
        self.beep_checkbox.pack(side=ctk.TOP, anchor=ctk.W)

        slider_frame = ctk.CTkFrame(beep_frame, fg_color=TRANSPARENTE)
        slider_frame.pack(side=ctk.TOP, anchor=ctk.W, pady=(8, 0))
        styled_label(slider_frame, text="Tocar em t-").pack(side=ctk.LEFT, padx=(0, 8))
        self.beep_slider = ctk.CTkSlider(
            slider_frame, from_=BEEP_LEAD_MIN, to=BEEP_LEAD_MAX,
            number_of_steps=BEEP_LEAD_MAX - BEEP_LEAD_MIN, width=220,
            variable=self.beep_segundos_var, command=self._ao_mudar_segundos_beep,
            progress_color=ACCENT, button_color=ACCENT, button_hover_color=ACCENT, fg_color=BORDER)
        self.beep_slider.pack(side=ctk.LEFT)
        self.beep_valor_label = styled_label(slider_frame, text=f"{self.beep_segundos_var.get()} s")
        self.beep_valor_label.pack(side=ctk.LEFT, padx=(8, 0))

        self._ao_alternar_beep()  # sincroniza o estado inicial (slider desabilitado por padrão)

    def _ao_alternar_beep(self):
        """Habilita/desabilita o slider da antecedência conforme o checkbox do beep."""
        estado = "normal" if bool(self.beep_habilitado_var.get()) else "disabled"
        self.beep_slider.configure(state=estado)
        self._validar_beep_visual()

    def _ao_mudar_segundos_beep(self, valor):
        """Atualiza o rótulo do slider com a antecedência escolhida (segundos inteiros)."""
        self.beep_valor_label.configure(text=f"{int(round(float(valor)))} s")
        self._validar_beep_visual()

    def _beep_invalido(self) -> bool:
        """True se o beep está habilitado e a antecedência não é menor que a contagem.

        O beep precisa tocar durante a contagem regressiva; se t-X >= contagem, ele nunca
        soaria antes da faixa. Só é considerado inválido quando o beep está habilitado.
        """
        if not bool(self.beep_habilitado_var.get()):
            return False
        return int(self.beep_segundos_var.get()) >= int(self.pre_stimulus_var.get())

    def _validar_beep_visual(self):
        """Pinta o slider/rótulo do beep de vermelho quando a antecedência é inválida."""
        habilitado = bool(self.beep_habilitado_var.get())
        invalido = self._beep_invalido()
        cor_slider = DANGER if invalido else ACCENT
        self.beep_slider.configure(progress_color=cor_slider, button_color=cor_slider,
                                   button_hover_color=cor_slider)
        if invalido:
            self.beep_valor_label.configure(text_color=DANGER)
        else:
            self.beep_valor_label.configure(text_color=TEXT if habilitado else BORDER)

    # pickers -----------------------------------------------------------
    def _pick_music_folder(self):
        path = filedialog.askdirectory(parent=self, title="Selecione a pasta de músicas", initialdir=str(get_experiment_files_dir().parent))
        if path:
            self.music_folder_var.set(path)

    def _pick_factors_file(self):
        path = filedialog.askopenfilename(parent=self, title="Selecione o arquivo de fatores",
                                          filetypes=[("Excel files", "*.xlsx *.xls")],
                                          initialdir=str(get_experiment_files_dir().parent))
        if path:
            self.factors_file_var.set(path)
            # novo arquivo -> descarta a seleção anterior de colunas e repopula os dropdowns.
            self.music_column_var.set("")
            self.factor_column_var.set("")
            self._load_factor_columns(path)

    # colunas da planilha de fatores ----------------------------------
    def _hide_column_selectors(self):
        """Oculta as duas linhas de seleção de coluna (mantendo suas posições no grid)."""
        for widget in (self.music_column_label, self.music_column_combo,
                       self.factor_column_label, self.factor_column_combo):
            widget.grid_remove()

    def _load_factor_columns(self, path: str):
        """Lê os cabeçalhos do Excel de fatores e exibe/popula os dropdowns de coluna.

        Lê apenas o cabeçalho (`nrows=0`) para não carregar os dados. Em caso de falha,
        avisa o usuário e mantém os seletores ocultos.
        """
        try:
            colunas = [str(c) for c in pd.read_excel(path, nrows=0).columns]
        except Exception as e:
            gui_logger.logger.warning(f"Não foi possível ler as colunas de '{path}': {e}")
            show_message("Erro", f"Não foi possível ler as colunas da planilha de fatores:\n{e}",
                         icon="cancel")
            self._hide_column_selectors()
            return

        if not colunas:
            show_message("Atenção", "A planilha de fatores não possui colunas legíveis.",
                         icon="warning")
            self._hide_column_selectors()
            return

        self.music_column_combo.configure(values=colunas)
        self.factor_column_combo.configure(values=colunas)
        for widget in (self.music_column_label, self.music_column_combo,
                       self.factor_column_label, self.factor_column_combo):
            widget.grid()
        self._on_column_change()

    def _on_column_change(self, _value=None):
        """Validação em tempo real: pinta as bordas de vermelho se as colunas coincidirem."""
        music = self.music_column_var.get().strip()
        factor = self.factor_column_var.get().strip()
        iguais = bool(music) and music == factor
        cor = DANGER if iguais else BORDER
        self.music_column_combo.configure(border_color=cor)
        self.factor_column_combo.configure(border_color=cor)

    def _pick_save_folder(self):
        path = filedialog.askdirectory(parent=self, title="Selecione a pasta de salvamento dos dados", initialdir=str(get_experiment_files_dir().parent))
        if path:
            self.data_save_var.set(path)

    # dados -------------------------------------------------------------
    def _collect(self) -> dict:
        return {
            "music_folder": self.music_folder_var.get().strip(),
            "music_quantity": self.music_quantity_var.get().strip(),
            "noise_quantity": self.noise_quantity_var.get().strip(),
            "factors_file": self.factors_file_var.get().strip(),
            "music_column": self.music_column_var.get().strip(),
            "factor_column": self.factor_column_var.get().strip(),
            "data_save_path": self.data_save_var.get().strip(),
            "bitalino_channel": self.channel_var.get().strip(),
            "sensor_type": self.sensor_var.get().strip(),
            "bitalino_mac": self.mac_var.get().strip(),
            "pre_stimulus_seconds": int(self.pre_stimulus_var.get()),
            "beep_enabled": bool(self.beep_habilitado_var.get()),
            "beep_lead_seconds": int(self.beep_segundos_var.get()),
        }

    def _populate(self, data: dict):
        self.music_folder_var.set(str(data.get("music_folder", "")))
        self.music_quantity_var.set(str(data.get("music_quantity", "")))
        self.noise_quantity_var.set(str(data.get("noise_quantity", "")))
        factors = str(data.get("factors_file", ""))
        self.factors_file_var.set(factors)
        # colunas: se houver arquivo válido, repopula os dropdowns e pré-seleciona o salvo.
        if factors and os.path.isfile(factors):
            self._load_factor_columns(factors)
            self.music_column_var.set(str(data.get("music_column", MUSIC_COLUMN_DEFAULT)))
            self.factor_column_var.set(str(data.get("factor_column", FACTOR_COLUMN_DEFAULT)))
            self._on_column_change()
        self.data_save_var.set(str(data.get("data_save_path", "")))
        self.channel_var.set(str(data.get("bitalino_channel", "")))
        sensor = str(data.get("sensor_type", SENSOR_DEFAULT)).strip().upper()
        self.sensor_var.set(sensor if sensor in SENSOR_TYPES else SENSOR_DEFAULT)
        self.mac_var.set(str(data.get("bitalino_mac", "")))
        pre_estimulo = data.get("pre_stimulus_seconds", PRE_STIMULUS_DEFAULT)
        self.pre_stimulus_var.set(int(pre_estimulo) if str(pre_estimulo).strip().isdigit() else PRE_STIMULUS_DEFAULT)
        self._ao_mudar_pre_estimulo(self.pre_stimulus_var.get())
        # beep de aviso: restaura o estado e sincroniza slider/rótulo com o checkbox.
        self.beep_habilitado_var.set(bool(data.get("beep_enabled", BEEP_ENABLED_DEFAULT)))
        self.beep_segundos_var.set(int(data.get("beep_lead_seconds", BEEP_LEAD_DEFAULT)))
        self._ao_mudar_segundos_beep(self.beep_segundos_var.get())
        self._ao_alternar_beep()

    # ações -------------------------------------------------------------
    def _on_salvar(self):
        values = self._collect()
        errors = validate_values(values)
        if errors:
            show_message("Configuração inválida", "\n".join(errors), icon="cancel")
            return

        # checagem específica da janela: as colunas escolhidas precisam existir no arquivo de
        # fatores (feita aqui porque só aqui temos o path do Excel à mão).
        factors_file = values.get("factors_file", "")
        if factors_file and os.path.isfile(factors_file):
            try:
                colunas = {str(c) for c in pd.read_excel(factors_file, nrows=0).columns}
            except Exception as e:
                show_message("Erro", f"Não foi possível ler as colunas da planilha de fatores:\n{e}",
                             icon="cancel")
                return
            faltando = [values[k] for k in ("music_column", "factor_column")
                        if values[k] and values[k] not in colunas]
            if faltando:
                show_message("Configuração inválida",
                             "As colunas selecionadas não existem na planilha de fatores: "
                             + ", ".join(faltando) + ".\nRecarregue o arquivo e selecione novamente.",
                             icon="cancel")
                return

        if self.mode == "editar" and self.config_path:
            nome = os.path.basename(self.config_path)
            if not confirm("Confirmar", f"Sobrescrever {nome}?"):
                return
            path = self.config_path
        else:
            save_dir = get_experiment_files_dir()
            os.makedirs(str(save_dir), exist_ok=True)
            path = filedialog.asksaveasfilename(parent=self, title="Salvar configuração",
                                                initialdir=str(save_dir),
                                                defaultextension=".config",
                                                filetypes=[("Config files", "*.config")])
            if not path:
                return

        try:
            save_config(path, values)
        except Exception as e:
            gui_logger.logger.error(f"Falha ao salvar configuração: {e}")
            show_message("Erro", f"Não foi possível salvar a configuração: {e}", icon="cancel")
            return

        if self.on_saved is not None:
            self.on_saved(path, values)
        self.withdraw()
        self.destroy()

    def _on_cancelar(self):
        self.withdraw()
        self.destroy()
