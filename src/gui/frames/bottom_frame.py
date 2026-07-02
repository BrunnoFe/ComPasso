import customtkinter as ctk

from ..theme import (FOOTER_BG, BORDER, TEXT, MUTED, FAINT, FAINT2, ACCENT,
                     ACCENT_INK, TRANSPARENTE, DISPLAY_FAMILY, CORNER_PILL, ACTION_BTN_H,
                     FONT_BASE, FONT_LG, FONT_XL, FONT_4XL)
from ..widgets import show_message, mono, caption
from src.core import ExperimentRunner


class DownFrame(ctk.CTkFrame):
    """Rodapé: contadores do experimento, status/progresso da sessão e o botão principal.

    Mantém o nome `DownFrame` e `_validar_prerequisitos` (dependência de teste). O botão
    principal agora é textual (não mais imagens), mas os estados
    `comecar`/`rodando`/`continuar` continuam trocados via `ctx.set_button_state`.
    """

    def __init__(self, master, ctx):
        super().__init__(master, fg_color=FOOTER_BG, corner_radius=0, border_width=0)
        self.ctx = ctx

        row = ctk.CTkFrame(self, fg_color=TRANSPARENTE)
        row.pack(fill="x", padx=24, pady=16)

        # ----- contadores -----
        self._counter(row, "ESTÍMULOS", self.ctx.music_done_text, self.ctx.music_total_text)
        self._counter(row, "RUÍDO", self.ctx.ruido_done_text, self.ctx.ruido_total_text)

        # ----- status + progresso da sessão -----
        mid = ctk.CTkFrame(row, fg_color=TRANSPARENTE)
        mid.pack(side="left", fill="x", expand=True, padx=8)
        head = ctk.CTkFrame(mid, fg_color=TRANSPARENTE)
        head.pack(fill="x")
        ctk.CTkLabel(head, textvariable=self.ctx.status_text, text_color=MUTED, anchor="w",
                     font=ctk.CTkFont(DISPLAY_FAMILY, FONT_BASE)).pack(side="left", fill="x", expand=True)
        mono(head, "", FONT_BASE, FAINT, textvariable=self.ctx.session_status_text).pack(side="right")
        spb = ctk.CTkProgressBar(mid, height=6, corner_radius=CORNER_PILL,
                                 progress_color=ACCENT, fg_color=BORDER,
                                 variable=self.ctx.session_progress)
        spb.pack(fill="x", pady=(6, 0))

        # ----- botão principal (comecar / rodando / continuar) -----
        self.action_button = ctk.CTkButton(
            row, text="Começar", width=170, height=ACTION_BTN_H, corner_radius=11,
            fg_color=ACCENT, hover_color=ACCENT, text_color=ACCENT_INK,
            font=ctk.CTkFont(DISPLAY_FAMILY, FONT_XL, weight="bold"),
            command=self.comecar_experimento)
        self.action_button.pack(side="left", padx=(24, 0))

        # expõe a troca de estado do botão para o runner (chamada via ctx.run_after)
        self.ctx.set_button_state = self._set_button_state
        self._set_button_state("comecar")

    def _counter(self, master, label, done_var, total_var):
        col = ctk.CTkFrame(master, fg_color=TRANSPARENTE)
        col.pack(side="left", padx=(0, 18))
        caption(col, label).pack(anchor="w")
        line = ctk.CTkFrame(col, fg_color=TRANSPARENTE)
        line.pack(anchor="w")
        ctk.CTkLabel(line, textvariable=done_var, text_color=TEXT,
                     font=ctk.CTkFont(DISPLAY_FAMILY, FONT_4XL, weight="bold")).pack(side="left")
        total = ctk.CTkLabel(line, text="", text_color=FAINT2,
                             font=ctk.CTkFont(DISPLAY_FAMILY, FONT_LG))
        total.pack(side="left")
        # prefixo " / " no total via trace
        def _sync(*_):
            total.configure(text=f" / {total_var.get()}")
        total_var.trace_add("write", _sync)
        _sync()

    # ------------------------------------------------------------------ #
    def _set_button_state(self, state: str):
        """Alterna o estado do botão principal: 'comecar' | 'rodando' | 'continuar'."""
        self._button_state = state
        if state == "rodando":
            self.action_button.configure(text="Executando…", state="disabled",
                                         fg_color=BORDER, text_color=MUTED, command=lambda: None)
        elif state == "continuar":
            self.action_button.configure(text="Continuar  →", state="normal",
                                         fg_color=ACCENT, text_color=ACCENT_INK,
                                         command=self._on_continuar)
        else:  # comecar
            self.action_button.configure(text="Começar", state="normal",
                                         fg_color=ACCENT, text_color=ACCENT_INK,
                                         command=self.comecar_experimento)

    def _on_continuar(self):
        """Avança para a próxima faixa (botão no estado 'continuar')."""
        if self.ctx.runner is not None:
            self.ctx.status_text.set("Continuando...")
            self.ctx.runner.continuar()

    def comecar_experimento(self):
        """Valida os pré-requisitos no contexto e inicia o experimento em thread separada."""
        # Exceção info do participante: se o formulário está preenchido mas não foi salvo,
        # salva em silêncio antes de validar. Se save_infos exibiu erro de validação
        # (formulário preenchido porém inválido), aborta sem mensagem duplicada.
        cb = getattr(self.ctx, "save_participant_infos_if_filled", None)
        if cb is not None and not self.ctx.infos_saved and cb():
            return

        problema = self._validar_prerequisitos()
        if problema:
            show_message("Atenção", problema, icon="warning")
            return

        if self.ctx.runner is None:
            self.ctx.runner = ExperimentRunner(self.ctx)
        self.ctx.status_text.set("Iniciando experimento...")
        self.ctx.runner.start()

    def _validar_prerequisitos(self) -> str:
        """Retorna uma mensagem de erro se algum pré-requisito faltar, ou '' se tudo certo."""
        if not getattr(self.ctx, "config_loaded", False):
            return "Crie ou abra uma configuração de experimento (menu Experimento) antes de iniciar."
        if self.ctx.bitalino is None:
            return "Conecte o Bitalino antes de iniciar o experimento."
        if not self.ctx.infos_saved:
            return "Salve as informações do participante antes de iniciar."
        if not self.ctx.music_files:
            return "Carregue os arquivos de música antes de iniciar."
        if not self.ctx.save_dir:
            return "Escolha o diretório para salvar os dados antes de iniciar."
        if self.ctx.runner is not None and self.ctx.runner.is_running():
            return "O experimento já está em andamento."
        return ""
