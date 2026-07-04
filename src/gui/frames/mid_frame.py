import os

import customtkinter as ctk
from tkinter import filedialog

from .. import gui_logger
from ..theme import (BORDER, DANGER_TINT, TEXT, MUTED, FAINT, SUCCESS, ACCENT, ACCENT_TINT, DANGER,
                     TRANSPARENTE, DISPLAY_FAMILY, CORNER_CHIP, CORNER_PILL, BTN_H,
                     FONT_XS, FONT_SM, FONT_BASE, FONT_LG, FONT_2XL, FONT_3XL)
from ..widgets import (show_message, confirm, title, caption, mono, ghost_button,
                       styled_entry, circle, check_icon, danger_button, Card)
from src.core import (scan_music_files, match_conditions, MissingConditionError,
                      set_system_volume, get_system_volume, session_totals)
from src.utils import validar_nome_genero, validar_idade, format_time, get_data_dir, MIN_IDADE, MAX_IDADE

# Intervalos (ms) do laço da GUI deste frame.
_POLL_MS = 100             # re-checagem da seleção de arquivos até tudo estar pronto
_PROGRESS_MS = 500         # atualização da barra de progresso / indicador de gravação
_VOLUME_DEBOUNCE_MS = 150  # espera após o último passo do slider antes de aplicar o volume

