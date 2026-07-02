import os
import tkinter
from tkinter import filedialog, messagebox

import customtkinter as ctk
import pywinstyles

from CTkMenuBar import CTkMenuBar, CustomDropdownMenu

from . import gui_logger
from . import set_window_configs
from . import theme
from .context import AppContext
from .assets import AppImages, ASSETS_DIR
from .theme import ACCENT, ACCENT_TINT, BAR_BG, DISPLAY_FAMILY, FOOTER_BG, TEXT, WIN_BG, TRANSPARENTE, WIN_MIN_WIDTH, WIN_MIN_HEIGHT
from .widgets import show_message
from .frames import (ConnectionFrame, StepperFrame, ParticipantCard, FilesCard,
                     PlayerBar, GraphPlaceholder, DownFrame)
from .experiment_config_window import ExperimentConfigWindow
from src.core import config_manager, set_system_volume

#ctk.set_appearance_mode("dark")

class ComPasso(ctk.CTk):
    """Janela raiz: cria o `AppContext` e monta o `MainFrame` (tema escuro)."""

    def __init__(self, nome="ComPasso"):
        # aplica o tema salvo (se houver) ANTES de construir qualquer widget, para que a
        # janela e todos os frames já nasçam com a paleta persistida.
        saved_theme = config_manager.get_theme_pref()
        if saved_theme:
            theme.set_theme(saved_theme)

        super().__init__(fg_color=WIN_BG)
        self.title(nome)
        self.minsize(WIN_MIN_WIDTH, WIN_MIN_HEIGHT)
        set_window_configs(self, width=WIN_MIN_WIDTH, height=WIN_MIN_HEIGHT)

        pywinstyles.change_border_color(self, WIN_BG)  # Windows: muda a cor da borda da janela
        pywinstyles.change_header_color(self, WIN_BG)  # Windows: muda a cor da barra de título

        # ícone da janela principal (Windows usa .ico; em outros SOs o ícone vem do bundle)
        try:
            self.iconbitmap(str(ASSETS_DIR / "icon.ico"))
        except Exception as e:
            gui_logger.logger.warning(f"Não foi possível definir o ícone da janela: {e}")

        self.ctx = AppContext(self)
        self.ctx.images = AppImages()   # carregado após o root existir (mantido por compat.)

        # menu "Experimento" + sistema de configuração (.config)
        self._loaded_config_path = None
        self._loaded_config_data = None
        self._build_menu()

        # inicialização do volume do sistema em 50% (uma única vez, no arranque).
        # O PlayerBar lê o volume atual em seguida e reflete esse valor no slider.
        set_system_volume(50)

        self.main_frame = MainFrame(self, self.ctx)
        self.main_frame.pack(fill="both", expand=True)

        self._auto_load_config()

    # ------------------------------------------------------------------ #
    def _build_menu(self):
        """Cria a barra de menus com o menu 'Experimento' (Novo/Abrir/Editar) usando CTkMenuBar."""
        # Cria a barra superior integrada ao fundo da janela
        self.menu_bar = CTkMenuBar(master=self, bg_color=FOOTER_BG,
                                   height=10, width=10,
                                   padx=5, pady=1)
        
        # Adiciona o botão principal "Experimento"
        self.btn_experimento = self.menu_bar.add_cascade(
            "Experimento",
            hover_color=ACCENT_TINT,
            font=ctk.CTkFont(DISPLAY_FAMILY, 12, weight="bold")
        )
        
        # Cria o dropdown flutuante associado ao botão
        self.dropdown_experimento = CustomDropdownMenu(
            widget=self.btn_experimento,
            bg_color=WIN_BG,
            hover_color=ACCENT_TINT,
            border_color=BAR_BG,
            border_width=2,
        )
        
        # Adiciona as opções
        self.dropdown_experimento.add_option(option="Novo", command=self._on_novo)
        self.dropdown_experimento.add_option(option="Abrir", command=self._on_abrir)
        self.editar_option = self.dropdown_experimento.add_option(  # type: ignore[func-returns-value]
            option="Editar", command=self._on_editar, state="disabled")

        # Menu "Tema": uma opção por paleta disponível; troca a aparência ao vivo.
        self.btn_tema = self.menu_bar.add_cascade("Tema", 
                                                  hover_color=ACCENT_TINT,
                                                  font=ctk.CTkFont(DISPLAY_FAMILY, 12, weight="bold"))
        self.dropdown_tema = CustomDropdownMenu(
            widget=self.btn_tema,
            bg_color=WIN_BG,
            hover_color=ACCENT_TINT,
            border_color=BAR_BG,
            border_width=2
        )
        for nome_tema in theme.THEME_NAMES:
            self.dropdown_tema.add_option(
                option=nome_tema,
                command=lambda n=nome_tema: self._on_theme_selected(n)
            )

    def _enable_editar(self):
        self.editar_option.configure(state="normal") #type: ignore[union-attr]

    # ------------------------------------------------------------------ #
    def _theme_switch_allowed(self) -> bool:
        """Só permite trocar o tema com a aplicação ociosa (sem conexão nem sessão em curso).

        Uma troca reconstrói a UI inteira, o que resetaria a visão de conexão e o andamento
        do experimento; por isso é bloqueada enquanto houver inlet ou runner ativo.
        """
        runner = self.ctx.runner
        return self.ctx.bitalino is None and (runner is None or not runner.is_running())

    def _on_theme_selected(self, name: str):
        """Aplica a paleta `name` ao vivo (se ocioso), persiste a escolha e reconstrói a UI."""
        if not self._theme_switch_allowed():
            show_message("Tema", "Desconecte o Bitalino e finalize a sessão antes de trocar o tema.",
                         icon="info")
            return
        if not theme.set_theme(name):
            gui_logger.logger.warning(f"Tema desconhecido ignorado: {name}")
            return
        config_manager.set_theme_pref(name)
        gui_logger.logger.info(f"Tema alterado para: {name}")
        self._rebuild_ui()

    def _rebuild_ui(self):
        """Reconstrói a barra de menus e o `MainFrame` para refletir a paleta ativa.

        Reutiliza o mesmo `AppContext` — o estado (config, infos do participante) sobrevive;
        os frames re-registram seus callbacks ao serem reconstruídos. Em seguida reaplica a
        config carregada e restaura o resumo do participante, se já estava salvo.
        """
        self.configure(fg_color=WIN_BG)
        pywinstyles.change_border_color(self, WIN_BG)
        pywinstyles.change_header_color(self, WIN_BG)

        self.main_frame.destroy()
        self.menu_bar.destroy()

        self._build_menu()
        if self._loaded_config_data:
            self._enable_editar()

        self.main_frame = MainFrame(self, self.ctx)
        self.main_frame.pack(fill="both", expand=True)

        if self._loaded_config_data:
            self.apply_config(self._loaded_config_data)
        if self.ctx.infos_saved:
            self.main_frame.participant_card.restore_summary()

    def _on_novo(self):
        ExperimentConfigWindow(self, mode="novo", on_saved=self._on_config_saved)

    def _on_editar(self):
        if not self._loaded_config_data:
            return
        ExperimentConfigWindow(self, mode="editar", on_saved=self._on_config_saved,
                               initial=self._loaded_config_data, config_path=self._loaded_config_path)

    def _on_abrir(self):
        path = filedialog.askopenfilename(parent=self, title="Abrir configuração",
                                          initialdir=str(config_manager.get_experiment_files_dir()),
                                          filetypes=[("Config files", "*.config")])
        if not path:
            return
        data, errors = config_manager.load_config(path)
        if errors:
            messagebox.showerror("Arquivo inválido", "O arquivo de configuração contém problemas:\n\n" + "\n".join(errors))
            return
        if data is None:
            messagebox.showerror("Erro", "Falha ao carregar o arquivo de configuração.")
            return
        gui_logger.logger.info(f"Configuração carregada: {path}")
        self._set_current_config(path, data)
        self.apply_config(data)
        self._show_temp_status("Configuração carregada com sucesso.", 3000)

    def _on_config_saved(self, path, data):
        """Callback após salvar (Novo/Editar): adota a config, aplica e habilita 'Editar'."""
        self._set_current_config(path, data)
        self.apply_config(data)

    def _set_current_config(self, path, data):
        self._loaded_config_path = path
        self._loaded_config_data = data
        config_manager.set_last_config(path)
        self._enable_editar()

    def _auto_load_config(self):
        """Carrega silenciosamente a última configuração usada, se válida."""
        path = config_manager.get_last_config_path()
        if not path or not os.path.exists(path):
            return
        data, errors = config_manager.load_config(path)
        if errors:
            gui_logger.logger.warning(f"Última configuração ignorada (inválida): {path}")
            return
        if data is None:
            gui_logger.logger.warning(f"Última configuração ignorada (falha ao carregar): {path}")
            return
        self._set_current_config(path, data)
        self.apply_config(data)
        gui_logger.logger.info(f"Configuração carregada automaticamente: {path}")

    def _show_temp_status(self, message, ms):
        """Mostra `message` no rótulo de status por `ms` milissegundos e restaura o texto anterior."""
        previous = self.ctx.status_text.get()
        self.ctx.status_text.set(message)
        self.after(ms, lambda: self.ctx.status_text.set(previous))

    def apply_config(self, data: dict):
        """Aplica os valores da configuração aos campos da janela principal e ao contexto.

        Cada campo é tratado individualmente; campos ausentes na janela são ignorados.
        """
        conn = self.main_frame.connection_frame
        files = self.main_frame.files_card

        # MAC do BITalino
        try:
            mac = str(data.get("bitalino_mac", "")).strip()
            if mac:
                conn.mac_addr_var.set(mac)
                self.ctx.mac_addr = mac
        except Exception as e:
            gui_logger.logger.warning(f"apply_config (MAC): {e}")

        # Canal ativo (A1–A6): grava "A{n}" no optionmenu e o índice no contexto
        try:
            channel = str(data.get("bitalino_channel", "")).strip().upper()
            if channel.startswith("A") and channel[1:].isdigit():
                n = int(channel[1:])
                conn.canal_var.set(f"A{n}")
                self.ctx.signal_channel = n
        except Exception as e:
            gui_logger.logger.warning(f"apply_config (canal): {e}")

        # Pasta de músicas
        try:
            music = str(data.get("music_folder", "")).strip()
            if music:
                files.music_file_folder_var.set(music)
                self.ctx.music_folder = music
        except Exception as e:
            gui_logger.logger.warning(f"apply_config (pasta de músicas): {e}")

        # Arquivo de fatores -> campo de condições
        try:
            factors = str(data.get("factors_file", "")).strip()
            if factors:
                files.conditions_file_var.set(factors)
                self.ctx.conditions_file = factors
        except Exception as e:
            gui_logger.logger.warning(f"apply_config (fatores): {e}")

        # Pasta de salvamento dos dados
        try:
            save_dir = str(data.get("data_save_path", "")).strip()
            if save_dir:
                files.salvar_arquivos_var.set(save_dir)
                self.ctx.save_dir = save_dir
        except Exception as e:
            gui_logger.logger.warning(f"apply_config (pasta de salvamento): {e}")

        # atualiza os checks dos arquivos e o stepper após aplicar a config
        try:
            files._refresh_checks()
        except Exception as e:
            gui_logger.logger.warning(f"apply_config (refresh checks): {e}")
        self.ctx.notify_stepper()


