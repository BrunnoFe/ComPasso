import os
import webbrowser
from tkinter import filedialog

import customtkinter as ctk
import pywinstyles

from CTkMenuBar import CTkMenuBar, CustomDropdownMenu

from . import gui_logger
from . import set_window_configs
from . import theme
from .context import AppContext
from .assets import ASSETS_DIR
from .theme import ACCENT_TINT, BAR_BG, DISPLAY_FAMILY, FAINT2, FOOTER_BG, WIN_BG, TRANSPARENTE, WIN_MIN_WIDTH, WIN_MIN_HEIGHT, FONT_BASE_12
from .widgets import show_message, confirm, ghost_button
from .frames import (ConnectionFrame, StepperFrame, ParticipantCard, FilesCard,
                     PlayerBar, GraphFrame, DownFrame, CardsCollapseController)
from .frames.graph_frame import aplicar_sensor_ao_grafico
from .experiment_config_window import ExperimentConfigWindow
from .graph_settings_window import GraphSettingsWindow
from compasso.core import config_manager, set_system_volume
from compasso.core.constants import SENSOR_TYPES, SENSOR_DEFAULT
from compasso.utils import ICON_FILENAME, PROJECT_URL, PROJECT_GITSITE, get_logs_dir, open_path 

# Volume principal do sistema aplicado uma única vez no arranque do app.
_INIT_VOLUME = 50