class ParticipantCard(Card):
    """Cartão do participante com dois estados: formulário e resumo.

    - Formulário (padrão / após "Editar"): campos Nome/Idade/Gênero + "Salvar informações".
    - Resumo (após salvar): avatar + nome + "idade anos · gênero" + "Editar".
    """

    def __init__(self, master, ctx):
        super().__init__(master)
        self.ctx = ctx

        inner = ctk.CTkFrame(self, fg_color=TRANSPARENTE)
        inner.pack(fill="both", expand=True, padx=20, pady=5)
        title(inner, "Participante").pack(anchor=ctk.W, pady=(5,0))

        self._body = ctk.CTkFrame(inner, fg_color=TRANSPARENTE)
        self._body.pack(fill=ctk.BOTH, expand=True)

        # ----- estado de formulário -----
        self.form_frame = ctk.CTkFrame(self._body, fg_color=TRANSPARENTE)
        self.name_entry = self._field(self.form_frame, "Nome", "Digite o nome do participante")
        self.idade_entry = self._field(self.form_frame, "Idade", "Digite a idade do participante")
        self.genero_entry = self._field(self.form_frame, "Gênero", "Digite o gênero do participante")
        self.save_infos_button = ghost_button(self.form_frame, text="Salvar informações",
                                                height=30, command=self.save_infos)
        self.save_infos_button.pack(anchor=ctk.S, pady=(20, 0))

        # ----- estado de resumo -----
        self.summary_frame = ctk.CTkFrame(self._body, fg_color=TRANSPARENTE)

        self.form_frame.pack(fill=ctk.BOTH, expand=True)

        # expõe ao DownFrame o salvamento silencioso quando o form está preenchido mas não salvo
        self.ctx.save_participant_infos_if_filled = self.save_infos_if_filled
        # expõe ao ExperimentRunner a possibilidade de bloquear a edição durante a sessão
        self.ctx.set_participant_editable = self.set_editable
        self.edit_button = None

    def _field(self, master, label, placeholder):
        row = ctk.CTkFrame(master, fg_color=TRANSPARENTE)
        row.pack(fill=ctk.X, pady=(5, 5))
        caption(row, label.upper()).pack(anchor=ctk.W, pady=(0, 2))
        entry = styled_entry(row, height=25, placeholder_text=placeholder)
        entry.pack(fill=ctk.X)
        return entry

    # ------------------------------------------------------------------ #
    def save_infos_if_filled(self) -> bool:
        """Se o formulário está preenchido mas não salvo, salva em silêncio.

        Retorna True somente se `save_infos` exibiu um erro de validação (formulário
        preenchido porém inválido), para que o chamador aborte sem mensagem duplicada."""
        if self.ctx.infos_saved:
            return False
        nome = self.name_entry.get().strip()
        idade = self.idade_entry.get().strip()
        genero = self.genero_entry.get().strip()
        if not (nome and idade and genero):
            return False  # incompleto: _validar_prerequisitos mostra a mensagem padrão
        self.save_infos()
        return not self.ctx.infos_saved

    def save_infos(self):
        nome = self.name_entry.get().strip()
        idade = self.idade_entry.get().strip()
        genero = self.genero_entry.get().strip()

        if not validar_nome_genero(nome, genero):
            show_message("Erro", "Nome e gênero devem conter apenas letras e espaços.")
            return

        if not validar_idade(idade):
            show_message("Erro", f"Idade deve ser um número entre {MIN_IDADE} e {MAX_IDADE}.")
            return

        if not nome or not idade or not genero:
            show_message("Erro", "Todos os campos são obrigatórios.")
            return

        gui_logger.logger.info(f"Salvando informações do participante - Nome: {nome}, Idade: {idade}, Gênero: {genero}")

        self.ctx.nome = nome
        self.ctx.idade = idade
        self.ctx.genero = genero
        self.ctx.infos_saved = True

        self._render_summary(nome, idade, genero)
        self.form_frame.pack_forget()
        self.summary_frame.pack(fill=ctk.BOTH, expand=True)

        gui_logger.logger.info("Informações do participante salvas com sucesso.")
        self.ctx.notify_stepper()

    def _render_summary(self, nome, idade, genero):
        for child in list(self.summary_frame.winfo_children()):
            child.destroy()
        avatar = circle(self.summary_frame, (nome[:1] or "?").upper(), filled=False, size=52)
        avatar.configure(font=ctk.CTkFont(DISPLAY_FAMILY, FONT_3XL, weight="bold"))
        avatar.pack(side="left")
        info = ctk.CTkFrame(self.summary_frame, fg_color=TRANSPARENTE)
        info.pack(side="left", padx=14)
        ctk.CTkLabel(info, text=nome, text_color=TEXT,
                     font=ctk.CTkFont(DISPLAY_FAMILY, FONT_2XL, weight="bold")).pack(anchor="w")
        mono(info, f"{idade} anos · {genero}", FONT_BASE, MUTED).pack(anchor="w")
        self.edit_button = ghost_button(self.summary_frame, "Editar", command=self.edit_infos)
        self.edit_button.configure(width=80, height=36)
        self.edit_button.pack(side="right")

    def edit_infos(self):
        gui_logger.logger.info("Habilitando edição das informações do participante.")
        self.ctx.infos_saved = False
        self.summary_frame.pack_forget()
        self.form_frame.pack(fill=ctk.BOTH, expand=True)
        self.ctx.notify_stepper()

    def set_editable(self, enabled: bool) -> None:
        """Habilita/desabilita o botão 'Editar' (bloqueado durante o experimento)."""
        if self.edit_button is not None:
            self.edit_button.configure(state="normal" if enabled else "disabled")

    def restore_summary(self):
        """Reexibe o resumo a partir do contexto (usado após reconstruir a UI, ex.: troca de tema)."""
        if not self.ctx.infos_saved:
            return
        self._render_summary(self.ctx.nome, self.ctx.idade, self.ctx.genero)
        self.form_frame.pack_forget()
        self.summary_frame.pack(fill=ctk.BOTH, expand=True)


