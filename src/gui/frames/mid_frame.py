import os

import customtkinter as ctk
from tkinter import filedialog

from .. import gui_logger
from ..guiconfigs import set_grids
from ..theme import (AZUL, AZUL_CLARO, ROSA, CINZA, AMARELO, AMARELO_ESC, TRANSPARENTE,
                     BASE_FONT, BORDER_WIDTH, BORDER_WIDTH_INSIDE, CORNER, NSE)
from ..widgets import show_message, styled_label, styled_button, styled_entry
from src.core import (scan_music_files, match_conditions, MissingConditionError,
                      set_system_volume, get_system_volume)
from src.utils import validar_nome_genero, validar_idade, format_time, get_data_dir


class MidFrame(ctk.CTkFrame):
    """Painel central: agrupa os formulários de participante, arquivos e o player."""

    def __init__(self, master, ctx):
        super().__init__(master, corner_radius=CORNER, border_width=BORDER_WIDTH, bg_color=AZUL, fg_color=ROSA, border_color=AZUL)
        set_grids(self, rows_conf={3: [0], 1: [1]}, column_conf={1: [0], 3: [1]}, grid_row=1)

        self.ctx = ctx

        self.up_left_mid_frame = UpLeftMidFrame(self, ctx)
        self.upright_mid_frame = UpRightMidFrame(self, ctx)
        self.down_mid_frame = DownMidFrame(self, ctx)


class UpLeftMidFrame(ctk.CTkFrame):
    """Formulário com os dados do participante (nome, idade, gênero)."""

    def __init__(self, master, ctx):
        super().__init__(master, corner_radius=CORNER, border_width=BORDER_WIDTH_INSIDE, bg_color=ROSA, fg_color=AZUL_CLARO, border_color=AZUL, background_corner_colors=(ROSA, ROSA, ROSA, ROSA)) # type: ignore
        set_grids(self, rows_conf={1: [0, 1, 2, 3]}, column_conf={0: [0], 3: [1]}, padx=20, pady=20)

        self.ctx = ctx

        self.name_label = styled_label(self, text="Nome:")
        self.name_label.grid(row=0, column=0, padx=15, pady=15, sticky=ctk.E)
        self.name_entry = styled_entry(self, width=300, height=30, placeholder_text="Digite o nome do participante")
        self.name_entry.grid(row=0, column=1, padx=15, pady=15, sticky=ctk.EW)

        self.idade_label = styled_label(self, text="Idade:")
        self.idade_label.grid(row=1, column=0, padx=15, pady=15, sticky=ctk.E)
        self.idade_entry = styled_entry(self, width=300, height=30, placeholder_text="Digite a idade do participante")
        self.idade_entry.grid(row=1, column=1, padx=15, pady=15, sticky=ctk.EW)

        self.genero_label = styled_label(self, text="Gênero:")
        self.genero_label.grid(row=2, column=0, padx=15, pady=15, sticky=ctk.E)
        self.genero_entry = styled_entry(self, width=300, height=30, placeholder_text="Digite o gênero do participante")
        self.genero_entry.grid(row=2, column=1, padx=15, pady=15, sticky=ctk.EW)

        self.save_infos_button = styled_button(self, text="Salvar informações", bg_color=AZUL_CLARO, fg_color=ROSA, command=self.save_infos)
        self.save_infos_button.grid(row=3, column=1, padx=15, pady=15, sticky=NSE)

    def save_infos(self):
        nome = self.name_entry.get().strip()
        idade = self.idade_entry.get().strip()
        genero = self.genero_entry.get().strip()

        if not validar_nome_genero(nome, genero):
            show_message("Erro", "Nome e gênero devem conter apenas letras e espaços.")
            return

        if not validar_idade(idade):
            show_message("Erro", "Idade deve ser um número entre 0 e 100.")
            return

        if not nome or not idade or not genero:
            show_message("Erro", "Todos os campos são obrigatórios.")
            return

        gui_logger.logger.info(f"Salvando informações do participante - Nome: {nome}, Idade: {idade}, Gênero: {genero}")

        self.ctx.nome = nome
        self.ctx.idade = idade
        self.ctx.genero = genero
        self.ctx.infos_saved = True

        self.save_infos_button.configure(state="disabled")
        self.name_entry.configure(state="disabled")
        self.idade_entry.configure(state="disabled")
        self.genero_entry.configure(state="disabled")

        self.edit_infos_button = styled_button(self, text="Editar informações", bg_color=AZUL_CLARO, fg_color=ROSA, command=self.edit_infos)
        self.edit_infos_button.grid(row=3, column=1, padx=15, pady=15, sticky=ctk.W)

        gui_logger.logger.info("Informações do participante salvas com sucesso.")

    def edit_infos(self):
        gui_logger.logger.info("Habilitando edição das informações do participante.")
        self.ctx.infos_saved = False
        self.save_infos_button.configure(state="normal")
        self.name_entry.configure(state="normal")
        self.idade_entry.configure(state="normal")
        self.genero_entry.configure(state="normal")
        self.edit_infos_button.destroy()