class MainFrame(ctk.CTkFrame):
    """Contêiner do redesign: pilha vertical de seções + rodapé fixo.

    `content` reúne conexão, stepper, cartões, player e o espaço do gráfico;
    o rodapé (`DownFrame`) fica preso embaixo.
    """

    def __init__(self, master, ctx):
        super().__init__(master, fg_color=WIN_BG, corner_radius=0)
        gui_logger.logger.info("MainFrame iniciado.")

        self.ctx = ctx

        content = ctk.CTkScrollableFrame(self, fg_color=WIN_BG,
                                         scrollbar_fg_color=TRANSPARENTE, 
                                         scrollbar_button_color=ACCENT_TINT,
                                         scrollbar_button_hover_color=ACCENT)
        content.pack(fill="both", expand=True, padx=22, pady=(5, 0))

        self.connection_frame = ConnectionFrame(content, ctx)
        self.connection_frame.pack(fill="x", pady=(0, 16))

        self.stepper_frame = StepperFrame(content, ctx)
        self.stepper_frame.pack(fill="x", pady=(0, 16))

        cards = ctk.CTkFrame(content, fg_color=TRANSPARENTE)
        cards.pack(fill="x", pady=(0, 16))
        cards.grid_columnconfigure(0, weight=2, uniform="c")
        cards.grid_columnconfigure(1, weight=3, uniform="c")

        self.participant_card = ParticipantCard(cards, ctx)
        self.participant_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        self.files_card = FilesCard(cards, ctx)
        self.files_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        self.player_bar = PlayerBar(content, ctx)
        self.player_bar.pack(fill="x", pady=(0, 16))

        self.graph = GraphPlaceholder(content, ctx)
        self.graph.pack(fill="x", pady=(0, 16))

        # rodapé preso embaixo (criado antes do content para reservar o espaço inferior)
        self.down_frame = DownFrame(self, ctx)
        self.down_frame.pack(fill="x", side="bottom") 

        self.after(100, self.files_card.check_music_file_infos)

if __name__ == "__main__":
    app = ComPasso()
    app.mainloop()