class FilesCard(Card):
    """Carregamento da pasta de músicas, do Excel de condições e do diretório de saída."""

    _MUSIC_HINT = "Pasta contendo os arquivos de música"
    _COND_HINT = "Excel contendo as condições ou fatores das músicas"
    _SAVE_HINT = "Diretório para salvar os dados"

    def __init__(self, master, ctx):
        super().__init__(master)
        self.ctx = ctx

        inner = ctk.CTkFrame(self, fg_color=TRANSPARENTE)
        inner.pack(fill=ctk.BOTH, expand=True, padx=20, pady=18)
        title(inner, "Arquivos & Dados").pack(anchor=ctk.W, pady=(0, 12))

        self.music_file_folder_var = ctk.StringVar(value=self._MUSIC_HINT)
        self.conditions_file_var = ctk.StringVar(value=self._COND_HINT)
        self.salvar_arquivos_var = ctk.StringVar(value=self._SAVE_HINT)

        self._checks = {}
        self._checks["music"] = self._row(inner, "Músicas", self.music_file_folder_var,
                                           "Carregar", self.load_music_folder, first=True)
        self._checks["cond"] = self._row(inner, "Condições (.xlsx)", self.conditions_file_var,
                                         "Buscar", self.load_conditions_file)
        self._checks["save"] = self._row(inner, "Salvar dados em", self.salvar_arquivos_var,
                                         "Escolher", self._choose_save_directory)

    def _row(self, master, label, var, btn_text, command, first=False):
        r = ctk.CTkFrame(master, fg_color=TRANSPARENTE)
        r.pack(fill=ctk.X, pady=(0 if first else 10, 10))
        chk = check_icon(r, text="X", fg_color=DANGER_TINT, done=False)
        chk.pack(side=ctk.LEFT)
        col = ctk.CTkFrame(r, fg_color=TRANSPARENTE)
        col.pack(side=ctk.LEFT, fill=ctk.X, expand=True, padx=12)
        caption(col, label.upper()).pack(anchor=ctk.W)
        mono(col, "", FONT_BASE, MUTED, textvariable=var, anchor=ctk.W).pack(anchor=ctk.W, fill=ctk.X)
        gb = ghost_button(r, btn_text, size=FONT_BASE, command=command)
        gb.configure(width=88, height=32)
        gb.pack(side=ctk.RIGHT)
        return chk

    def _refresh_checks(self):
        """Recolore os ícones de check a partir do estado do contexto (thread da GUI)."""

        if self.ctx.music_folder:
            self._checks["music"].configure(fg_color=ACCENT_TINT, text="✓", text_color=SUCCESS)

        if self.ctx.conditions_file:
            self._checks["cond"].configure(fg_color=ACCENT_TINT, text="✓", text_color=SUCCESS)

        if self.ctx.save_dir:
            self._checks["save"].configure(fg_color=ACCENT_TINT, text="✓", text_color=SUCCESS)


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
                self._refresh_checks()
                self.ctx.notify_stepper()
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

        if not folder or folder == self._MUSIC_HINT:
            self.ctx.status_text.set("Selecione a pasta contendo os arquivos de música.")
            self.after(_POLL_MS, self.check_music_file_infos)
            return
        elif not cond or cond == self._COND_HINT:
            self.ctx.status_text.set("Selecione o arquivo excel contendo as condições ou fatores das músicas.")
            self.after(_POLL_MS, self.check_music_file_infos)
            return
        elif not save or save == self._SAVE_HINT:
            self.ctx.status_text.set("Selecione o diretório para salvar os dados.")
            self.after(_POLL_MS, self.check_music_file_infos)
            return

        # tudo selecionado; mapeia (uma vez por combinação) enquanto ainda não houver mapeamento
        if not self.ctx.music_condition_mapping:
            sig = (folder, cond)
            if sig != getattr(self, "_last_scan_sig", None) and not getattr(self, "_scan_in_progress", False):
                self._last_scan_sig = sig
                self._scan_in_progress = True
                self.ctx.status_text.set("Arquivos selecionados! Verificando condições...")
                self.ctx.run_async(lambda: self.get_musics_from_folder(folder, cond))
            self.after(_POLL_MS, self.check_music_file_infos)

    def get_musics_from_folder(self, folder: str, cond_path: str):
        """Varre a pasta de músicas (thread de trabalho) e dispara o casamento de condições."""
        try:
            music_files = scan_music_files(folder)
        except FileNotFoundError as e:
            # captura a mensagem antes do lambda: Python limpa `e` ao sair do except,
            # e o lambda só roda depois (via run_after), o que causaria NameError.
            erro = str(e)
            self._scan_in_progress = False
            self.ctx.run_after(lambda: show_message("Erro", f"Pasta de músicas não encontrada: {erro}.\nPor favor, verifique o caminho e tente novamente."))
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
        self.ctx.run_after(self._refresh_checks)
        self.update_session_counters()
        self.ctx.notify_stepper()
        gui_logger.logger.info("Mapemento de músicas e condições realizado com sucesso!")

    def update_session_counters(self):
        """Atualiza os contadores do rodapé a partir do mapeamento e da `noise_quantity`.

        Mostra os totais planejados (Estímulos/Ruído) já no carregamento dos arquivos, com
        os "concluídos" zerados — antes mesmo de o experimento iniciar. Seguro de chamar de
        qualquer thread (agenda a atualização das Vars na thread da GUI via `run_after`)."""
        mapping = self.ctx.music_condition_mapping or {}
        if not mapping:
            return
        mt, nt = session_totals(mapping, int(self.ctx.noise_quantity or 0))

        def apply():
            self.ctx.music_done_text.set("0")
            self.ctx.ruido_done_text.set("0")
            self.ctx.music_total_text.set(str(mt))
            self.ctx.ruido_total_text.set(str(nt))
            self.ctx.session_progress.set(0.0)
            self.ctx.session_status_text.set(f"0 / {mt + nt}")

        self.ctx.run_after(apply)


