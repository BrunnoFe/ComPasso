"""Janela modal de configuração do experimento (compartilhada por "Novo" e "Editar").

Segue o tema escuro da janela principal (cores/fontes de `theme.py`, widgets de `widgets.py`).
Salva/edita arquivos `.config` via `compasso.core.config_manager`.
"""

import os

import pywinstyles
import customtkinter as ctk
from tkinter import filedialog

from compasso.gui.assets import ASSETS_DIR
from compasso.utils.configs import ICON_FILENAME

from . import gui_logger
from .theme import (WIN_BG, BAR_BG, BORDER, TRANSPARENTE, BASE_FONT, CORNER)
from .widgets import (show_message, confirm, styled_label, styled_button, styled_entry,
                     styled_combobox, ghost_button)
from compasso.core.config_manager import (save_config, validate_values, get_experiment_files_dir,
                                     CHANNEL_OPTIONS, PRE_STIMULUS_MIN, PRE_STIMULUS_MAX,
                                     PRE_STIMULUS_DEFAULT)

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
        self.data_save_var = ctk.StringVar()
        self.channel_var = ctk.StringVar(value="")
        self.mac_var = ctk.StringVar()
        self.pre_stimulus_var = ctk.StringVar(value=str(PRE_STIMULUS_DEFAULT))

        # 1) Pasta de músicas
        self._path_row(mainframe, 1, "Pasta de músicas:", self.music_folder_var, self._pick_music_folder)
        # 2) Quantidade de músicas
        self._entry_row(mainframe, 2, "Quantidade de músicas:", self.music_quantity_var, "Apenas dígitos (mín. 1)")
        # 3) Quantidade de ruído
        self._entry_row(mainframe, 3, "Quantidade de ruído:", self.noise_quantity_var, "Apenas dígitos (mín. 0)")
        # 4) Arquivo de fatores
        self._path_row(mainframe, 4, "Arquivo de fatores:", self.factors_file_var, self._pick_factors_file)
        # 5) Pasta de salvamento dos dados
        self._path_row(mainframe, 5, "Pasta de salvamento dos dados:", self.data_save_var, self._pick_save_folder)

        # 6) Canal ativo do BITalino
        styled_label(mainframe, text="Canal ativo do BITalino:").grid(row=6, column=0, padx=15, pady=10, sticky=ctk.E)
        self.channel_combobox = styled_combobox(mainframe, variable=self.channel_var, values=CHANNEL_OPTIONS, state="readonly", width=120)
        self.channel_combobox.grid(row=6, column=1, columnspan=2, padx=15, pady=10, sticky=ctk.W)

        # 7) Endereço MAC do BITalino
        styled_label(mainframe, text="Endereço MAC do BITalino:").grid(row=7, column=0, padx=15, pady=10, sticky=ctk.E)
        self.mac_entry = styled_entry(mainframe, textvariable=self.mac_var, width=320, placeholder_text="XX:XX:XX:XX:XX:XX")
        self.mac_entry.grid(row=7, column=1, columnspan=2, padx=15, pady=10, sticky=ctk.EW)

        # 8) Tempo pré-estímulo (contagem regressiva antes de cada faixa)
        self._entry_row(mainframe, 8, "Tempo pré-estímulo (s):", self.pre_stimulus_var,
                        f"Inteiro de {PRE_STIMULUS_MIN} a {PRE_STIMULUS_MAX}")

        # botões
        button_row = ctk.CTkFrame(mainframe, fg_color=TRANSPARENTE)
        button_row.grid(row=9, column=0, columnspan=3, padx=15, pady=(20, 15), sticky=ctk.E)
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
            "data_save_path": self.data_save_var.get().strip(),
            "bitalino_channel": self.channel_var.get().strip(),
            "bitalino_mac": self.mac_var.get().strip(),
            "pre_stimulus_seconds": self.pre_stimulus_var.get().strip(),
        }

    def _populate(self, data: dict):
        self.music_folder_var.set(str(data.get("music_folder", "")))
        self.music_quantity_var.set(str(data.get("music_quantity", "")))
        self.noise_quantity_var.set(str(data.get("noise_quantity", "")))
        self.factors_file_var.set(str(data.get("factors_file", "")))
        self.data_save_var.set(str(data.get("data_save_path", "")))
        self.channel_var.set(str(data.get("bitalino_channel", "")))
        self.mac_var.set(str(data.get("bitalino_mac", "")))
        self.pre_stimulus_var.set(str(data.get("pre_stimulus_seconds", PRE_STIMULUS_DEFAULT)))

    # ações -------------------------------------------------------------
    def _on_salvar(self):
        values = self._collect()
        errors = validate_values(values)
        if errors:
            show_message("Configuração inválida", "\n".join(errors), icon="cancel")
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