class UpRightMidFrame(ctk.CTkFrame):
    """Carregamento da pasta de músicas, do Excel de condições e do diretório de saída."""

    def __init__(self, master, ctx):
        super().__init__(master, corner_radius=CORNER, border_width=BORDER_WIDTH_INSIDE, bg_color=ROSA, fg_color=AZUL_CLARO, border_color=AZUL, background_corner_colors=(ROSA, ROSA, ROSA, ROSA)) # type: ignore
        set_grids(self, rows_conf={1: [0, 1, 2]}, column_conf={1: [0, 2], 3: [1]}, grid_column=1, padx=20, pady=20)

        self.ctx = ctx

        self.load_file_label = styled_label(self, text="Arquivos de músicas:")
        self.load_file_label.grid(row=0, column=0, padx=15, pady=15, sticky=ctk.E)

        self.music_file_folder_var = ctk.StringVar(value=r"Pasta contendo os arquivos de música")
        self.load_file_entry = styled_entry(self, width=420, placeholder_text="Diretório do arquivo de músicas",
                                             textvariable=self.music_file_folder_var, state="readonly")
        self.load_file_entry.grid(row=0, column=1, padx=15, pady=15, sticky=ctk.EW)

        self.load_file_button = styled_button(self, text="Carregar", width=80, bg_color=AZUL_CLARO, fg_color=ROSA, command=self.load_music_folder)
        self.load_file_button.grid(row=0, column=2, padx=15, pady=15, sticky=ctk.W)

        self.load_conditions = styled_label(self, text="Condições:")
        self.load_conditions.grid(row=1, column=0, padx=15, pady=15, sticky=ctk.E)

        self.conditions_file_var = ctk.StringVar(value="Excel contendo as condições ou fatores das músicas")
        self.conditions_entry = styled_entry(self, width=420, placeholder_text="Arquivo excel com as condições ou fatores das musicas",
                                              textvariable=self.conditions_file_var, state="readonly")
        self.conditions_entry.grid(row=1, column=1, padx=15, pady=15, sticky=ctk.EW)

        self.conditions_button = styled_button(self, text="Buscar", width=80, bg_color=AZUL_CLARO, fg_color=ROSA, command=self.load_conditions_file)
        self.conditions_button.grid(row=1, column=2, padx=15, pady=15, sticky=ctk.W)

        self.salvar_arquivos_label = styled_label(self, text="Salvar dados em:")
        self.salvar_arquivos_label.grid(row=2, column=0, padx=15, pady=15, sticky=ctk.E)

        self.salvar_arquivos_var = ctk.StringVar(value="Diretório para salvar os dados")
        self.salvar_arquivos_entry = styled_entry(self, width=420, placeholder_text="Diretório para salvar os dados",
                                                   textvariable=self.salvar_arquivos_var, state="readonly")
        self.salvar_arquivos_entry.grid(row=2, column=1, padx=15, pady=15, sticky=ctk.EW)

        self.salvar_arquivos_button = styled_button(self, text="Escolher", width=80, bg_color=AZUL_CLARO, fg_color=ROSA, command=self._choose_save_directory)
        self.salvar_arquivos_button.grid(row=2, column=2, padx=15, pady=15, sticky=ctk.W)

    def _pick_path(self, dialog, var, ctx_attr: str, erro_msg: str):
        """Abre um diálogo de seleção e, se um caminho válido for escolhido, atualiza a
        StringVar do campo e o atributo correspondente no contexto."""
        path = dialog()
        if not path:
            return
        try:
            if os.path.exists(path):
                var.set(path)
                setattr(self.ctx, ctx_attr, path)
        except Exception as e:
            show_message("Erro", f"{erro_msg}: {e}")

    def load_music_folder(self):
        self._pick_path(lambda: filedialog.askdirectory(title="Selecione uma pasta contendo os arquivos de música", initialdir=str(get_data_dir().parent)),
                        self.music_file_folder_var, "music_folder", "Erro ao carregar pasta com as músicas")

    def load_conditions_file(self):
        self._pick_path(lambda: filedialog.askopenfilename(title="Selecione um arquivo excel contendo as condições ou fatores das músicas", initialdir=str(get_data_dir().parent), filetypes=[("Excel files", "*.xlsx *.xls")]),
                        self.conditions_file_var, "conditions_file", "Erro ao carregar arquivo com as condições")

    def _choose_save_directory(self):
        self._pick_path(lambda: filedialog.askdirectory(title="Selecione um diretório para salvar os dados", initialdir=str(get_data_dir())),
                        self.salvar_arquivos_var, "save_dir", "Erro ao carregar diretório para salvar dados")

    def check_music_file_infos(self):
        """Aguarda a seleção da pasta de músicas, do Excel de condições e do diretório de
        saída, reverificando a cada 100 ms; dispara a varredura quando tudo está pronto e
        enquanto o mapeamento ainda não foi concluído (permite refazer ao corrigir a seleção).

        As StringVars são lidas aqui (thread da GUI) e passadas por valor para os workers —
        nunca acessar widgets/vars Tk fora da thread principal.
        """
        folder = self.music_file_folder_var.get()
        cond = self.conditions_file_var.get()
        save = self.salvar_arquivos_var.get()

        if not folder or folder == "Pasta contendo os arquivos de música":
            self.ctx.status_text.set("Selecione a pasta contendo os arquivos de música.")
            self.after(100, self.check_music_file_infos)
            return
        elif not cond or cond == "Excel contendo as condições ou fatores das músicas":
            self.ctx.status_text.set("Selecione o arquivo excel contendo as condições ou fatores das músicas.")
            self.after(100, self.check_music_file_infos)
            return
        elif not save or save == "Diretório para salvar os dados":
            self.ctx.status_text.set("Selecione o diretório para salvar os dados.")
            self.after(100, self.check_music_file_infos)
            return

        # tudo selecionado; mapeia (uma vez por combinação) enquanto ainda não houver mapeamento
        if not self.ctx.music_condition_mapping:
            sig = (folder, cond)
            if sig != getattr(self, "_last_scan_sig", None) and not getattr(self, "_scan_in_progress", False):
                self._last_scan_sig = sig
                self._scan_in_progress = True
                self.ctx.status_text.set("Arquivos selecionados! Verificando condições...")
                self.ctx.run_async(lambda: self.get_musics_from_folder(folder, cond))
            self.after(100, self.check_music_file_infos)

    def get_musics_from_folder(self, folder: str, cond_path: str):
        """Varre a pasta de músicas (thread de trabalho) e dispara o casamento de condições."""
        try:
            music_files = scan_music_files(folder)
        except FileNotFoundError as e:
            self._scan_in_progress = False
            self.ctx.run_after(lambda: show_message("Erro", f"Pasta de músicas não encontrada: {e}.\nPor favor, verifique o caminho e tente novamente."))
            return

        if not music_files:
            self._scan_in_progress = False
            self.ctx.run_after(lambda: self.ctx.status_text.set("Nenhum arquivo de áudio (.mp3/.wav/.ogg) na pasta selecionada."))
            gui_logger.logger.warning("Pasta selecionada não contém arquivos de áudio.")
            return

        self.ctx.music_files = music_files
        self.ctx.run_after(lambda: self.ctx.status_text.set("Arquivos de música encontrados! Verificando condições..."))
        self.match_condition_with_music_file(music_files, cond_path)

    def match_condition_with_music_file(self, music_files: list, cond_path: str):
        """Casa cada música com seu fator (thread de trabalho) e grava o mapeamento no contexto."""
        try:
            mapping = match_conditions(music_files, cond_path)
        except FileNotFoundError:
            self._scan_in_progress = False
            self.ctx.run_after(lambda: show_message("Erro", f"Arquivo de condições não encontrado: {cond_path}.\nPor favor, verifique o arquivo e tente novamente."))
            return
        except MissingConditionError as e:
            self._scan_in_progress = False
            self.ctx.run_after(lambda n=e.music_name: show_message("Atenção", f"Nenhuma condição encontrada para {n} no arquivo de condições.\nEssa música será ignorada durante o experimento.", icon="warning"))
            return

        if mapping is None:
            self._scan_in_progress = False
            self.ctx.run_after(lambda: self.ctx.status_text.set("Nenhuma condição encontrada para as músicas selecionadas."))
            gui_logger.logger.warning("Nenhuma condição encontrada para as músicas selecionadas.")
            return

        self.ctx.music_condition_mapping = mapping
        self._scan_in_progress = False
        self.ctx.run_after(lambda: self.ctx.status_text.set("Mapemento de músicas para condições realizado com sucesso!"))
        gui_logger.logger.info("Mapemento de músicas e condições realizado com sucesso!")