class PlayerBar(Card):
    """Controles de reprodução: faixa atual, volume, barra de progresso e parar."""

    def __init__(self, master, ctx):
        super().__init__(master)
        self.ctx = ctx

        row = ctk.CTkFrame(self, fg_color=TRANSPARENTE, height=300)
        row.pack(fill=ctk.BOTH, padx=20, pady=16, expand=True)

        # ----- esquerda: faixa -----
        left = ctk.CTkFrame(row, fg_color=TRANSPARENTE)
        left.pack(side=ctk.LEFT)

        # rec_frame e condition_chip ficam sempre "packed" (nunca pack_forget) para que o
        # cartão tenha altura fixa desde o início — só o texto/cor mudam em _update_progress,
        # reservando o espaço mesmo quando não há gravação/condição ativa.
        self.rec_frame = ctk.CTkFrame(left, fg_color=TRANSPARENTE)
        self.rec_frame.pack(anchor=ctk.W, pady=(4, 4))
        self.rec_dot = ctk.CTkLabel(self.rec_frame, text="", text_color=DANGER,
                     font=ctk.CTkFont(DISPLAY_FAMILY, FONT_XS))
        self.rec_dot.pack(side=ctk.LEFT, padx=(0, 7))
        self.rec_label = ctk.CTkLabel(self.rec_frame, text="", text_color=DANGER,
                     font=ctk.CTkFont(DISPLAY_FAMILY, FONT_SM, weight="bold"))
        self.rec_label.pack(side=ctk.LEFT)

        ctk.CTkLabel(left, textvariable=self.ctx.current_music_text, text_color=TEXT,
                     width=240, wraplength=240, anchor=ctk.W,
                     font=ctk.CTkFont(DISPLAY_FAMILY, FONT_LG, weight="bold")).pack(anchor=ctk.W, pady=(4, 4))
        self.condition_chip = ctk.CTkLabel(left, textvariable=self.ctx.current_condition_text,
                                           fg_color=TRANSPARENTE, text_color=ACCENT, corner_radius=CORNER_CHIP,
                                           font=ctk.CTkFont(DISPLAY_FAMILY, FONT_SM, weight="bold"))
        self.condition_chip.pack(anchor=ctk.W, pady=(4, 4))
        # cor/texto do chip são atualizados em _update_progress conforme houver condição

        # ----- centro: progresso -----
        prog = ctk.CTkFrame(row, fg_color=TRANSPARENTE)
        prog.pack(side=ctk.LEFT, fill=ctk.X, expand=True, padx=22)
        mono(prog, "", FONT_BASE, MUTED, textvariable=self.ctx.time_begin_text).pack(side=ctk.LEFT)
        self.music_progress = ctk.CTkProgressBar(prog, height=6, corner_radius=CORNER_PILL,
                                                 progress_color=ACCENT, fg_color=BORDER)
        self.music_progress.set(0.0)
        self.music_progress.pack(side=ctk.LEFT, fill=ctk.X, expand=True, padx=12)
        mono(prog, "", FONT_BASE, MUTED, textvariable=self.ctx.time_end_text).pack(side=ctk.LEFT)

        # ----- volume -----
        vol = ctk.CTkFrame(row, fg_color=TRANSPARENTE)
        vol.pack(side=ctk.LEFT, padx=(0, 22))
        ctk.CTkLabel(vol, text="Volume", text_color=MUTED,
                     font=ctk.CTkFont(DISPLAY_FAMILY, FONT_BASE)).pack(side=ctk.LEFT, padx=(0, 8))
        self.music_volume = ctk.CTkSlider(vol, width=120, height=16, from_=0, to=100,
                                          number_of_steps=100, progress_color=ACCENT,
                                          button_color=ACCENT, button_hover_color=ACCENT,
                                          fg_color=BORDER, command=self._on_volume_change)
        self.music_volume.pack(side=ctk.LEFT, fill=ctk.X, expand=True)
        self.music_volume_label = mono(vol, "", FONT_BASE, TEXT, textvariable=self.ctx.volume_text)
        self.music_volume_label.pack(side=ctk.LEFT, padx=(8, 0), fill=ctk.X, expand=True)

        # Inicializa o slider/rótulo com o volume atual do sistema (leitura apenas).
        v = int(round(get_system_volume()))
        self.music_volume.set(v)
        self.ctx.volume_text.set(f"{v}%")

        # ----- parar -----
        danger_button(row, "Parar", command=self._on_stop, width=90, height=BTN_H).pack(side=ctk.LEFT)

        self.after(_PROGRESS_MS, self._update_progress)

    def _on_stop(self):
        """Para o experimento (se houver um em curso) e a reprodução de áudio."""
        runner = self.ctx.runner
        if runner is not None and runner.is_running():
            if confirm("Parar experimento", "Tem certeza que deseja parar o experimento?"):
                runner.stop()
            return
        try:
            self.ctx.player.stop()
        except Exception:
            pass

    def _on_volume_change(self, value):
        """Atualiza o rótulo imediatamente e aplica o volume com debounce.

        O comando do slider dispara a cada passo; aplicar `set_system_volume` em todos
        eles geraria muitos subprocessos (osascript/amixer). Por isso, agenda-se a
        aplicação ~150 ms após o último movimento, cancelando a anterior."""
        try:
            vol = int(float(value))
            self.ctx.volume_text.set(f"{vol}%")
            self._pending_volume = vol
            pending = getattr(self, "_volume_after_id", None)
            if pending is not None:
                self.after_cancel(pending)
            self._volume_after_id = self.after(_VOLUME_DEBOUNCE_MS, self._apply_pending_volume)
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

        # indicador de gravação + chip de condição refletem o estado da aquisição; ambos
        # ficam sempre "packed" (altura fixa do cartão) — só texto/cor mudam aqui.
        try:
            runner = self.ctx.runner
            acquiring = runner is not None and runner.is_acquiring()
            self.rec_dot.configure(text="●" if acquiring else "")
            self.rec_label.configure(text="GRAVANDO" if acquiring else "")
            has_cond = bool(self.ctx.current_condition_text.get().strip())
            self.condition_chip.configure(fg_color=ACCENT_TINT if has_cond else TRANSPARENTE)
        except Exception:
            pass

        try:
            self.after(_PROGRESS_MS, self._update_progress)
        except Exception:
            pass