ctk.set_appearance_mode("dark")  # tema escuro por padrão (pode ser alterado pelo usuário)

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

        # ícone da janela principal (Windows usa .ico; em outros SOs o ícone vem do bundle)
        try:
            pywinstyles.change_border_color(self, WIN_BG)  # Windows: muda a cor da borda da janela
            pywinstyles.change_header_color(self, WIN_BG)  # Windows: muda a cor da barra de título
            self.iconbitmap(str(ASSETS_DIR / ICON_FILENAME))
        except Exception as e:
            gui_logger.logger.warning(f"Não foi possível ajustar a janela : {e}")

        self.ctx = AppContext(self)

        # configurações de exibição do gráfico (persistidas em prefs.json); lidas antes de
        # construir o MainFrame para que o GraphFrame já nasça com os valores salvos.
        self.ctx.graph_settings = config_manager.get_graph_prefs()

        # menu "Experimento" + sistema de configuração (.config)
        self._loaded_config_path = None
        self._loaded_config_data = None
        self._build_menu()

        # inicialização do volume do sistema em 50% (uma única vez, no arranque).
        # O PlayerBar lê o volume atual em seguida e reflete esse valor no slider.
        set_system_volume(_INIT_VOLUME)

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
            font=ctk.CTkFont(DISPLAY_FAMILY, FONT_BASE_12, weight="bold")
        )
        
        # Cria o dropdown flutuante associado ao botão
        self.dropdown_experimento = CustomDropdownMenu(
            widget=self.btn_experimento,
            bg_color=WIN_BG,
            hover_color=ACCENT_TINT,
            border_color=BAR_BG,
            border_width=2,
        )
        
        # Adiciona as opções (referências guardadas para travar durante o experimento)
        self.novo_option = self.dropdown_experimento.add_option(option="Novo", command=self._on_novo)
        self.abrir_option = self.dropdown_experimento.add_option(option="Abrir", command=self._on_abrir)
        self.editar_option = self.dropdown_experimento.add_option(  # type: ignore[func-returns-value]
            option="Editar", command=self._on_editar, state="disabled")
        # "Sair" encerra o app; permanece sempre habilitada (inclusive durante o experimento).
        self.sair_option = self.dropdown_experimento.add_option(option="Sair", command=self._on_sair)

        self.btn_configs = self.menu_bar.add_cascade("Configurações",
                                                     hover_color=ACCENT_TINT,
                                                     font=ctk.CTkFont(DISPLAY_FAMILY, FONT_BASE_12, weight="bold"))
        self.dropdown_configs = CustomDropdownMenu(widget=self.btn_configs,
                                                    bg_color=WIN_BG,
                                                    hover_color=ACCENT_TINT,
                                                    border_color=BAR_BG,
                                                    border_width=2)
        
        self.dropdown_configs.add_option(option="Gráfico", command=self._on_graph_settings)

        # Menu "Tema": uma opção por paleta disponível; troca a aparência ao vivo.
        self.btn_tema = self.menu_bar.add_cascade("Tema",
                                                  hover_color=ACCENT_TINT,
                                                  font=ctk.CTkFont(DISPLAY_FAMILY, FONT_BASE_12, weight="bold"))
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

        # Menu "Ajuda": abrir a pasta de logs e a página do projeto no GitHub.
        self.btn_ajuda = self.menu_bar.add_cascade("Ajuda",
                                                   hover_color=ACCENT_TINT,
                                                   font=ctk.CTkFont(DISPLAY_FAMILY, FONT_BASE_12, weight="bold"))
        self.dropdown_ajuda = CustomDropdownMenu(
            widget=self.btn_ajuda,
            bg_color=WIN_BG,
            hover_color=ACCENT_TINT,
            border_color=BAR_BG,
            border_width=2
        )
        self.dropdown_ajuda.add_option(option="Abrir pasta de logs", command=self._on_open_logs)
        self.dropdown_ajuda.add_option(option="Página do projeto (GitHub)", command=lambda: self._on_open_github(PROJECT_URL))
        self.dropdown_ajuda.add_option(option="Site do projeto (GitHub Pages)", command=lambda: self._on_open_github(PROJECT_GITSITE))

    def _on_open_logs(self):
        """Abre a pasta de logs (`<app-data>/ComPasso/logs`) no gerenciador de arquivos do SO."""
        path = get_logs_dir()
        try:
            path.mkdir(parents=True, exist_ok=True)
            open_path(str(path))
            gui_logger.logger.info(f"Pasta de logs aberta: {path}")
        except Exception as e:
            gui_logger.logger.warning(f"Falha ao abrir a pasta de logs: {e}")
            show_message("Ajuda", f"Não foi possível abrir a pasta de logs:\n{path}", icon="warning")

    def _on_graph_settings(self):
        """Abre a janela modal "Configurações do Gráfico" (menu Configurações → Gráfico)."""
        GraphSettingsWindow(self, self.ctx)

    def _on_open_github(self, url):
        """Abre a página do projeto no navegador padrão."""
        try:
            webbrowser.open(url)
            gui_logger.logger.info(f"Página do projeto aberta: {url}")
        except Exception as e:
            gui_logger.logger.warning(f"Falha ao abrir a página do projeto: {e}")
            show_message("Ajuda", "Não foi possível abrir a página do projeto no navegador.", icon="warning")

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

        try:
            pywinstyles.change_border_color(self, WIN_BG)
            pywinstyles.change_header_color(self, WIN_BG)
        except Exception as e:
            gui_logger.logger.warning(f"Falha ao alterar cores da janela: {e}")

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

    def _on_sair(self):
        """Encerra a aplicação (opção 'Sair' do menu Experimento), com confirmação prévia."""
        if not confirm("Sair", "Tem certeza que deseja sair?"):
            return
        gui_logger.logger.info("Encerrando o aplicativo pela opção 'Sair'.")
        self.destroy()

    def _set_experimento_menu_locked(self, locked: bool):
        """Trava/destrava as opções Novo/Abrir/Editar do menu Experimento (exceto 'Sair').

        Chamado no início/fim do experimento (via `_set_experiment_ui_lock`). Ao destravar,
        'Editar' só volta a ficar disponível se há uma configuração carregada.
        """
        estado = "disabled" if locked else "normal"
        self.novo_option.configure(state=estado)   # type: ignore[union-attr]
        self.abrir_option.configure(state=estado)  # type: ignore[union-attr]
        if locked:
            self.editar_option.configure(state="disabled")  # type: ignore[union-attr]
        else:
            self.editar_option.configure(  # type: ignore[union-attr]
                state="normal" if self._loaded_config_data else "disabled")

    def _on_abrir(self):
        path = filedialog.askopenfilename(parent=self, title="Abrir configuração",
                                          initialdir=str(config_manager.get_experiment_files_dir()),
                                          filetypes=[("Config files", "*.config")])
        if not path:
            return
        data, errors = config_manager.load_config(path)
        if errors:
            show_message("Arquivo inválido", "O arquivo de configuração contém problemas:\n\n" + "\n".join(errors))
            return
        if data is None:
            show_message("Erro", "Falha ao carregar o arquivo de configuração.")
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

        # Tipo de sensor: reflete no optionmenu do top_frame e ajusta unidade/escala do gráfico
        # (chave opcional; arquivos antigos caem no default). resetar_escala=False mantém a
        # escala salva se estiver dentro dos limites do sensor.
        try:
            sensor = str(data.get("sensor_type", SENSOR_DEFAULT)).strip().upper()
            if sensor not in SENSOR_TYPES:
                sensor = SENSOR_DEFAULT
            conn.sensor_var.set(sensor)
            aplicar_sensor_ao_grafico(self.ctx, sensor, resetar_escala=False)
        except Exception as e:
            self.ctx.sensor_type = SENSOR_DEFAULT
            gui_logger.logger.warning(f"apply_config (tipo de sensor): {e}")

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

        # Colunas da planilha de condições (chaves opcionais; arquivos antigos caem no default).
        try:
            self.ctx.music_column = str(data.get("music_column", "musica")).strip() or "musica"
            self.ctx.factor_column = str(data.get("factor_column", "fator")).strip() or "fator"
        except Exception as e:
            self.ctx.music_column, self.ctx.factor_column = "musica", "fator"
            gui_logger.logger.warning(f"apply_config (colunas de condições): {e}")

        # Pasta de salvamento dos dados
        try:
            save_dir = str(data.get("data_save_path", "")).strip()
            if save_dir:
                files.salvar_arquivos_var.set(save_dir)
                self.ctx.save_dir = save_dir
        except Exception as e:
            gui_logger.logger.warning(f"apply_config (pasta de salvamento): {e}")

        # Quantidade de ruído: total de reproduções do ruído na sessão (0 se inválido/ausente).
        try:
            nq = data.get("noise_quantity", 0)
            self.ctx.noise_quantity = int(nq) if str(nq).strip().isdigit() else 0
        except Exception as e:
            self.ctx.noise_quantity = 0
            gui_logger.logger.warning(f"apply_config (quantidade de ruído): {e}")

        # Tempo pré-estímulo (s): contagem regressiva antes de cada faixa. Chave opcional —
        # arquivos antigos não a têm; cai no padrão. Clampado à faixa aceita por segurança.
        try:
            ps = data.get("pre_stimulus_seconds", config_manager.PRE_STIMULUS_DEFAULT)
            ps = int(ps) if str(ps).strip().lstrip("-").isdigit() else config_manager.PRE_STIMULUS_DEFAULT
            self.ctx.pre_stimulus_seconds = max(config_manager.PRE_STIMULUS_MIN,
                                                min(config_manager.PRE_STIMULUS_MAX, ps))
        except Exception as e:
            self.ctx.pre_stimulus_seconds = config_manager.PRE_STIMULUS_DEFAULT
            gui_logger.logger.warning(f"apply_config (tempo pré-estímulo): {e}")

        # Beep de aviso na contagem regressiva (chaves opcionais; arquivos antigos caem no
        # padrão: desabilitado, t-1 s). Antecedência clampada à faixa aceita por segurança.
        try:
            self.ctx.beep_habilitado = bool(data.get("beep_enabled", config_manager.BEEP_ENABLED_DEFAULT))
            antecedencia = data.get("beep_lead_seconds", config_manager.BEEP_LEAD_DEFAULT)
            antecedencia = int(antecedencia) if str(antecedencia).strip().lstrip("-").isdigit() else config_manager.BEEP_LEAD_DEFAULT
            self.ctx.beep_antecedencia_segundos = max(config_manager.BEEP_LEAD_MIN,
                                                      min(config_manager.BEEP_LEAD_MAX, antecedencia))
        except Exception as e:
            self.ctx.beep_habilitado = config_manager.BEEP_ENABLED_DEFAULT
            self.ctx.beep_antecedencia_segundos = config_manager.BEEP_LEAD_DEFAULT
            gui_logger.logger.warning(f"apply_config (beep de aviso): {e}")

        # Calibração de volume (chaves opcionais; arquivos antigos caem no padrão: desabilitada,
        # sem áudio). O botão "Calibrar" do PlayerBar é atualizado logo em seguida.
        try:
            self.ctx.calibracao_habilitada = bool(
                data.get("calibration_enabled", config_manager.CALIBRATION_ENABLED_DEFAULT))
            audio = str(data.get("calibration_audio", "")).strip()
            self.ctx.calibracao_caminho = audio or None
        except Exception as e:
            self.ctx.calibracao_habilitada = config_manager.CALIBRATION_ENABLED_DEFAULT
            self.ctx.calibracao_caminho = None
            gui_logger.logger.warning(f"apply_config (calibração de volume): {e}")
        try:
            if self.ctx.atualizar_botao_calibrar is not None:
                self.ctx.atualizar_botao_calibrar()
        except Exception as e:
            gui_logger.logger.warning(f"apply_config (botão calibrar): {e}")

        # marca que há uma configuração carregada (pré-requisito para iniciar o experimento)
        self.ctx.config_loaded = True

        # atualiza os checks dos arquivos e o stepper após aplicar a config
        try:
            files._refresh_checks()
        except Exception as e:
            gui_logger.logger.warning(f"apply_config (refresh checks): {e}")

        # se as músicas já foram mapeadas, reflete a nova noise_quantity nos contadores
        try:
            files.update_session_counters()
        except Exception as e:
            gui_logger.logger.warning(f"apply_config (contadores): {e}")

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
                                         scrollbar_button_color=BAR_BG,
                                         scrollbar_button_hover_color=FAINT2)
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

        # botão "^" (canto superior direito do bloco de cards) recolhe/expande os DOIS cards
        # juntos, via animação de slide coordenada (CardsCollapseController).
        self.collapse_button = ghost_button(self.files_card.header, "▴", 
                                            width=32, height=28,
                                            size=16)
        self.collapse_button.pack(side="right")
        self.cards_collapser = CardsCollapseController(
            [self.participant_card, self.files_card], self.collapse_button)
        self.collapse_button.configure(command=self.cards_collapser.toggle)

        # trava/destrava dos cards conforme o experimento (chamado pelo ExperimentRunner):
        # ao iniciar recolhe + desabilita o botão; ao finalizar/parar expande + reabilita.
        ctx.set_experiment_ui_lock = self._set_experiment_ui_lock

        self.player_bar = PlayerBar(content, ctx)
        self.player_bar.pack(fill="x", pady=(0, 16))

        self.graph = GraphFrame(content, ctx)
        self.graph.pack(fill="x", pady=(0, 16))

        # rodapé preso embaixo (criado antes do content para reservar o espaço inferior)
        self.down_frame = DownFrame(self, ctx)
        self.down_frame.pack(fill="x", side="bottom") 

        self.after(100, self.files_card.check_music_file_infos)

    def _set_experiment_ui_lock(self, active: bool):
        """Trava/destrava os cards colapsáveis conforme o experimento (thread da GUI).

        `active=True` (experimento iniciado): recolhe os cards (se abertos) e desabilita o
        botão de recolher. `active=False` (finalizado/parado): reabilita o botão e expande.
        """
        if active:
            self.cards_collapser.collapse()
            self.cards_collapser.set_enabled(False)
        else:
            self.cards_collapser.set_enabled(True)
            self.cards_collapser.expand()
        # trava/destrava o menu Experimento (Novo/Abrir/Editar) durante a sessão.
        self._set_experimento_menu_locked(active)

if __name__ == "__main__":
    app = ComPasso()
    app.mainloop()