class DownMidFrame(ctk.CTkFrame):
    """Controles de reprodução: nome da faixa, volume, barra de progresso e parar."""

    def __init__(self, master, ctx):
        super().__init__(master, corner_radius=CORNER, border_width=BORDER_WIDTH_INSIDE, bg_color=ROSA, fg_color=AZUL_CLARO, border_color=AZUL, background_corner_colors=(ROSA, ROSA, ROSA, ROSA)) # type: ignore
        set_grids(self, rows_conf={1: [0, 1, 2]}, column_conf={1: [0, 1, 2, 3]}, grid_row=1, columnspan=2, padx=20, pady=20)

        self.ctx = ctx

        # Rótulos reativos com largura FIXA (width+wraplength p/ textos longos, width simples
        # p/ textos curtos): travar a largura evita que mudar o texto redimensione o widget
        # e dispare reflow do layout (o "glitch" de redimensionamento ao interagir).
        self.music_name_label = styled_label(self, textvariable=self.ctx.current_music_text, font=BASE_FONT, width=520, wraplength=520, anchor=ctk.W)
        self.music_name_label.grid(row=0, column=0, columnspan=2, padx=20, pady=15, ipadx=10, sticky=ctk.EW)

        self.music_volume = ctk.CTkSlider(self, from_=0, to=100, number_of_steps=100, border_width=BORDER_WIDTH, border_color=AZUL, bg_color=AZUL_CLARO, fg_color=ROSA,
                                          button_color=AMARELO, button_hover_color=AMARELO_ESC, progress_color=AMARELO, command=self._on_volume_change)
        self.music_volume.grid(row=0, column=3, padx=20, pady=15, sticky=ctk.EW)

        self.music_volume_label = styled_label(self, textvariable=self.ctx.volume_text, font=BASE_FONT, width=150, anchor=ctk.E)
        self.music_volume_label.grid(row=0, column=2, padx=10, pady=15, sticky=ctk.EW)

        # Inicializa o slider/rótulo com o volume atual do sistema (leitura apenas).
        vol = int(round(get_system_volume()))
        self.music_volume.set(vol)
        self.ctx.volume_text.set(f"Volume: {vol}%")

        self.music_time_begin = styled_label(self, textvariable=self.ctx.time_begin_text, font=BASE_FONT, width=90, anchor=ctk.E)
        self.music_time_begin.grid(row=1, column=3, padx=20, pady=10, sticky=ctk.EW)

        self.music_time_end = styled_label(self, textvariable=self.ctx.time_end_text, font=BASE_FONT, width=90, anchor=ctk.W)
        self.music_time_end.grid(row=1, column=0, padx=20, pady=10, sticky=ctk.EW)

        self.stop_button = styled_button(self, text="Parar", width=80, bg_color=AZUL_CLARO, fg_color=ROSA, command=self._on_stop)
        self.stop_button.grid(row=2, column=0, columnspan=4, padx=10, pady=10, sticky=ctk.NS)

        self.music_progress = ctk.CTkProgressBar(self, height=10, border_width=BORDER_WIDTH, border_color=AZUL, bg_color=AZUL_CLARO, fg_color=ROSA, progress_color=CINZA)
        self.music_progress.grid(row=1, column=0, columnspan=4, padx=80, pady=20, sticky=ctk.NSEW)

        self.after(500, self._update_progress)

    def _on_stop(self):
        """Para o experimento (se houver um em curso) e a reprodução de áudio."""
        runner = self.ctx.runner
        if runner is not None and runner.is_running():
            runner.stop()
            return
        player = self.ctx.player
        try:
            if getattr(player, '_playlist_loaded', False):
                player.stop_playlist()
            else:
                player.stop()
        except Exception:
            pass

    def _on_volume_change(self, value):
        """Atualiza o rótulo imediatamente e aplica o volume com debounce.

        O comando do slider dispara a cada passo; aplicar `set_system_volume` em todos
        eles geraria muitos subprocessos (osascript/amixer). Por isso, agenda-se a
        aplicação ~150 ms após o último movimento, cancelando a anterior."""
        try:
            vol = int(float(value))
            self.ctx.volume_text.set(f"Volume: {vol}%")
            self._pending_volume = vol
            pending = getattr(self, "_volume_after_id", None)
            if pending is not None:
                self.after_cancel(pending)
            self._volume_after_id = self.after(150, self._apply_pending_volume)
        except Exception:
            pass

    def _apply_pending_volume(self):
        """Aplica o último volume solicitado (chamado pelo debounce na thread da GUI)."""
        self._volume_after_id = None
        if not set_system_volume(self._pending_volume) and not getattr(self, "_volume_warned", False):
            self._volume_warned = True
            self.ctx.status_text.set("Controle de volume do sistema indisponível.")

    def _update_progress(self):
        player = self.ctx.player
        pos = 0.0
        length = 0.0
        try:
            # só mostra posição/duração reais enquanto há reprodução; ocioso = 00:00
            if player and player.is_busy():
                pos = float(player.get_pos() or 0.0)
                length = float(player.get_length() or 0.0)
        except Exception:
            pass
        try:
            self.ctx.time_begin_text.set(format_time(pos))
            self.ctx.time_end_text.set(format_time(length))
            prog = max(0.0, min(1.0, pos / length)) if length > 0 else 0.0
            try:
                self.music_progress.set(prog)
            except Exception:
                pass
        except Exception:
            pass
        try:
            self.after(500, self._update_progress)
        except Exception:
            pass
